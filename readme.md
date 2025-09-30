Instalação Redis para Windows:

Primeiro, ative o WSL2 para rodar Linux no windows.

Instale Ubuntu na Microsoft Store

Com o Ubuntu aberto e configurado, digite os seguintes comandos:

sudo apt-get update

sudo apt-get install redis

Para rodar o servidor redis:

sudo service redis-server start

Para testar:    

redis-cli

Digite PING e, se funcionar, retornará PONG


Instalação Dependência redis:

poetry shell

poetry add redis

Rodar aplicação:

fastapi dev livrosapi.py

Insomnia:

Checar retorno dos endpoints.

No http://127.0.0.1:8000/livros POST, adicione uma requisição BODY no formato JSON da seguinte maneira:

{
	"nome_livro": "Harry Potter",
	"autor_livro": "J.K Rowling",
	"ano_livro": 2005 
}

Cheque no http://127.0.0.1:8000/livros GET o retorno da API.

Atualize informações com o método PUT da mesma maneira, especificando ID.

Delete informações através do método DELETE, especificando ID.

Celery:

Para instalar,

pip install celery

Testar endpoints no Insomnia 

HTTP 200 retornará:

{
	"task_id": "cc65bdf5-6d7f-4c04-a679-8fa701180fe5",
	"message": "Tarefa de soma enviada para execução!"
}

Depois:

Checar endpoint (ou log do celery) Resultado Celery para resultado das tarefas