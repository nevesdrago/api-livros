from celery_app import celery_app
import time
import math

@celery_app.task(bind=True)
def calcular_soma(self, a: int, b: int):
    time.sleep(3)
    return a + b
    

@celery_app.task(bind=True)
def calcular_fatorial(self, a: int):
    if a < 0:
        return "Valor inválido"
    time.sleep(3)
    return math.factorial(a)

