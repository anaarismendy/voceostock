"""Fallback del TTS (Fase 2 — E3), a nivel de servicio (sin BD).

DoD: con ElevenLabs caído O lento, `sintetizar` levanta TTSNoDisponible → el
endpoint responde 503 → el frontend cae a speechSynthesis. Un hit de caché sigue
funcionando sin tocar la API. El timeout es corto y configurable.

Los tests de endpoint (tests/test_api_tts.py) necesitan BD; estos prueban la
lógica de degradación sin Postgres.
"""

import httpx
import pytest

from app.services import tts


def test_timeout_corto_y_configurable(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_TIMEOUT", raising=False)
    assert tts._timeout() == tts.TIMEOUT_DEFECTO
    assert tts._timeout() <= 3.0  # camino en vivo: no bloquea la confirmación
    monkeypatch.setenv("ELEVENLABS_TIMEOUT", "1.0")
    assert tts._timeout() == 1.0


def test_elevenlabs_lento_degrada(monkeypatch, tmp_path):
    monkeypatch.setenv("TTS_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")  # fuerza el intento de llamada

    def _lento(*args, **kwargs):
        raise httpx.TimeoutException("ElevenLabs no respondió a tiempo")

    monkeypatch.setattr(tts.httpx, "post", _lento)
    with pytest.raises(tts.TTSNoDisponible):
        tts.sintetizar("frase no cacheada para el timeout 42")


def test_elevenlabs_caido_degrada(monkeypatch, tmp_path):
    monkeypatch.setenv("TTS_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")

    def _caido(*args, **kwargs):
        raise httpx.ConnectError("conexión rechazada")

    monkeypatch.setattr(tts.httpx, "post", _caido)
    with pytest.raises(tts.TTSNoDisponible):
        tts.sintetizar("otra frase no cacheada 99")


def test_sin_api_key_degrada(monkeypatch, tmp_path):
    monkeypatch.setenv("TTS_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(tts.TTSNoDisponible):
        tts.sintetizar("miss sin key jamás cacheado")


def test_hit_de_cache_no_llama_a_la_api(monkeypatch, tmp_path):
    monkeypatch.setenv("TTS_CACHE_DIR", str(tmp_path))

    def _no_debe_llamar(*args, **kwargs):
        raise AssertionError("un hit no debe tocar la API")

    monkeypatch.setattr(tts.httpx, "post", _no_debe_llamar)
    frase = "33 Liter de ACEITE DE OLIVA"
    tts.ruta_cache(frase).write_bytes(b"mp3 de prueba")

    audio, hit = tts.sintetizar(frase)
    assert hit is True
    assert audio == b"mp3 de prueba"
