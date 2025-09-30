from tasks import calcular_fatorial, calcular_soma
import pytest

def test_calcular_soma_retorna_soma():
    resultado = calcular_soma.apply(args=[5,3]).get()
    assert resultado == 8

def test_calcular_fatorial_retorna_fatorial():
    resultado = calcular_fatorial.apply(args=[5]).get()
    assert resultado == 120

def test_calcular_fatorial_zero():
    resultado = calcular_fatorial.apply(args=[0]).get()
    assert resultado == 1



