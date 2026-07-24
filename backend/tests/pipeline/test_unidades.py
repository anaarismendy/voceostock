"""Normalización de unidades a las 4 canónicas (regla INVIOLABLE)."""

import pytest

from app.pipeline.nlu.unidades import es_unidad_entera, normalizar_unidad


@pytest.mark.parametrize(
    "texto,esperada,factor",
    [
        ("kilo", "Kilogram", 1.0),
        ("kilos", "Kilogram", 1.0),
        ("kilito", "Kilogram", 1.0),
        ("kg", "Kilogram", 1.0),
        ("gramos", "Kilogram", 0.001),
        ("arroba", "Kilogram", 12.5),
        ("litros", "Liter", 1.0),
        ("lt", "Liter", 1.0),
        ("ml", "Liter", 0.001),
        ("paquete", "Unidad", 1.0),
        ("cajas", "Unidad", 1.0),
        ("unidades", "Unidad", 1.0),
        ("porción", "Portion", 1.0),
        ("porciones", "Portion", 1.0),
        ("Kilogram", "Kilogram", 1.0),  # ya canónica
    ],
)
def test_sinonimos(texto, esperada, factor):
    unidad, f = normalizar_unidad(texto)
    assert unidad == esperada
    assert f == pytest.approx(factor)


def test_desconocida_devuelve_none():
    assert normalizar_unidad("cucharadas") == (None, 1.0)
    assert normalizar_unidad(None) == (None, 1.0)


def test_unidad_entera():
    assert es_unidad_entera("Unidad")
    assert es_unidad_entera("Portion")
    assert not es_unidad_entera("Kilogram")
    assert not es_unidad_entera("Liter")
