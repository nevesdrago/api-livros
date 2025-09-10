# livrosapi.py

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import BackgroundTasks
from tasks import calcular_soma, calcular_fatorial
from pydantic import BaseModel
import secrets
import os
import dotenv
import redis
import json
from celery_app import celery_app
from celery.result import AsyncResult
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Carregar variáveis de ambiente
dotenv.load_dotenv()

app = FastAPI(
    title="API de Livros",
    description="API para gerenciar catálogo de livros",
    version="1.0.0",
    contact={
        "name": "Eduardo Drago",
        "email": "eduardondrago05@gmail.com"
    }
)

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

security = HTTPBasic()

# Dicionário principal
livros = {}

# Classes Livro e LivroDB
class LivroDB(Base):
    __tablename__ = "Livros"
    id = Column(Integer, primary_key=True, index=True)
    nome_livro = Column(String, index=True) 
    autor_livro = Column(String, index=True)
    ano_livro = Column(Integer)

class Livro(BaseModel):
    nome_livro: str
    autor_livro: str
    ano_livro: int

Base.metadata.create_all(bind=engine)

def sessao_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Autenticação básica
def autenticar_usuario(credentials: HTTPBasicCredentials = Depends(security)):
    MEU_USUARIO = os.getenv("MEU_USUARIO")
    MINHA_SENHA = os.getenv("MINHA_SENHA")
    is_username_correct = secrets.compare_digest(credentials.username, MEU_USUARIO)
    is_password_correct = secrets.compare_digest(credentials.password, MINHA_SENHA)

    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=401,
            detail="Usuário ou senha incorretos.",
            headers={"WWW-Authenticate": "Basic"}
        )

# Métodos para salvar e deletar livros no Redis
async def salvar_livros_redis(page: int, limit: int, livros: list):
    cache_key = f"livros:page={page}&limit={limit}"
    redis_client.setex(cache_key, 100, json.dumps(livros))

async def deletar_livros_redis():
    for chave in redis_client.scan_iter("livros:page=*"):
        redis_client.delete(chave)

# GET - Buscar dados dos livros
@app.get("/livros")
async def get_livros(page: int = 1, limit: int = 10, db: Session = Depends(sessao_db), credentials: HTTPBasicCredentials = Depends(autenticar_usuario)):
    if page < 1 or limit < 1:
        raise HTTPException(status_code=400, detail="Page ou limit com valores inválidos!")
    
    cache_key = f"livros:page={page}&limit={limit}"
    cached = redis_client.get(cache_key)  

    if cached:
        return json.loads(cached)

    db_livros = db.query(LivroDB).offset((page - 1) * limit).limit(limit).all()

    if not db_livros:
        return {"message": "Não existe nenhum livro."}

    total_livros = db.query(LivroDB).count()

    resposta = {
        "page": page,
        "limit": limit,
        "total": total_livros,
        "livros": [{"id": livro.id, "nome_livro": livro.nome_livro, "autor_livro": livro.autor_livro, "ano_livro": livro.ano_livro} for livro in db_livros]
    }

    await salvar_livros_redis(page, limit, resposta)
    
    return resposta

# Debug Redis
@app.get("/debug/redis")
def ver_livros_redis():
    chaves = redis_client.keys("livros:*")
    livros = []

    for chave in chaves:
        valor = redis_client.get(chave)
        ttl = redis_client.ttl(chave)
        livros.append({"chave": chave, "valor": json.loads(valor), "ttl": ttl})

    return livros

# POST - Adicionar novos livros
@app.post("/livros")
async def post_livros(livro: Livro, db: Session = Depends(sessao_db), credentials: HTTPBasicCredentials = Depends(autenticar_usuario)):
    db_livro = db.query(LivroDB).filter(LivroDB.nome_livro == livro.nome_livro, LivroDB.autor_livro == livro.autor_livro).first()
    if db_livro:
        raise HTTPException(status_code=400, detail="Esse livro já existe no banco de dados!!!")
    
    novo_livro = LivroDB(nome_livro=livro.nome_livro, autor_livro=livro.autor_livro, ano_livro=livro.ano_livro)
    db.add(novo_livro)
    db.commit()
    db.refresh(novo_livro)

    await deletar_livros_redis()

    raise HTTPException(status_code=201, detail="Livro criado com sucesso!") 

# Tarefas Celery
@app.post("/calcular/soma")
def somar(a: int, b:int):
    tarefa = calcular_soma.delay(a, b)
    return {
        "task_id": tarefa.id,
        "message": "Tarefa de soma enviada para execução!"
    }

@app.post("/calcular/fatorial")
def fatorial(a: int):
    tarefa = calcular_fatorial.delay(a)
    return {
        "task_id": tarefa.id,
        "message": "Tarefa fatorial enviada para execução!"
    }

# Endpoint para consultar status/resultados de tasks
@app.get("/tasks/{task_id}")
def get_task_result(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None
    }

# PUT - Atualizar livros
@app.put("/livros/{id_livro}")
async def put_livros(id_livro: int, livro: Livro, db: Session = Depends(sessao_db), credentials: HTTPBasicCredentials = Depends(autenticar_usuario)):
    db_livro = db.query(LivroDB).filter(LivroDB.id == id_livro).first()
    if not db_livro:
        raise HTTPException(status_code=404, detail="Esse livro não foi encontrado no banco de dados.")
    
    db_livro.nome_livro = livro.nome_livro
    db_livro.autor_livro = livro.autor_livro
    db_livro.ano_livro = livro.ano_livro
    db.commit()
    db.refresh(db_livro)

    await deletar_livros_redis()

    raise HTTPException(status_code=200, detail="O livro foi atualizado com sucesso!")

# DELETE - Deletar livros
@app.delete("/livros/{id_livro}")
async def delete_livro(id_livro: int, db: Session = Depends(sessao_db), HTTPBasicCredentials = Depends(autenticar_usuario)):
    db_livro = db.query(LivroDB).filter(LivroDB.id == id_livro).first()

    if not db_livro:
        raise HTTPException(status_code=404, detail="Este livro não foi encontrado no seu banco de dados.")
    
    db.delete(db_livro)
    db.commit()

    await deletar_livros_redis()

    raise HTTPException(status_code=204, detail="Livro deletado com sucesso!")
