"""TTS con caché en disco: hit sin API, miss sin key degrada con 503."""
# ruff: noqa: F811 — las fixtures importadas se "redefinen" como parámetros

from app.services import tts
from tests.test_api_conteos import _bootstrap_db, client  # noqa: F401


def test_hit_de_cache_sirve_del_disco_sin_llamar_api(client):
    frase = "33 Liter de ACEITE DE OLIVA"
    ruta = tts.ruta_cache(frase)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(b"mp3 falso para la prueba")

    antes = tts.llamadas_api
    r = client.post("/api/v1/tts", json={"texto": frase})
    assert r.status_code == 200
    assert r.headers["x-tts-cache"] == "hit"
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.content == b"mp3 falso para la prueba"
    assert tts.llamadas_api == antes  # 0 llamadas a ElevenLabs


def test_miss_sin_api_key_degrada_con_503(client):
    r = client.post("/api/v1/tts", json={"texto": "frase jamás cacheada 42"})
    assert r.status_code == 503  # el frontend cae a speechSynthesis


def test_el_hash_incluye_la_voz():
    import os

    clave_a = tts.clave("hola")
    os.environ["ELEVENLABS_VOICE_ID"] = "otra-voz"
    try:
        assert tts.clave("hola") != clave_a  # cambiar la voz invalida la caché
    finally:
        del os.environ["ELEVENLABS_VOICE_ID"]
