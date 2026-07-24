"""Embeddings: determinismo del léxico y caché en disco del de Gemini (A5)."""

from types import SimpleNamespace

import numpy as np

from app.pipeline.matching.embeddings import EmbedderGemini, EmbedderLexico


def test_lexico_determinista_y_normalizado():
    emb = EmbedderLexico()
    m1 = emb.embed(["cinta sellamiento", "caldero"])
    m2 = emb.embed(["cinta sellamiento", "caldero"])
    assert np.allclose(m1, m2)  # reproducible
    normas = np.linalg.norm(m1, axis=1)
    assert np.allclose(normas, 1.0)  # filas L2-normalizadas


class _ModelsFalso:
    """Cuenta llamadas y devuelve un vector fijo por texto."""

    def __init__(self):
        self.llamadas = 0

    def embed_content(self, model, contents, config=None):
        self.llamadas += 1
        return SimpleNamespace(
            embeddings=[SimpleNamespace(values=[float(len(c)), 1.0, 0.0]) for c in contents]
        )


class _ClienteFalso:
    def __init__(self):
        self.models = _ModelsFalso()


def test_gemini_cachea_en_disco_segunda_corrida_0_llamadas(tmp_path):
    cache = tmp_path / "emb.pkl"

    cliente1 = _ClienteFalso()
    emb1 = EmbedderGemini(api_key="x", ruta_cache=cache, cliente=cliente1)
    emb1.embed(["arroz", "aceite", "sal"])
    assert cliente1.models.llamadas == 1  # un lote
    assert cache.exists()

    # Segunda corrida: instancia nueva, mismo archivo de caché → 0 llamadas.
    cliente2 = _ClienteFalso()
    emb2 = EmbedderGemini(api_key="x", ruta_cache=cache, cliente=cliente2)
    emb2.embed(["arroz", "aceite", "sal"])
    assert cliente2.models.llamadas == 0


def test_gemini_solo_pide_los_faltantes(tmp_path):
    cliente = _ClienteFalso()
    emb = EmbedderGemini(api_key="x", ruta_cache=tmp_path / "emb.pkl", cliente=cliente)
    emb.embed(["arroz"])
    emb.embed(["arroz", "sal"])  # solo "sal" es nuevo
    assert cliente.models.llamadas == 2
