"""Pipeline real de punta a punta a través de la firma CONGELADA (tarea A8).

Antes este archivo probaba el stub determinista de la Fase 0. En A8 el cuerpo de
`procesar_conteo` pasó a ser el pipeline real (NLU + matching + anomalías); estas
pruebas verifican ese pipeline en modo offline (replay de NLU + catálogo CSV),
sin red, contra los datos reales de `data/fixtures/`.
"""

from pathlib import Path
from uuid import uuid4

import pytest

from app.pipeline.core import ContextoBodega, PayloadConteo, procesar_conteo
from app.pipeline.datos.repos import RepoCSV
from app.pipeline.matching.embeddings import EmbedderLexico
from app.pipeline.nlu.cliente import ClienteReplay
from app.pipeline.servicios import Pipeline, configurar_pipeline, reset_pipeline

REPLAY_DEMO = Path(__file__).resolve().parents[2] / "data" / "replay" / "nlu"
BODEGA = 3  # "almacen general" — tiene cazuela (SD 10), arroz, aceite de oliva


@pytest.fixture(autouse=True)
def pipeline_offline():
    configurar_pipeline(
        Pipeline(ClienteReplay(REPLAY_DEMO), EmbedderLexico(), RepoCSV())
    )
    yield
    reset_pipeline()


def _payload(texto: str | None = None, audio: str | None = None) -> PayloadConteo:
    return PayloadConteo(
        sesion_id=uuid4(), bodega_id=BODEGA, operario_id=uuid4(),
        fuente="voz-tablet", payload_texto=texto, payload_audio_b64=audio,
    )


async def _procesar(texto: str):
    return await procesar_conteo(_payload(texto), ContextoBodega(bodega_id=BODEGA))


async def test_confirmado():
    r = await _procesar("cincuenta kilos de arroz")
    assert r.status == "confirmado"
    assert r.articulo_nombre == "ARROZ"
    assert r.cantidad == 50
    assert r.unidad == "Kilogram"


async def test_anomalia_calculada_del_sd_real():
    r = await _procesar("noventa cajas de cazuelas")
    assert r.status == "requiere_confirmacion"
    assert r.motivo == "anomalia"
    assert r.articulo_nombre == "CAZUELA 16 ONZ"
    assert r.pregunta and "90" in r.pregunta


async def test_orden_de_magnitud_revela_el_saldo_del_ultimo_corte():
    """Decisión de producto (reto Colsubsidio): la pregunta de una anomalía de
    orden de magnitud SÍ cita el saldo anterior — la cazuela tiene SD 10."""
    r = await _procesar("noventa cajas de cazuelas")
    assert r.pregunta == "¿Confirmas 90? El corte anterior registró 10."


async def test_ambiguedad():
    r = await _procesar("una cazuela")
    assert r.status == "requiere_confirmacion"
    assert r.motivo == "ambiguedad"
    nombres = [c.articulo_nombre for c in r.candidatos]
    assert "CAZUELA 16 ONZ" in nombres and "TAPA CAZUELA 16 ONZ" in nombres


async def test_no_catalogado():
    r = await _procesar("diez destornilladores")
    assert r.status == "no_catalogado"
    assert r.texto_capturado == "destornillador"


async def test_baja_confianza():
    r = await _procesar("eh como catorce cintas de sellamiento")
    assert r.status == "requiere_confirmacion"
    assert r.motivo == "baja_confianza"
