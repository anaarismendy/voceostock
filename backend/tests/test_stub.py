from uuid import uuid4

from app.pipeline.core import ContextoBodega, PayloadConteo, procesar_conteo

CTX = ContextoBodega(bodega_id=13)


def _payload(texto: str | None = None, audio: str | None = None) -> PayloadConteo:
    return PayloadConteo(
        sesion_id=uuid4(),
        bodega_id=13,
        operario_id=uuid4(),
        fuente="voz-tablet",
        payload_texto=texto,
        payload_audio_b64=audio,
    )


async def test_anomalia():
    r = await procesar_conteo(_payload("noventa cajas de cazuelas"), CTX)
    assert r.status == "requiere_confirmacion"
    assert r.motivo == "anomalia"
    assert r.pregunta == "¿Confirmas 90? El corte anterior registró 10."


async def test_ambiguedad():
    r = await procesar_conteo(_payload("cazuela sola"), CTX)
    assert r.status == "requiere_confirmacion"
    assert r.motivo == "ambiguedad"
    assert [c.articulo_nombre for c in r.candidatos] == [
        "CAZUELA 16 ONZ",
        "CALDERO RECORT TAPA 50X60 CM",
    ]


async def test_no_catalogado():
    r = await procesar_conteo(_payload("producto xyz"), CTX)
    assert r.status == "no_catalogado"
    assert r.texto_capturado == "producto xyz"


async def test_confirmado_texto():
    r = await procesar_conteo(_payload("treinta y tres litros de aceite de oliva"), CTX)
    assert r.status == "confirmado"
    assert r.unidad == "Liter"
    assert r.confianza == 0.95


async def test_confirmado_audio():
    r = await procesar_conteo(_payload(audio="ZmFrZSBhdWRpbw=="), CTX)
    assert r.status == "confirmado"
    assert r.articulo_id == 7290
