"""Embeddings para el matching semántico (tareas A4 y A5).

Dos implementaciones tras el mismo protocolo `Embedder`:
- `EmbedderLexico`: hashing de n-gramas de caracteres. Determinista, sin red;
  es el que usa CI y el modo offline. Su geometría coseno es distinta a la de un
  modelo neuronal, por eso declara SU PROPIO umbral (más bajo).
- `EmbedderGemini`: gemini-embedding-001 real, por lotes, con reintentos y caché
  en disco. La segunda corrida sobre el mismo catálogo hace 0 llamadas a la API.

Cada embedder trae su `umbral`/`margen` porque el coseno no es comparable entre
espacios: 0.80 es "cercano" en Gemini, no en el léxico. Mantener el umbral con
el embedder evita el bug de aplicar el número de un modelo al otro.
"""

import hashlib
import pickle
import time
from pathlib import Path
from typing import Protocol

import numpy as np

from app.pipeline.normalizacion import normalizar

MODELO_EMBEDDING = "gemini-embedding-001"
DIM_GEMINI = 768


class Embedder(Protocol):
    umbral: float  # coseno mínimo para considerar "match" seguro
    margen: float  # separación mínima entre top-1 y top-2 para no ser ambiguo
    dim: int

    def embed(self, textos: list[str]) -> np.ndarray:
        """Devuelve una matriz (len(textos), dim) con filas L2-normalizadas."""
        ...


def _normalizar_filas(m: np.ndarray) -> np.ndarray:
    normas = np.linalg.norm(m, axis=1, keepdims=True)
    normas[normas == 0] = 1.0
    return m / normas


class EmbedderLexico:
    """Bolsa de n-gramas de caracteres (3 y 4) con hashing. Reproducible y sin
    dependencias externas. Captura similitud léxica (raíces compartidas), que es
    suficiente para 'cazuelas'→'cazuela 16 onz' pero no para sinónimos
    semánticos ('pegante'→'sellamiento'): para eso está EmbedderGemini."""

    def __init__(self, dim: int = 256, umbral: float = 0.62, margen: float = 0.05):
        self.dim = dim
        self.umbral = umbral
        self.margen = margen

    def _vector(self, texto: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float64)
        for token in normalizar(texto).split():
            envuelto = f" {token} "
            for n in (3, 4):
                for i in range(len(envuelto) - n + 1):
                    gram = envuelto[i : i + n]
                    h = int(hashlib.md5(gram.encode()).hexdigest(), 16)
                    v[h % self.dim] += 1.0
        return v

    def embed(self, textos: list[str]) -> np.ndarray:
        if not textos:
            return np.zeros((0, self.dim))
        return _normalizar_filas(np.vstack([self._vector(t) for t in textos]))


class EmbedderGemini:
    """Embeddings reales de gemini-embedding-001, con caché en disco.

    La caché va indexada por hash del nombre normalizado; re-embeber un catálogo
    ya visto no vuelve a llamar a la API (tarea A5). El archivo de caché está en
    .gitignore."""

    def __init__(
        self,
        api_key: str,
        ruta_cache: Path,
        dim: int = DIM_GEMINI,
        umbral: float = 0.80,
        margen: float = 0.05,
        lote: int = 100,
        reintentos: int = 3,
        pausa_lote: float = 0.0,
        cliente=None,
    ):
        # `cliente` inyectable para pruebas; en producción se crea el real.
        if cliente is None:
            from google import genai

            cliente = genai.Client(api_key=api_key)
        self._cliente = cliente
        self.ruta_cache = ruta_cache
        self.dim = dim
        self.umbral = umbral
        self.margen = margen
        self.lote = lote
        self.reintentos = reintentos
        self.pausa_lote = pausa_lote  # free tier: 100 items/min en embed_content
        self._cache: dict[str, list[float]] = self._cargar_cache()

    def _cargar_cache(self) -> dict[str, list[float]]:
        if self.ruta_cache.exists():
            return pickle.loads(self.ruta_cache.read_bytes())
        return {}

    def _guardar_cache(self) -> None:
        self.ruta_cache.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_cache.write_bytes(pickle.dumps(self._cache))

    @staticmethod
    def _clave(texto: str) -> str:
        return hashlib.sha1(normalizar(texto).encode()).hexdigest()

    def _embeber_lote(self, textos: list[str]) -> list[list[float]]:
        # output_dimensionality=768 para cuadrar con la columna Vector(768) de la
        # BD (gemini-embedding-001 devuelve 3072 por defecto). El SDK acepta el
        # config como dict, así que no hace falta importar google.genai aquí.
        config = {"output_dimensionality": self.dim}
        ultimo_error: Exception | None = None
        for intento in range(self.reintentos):
            try:
                resp = self._cliente.models.embed_content(
                    model=MODELO_EMBEDDING, contents=textos, config=config
                )
                return [list(e.values) for e in resp.embeddings]
            except Exception as e:  # noqa: BLE001 — reintentar con backoff
                ultimo_error = e
                time.sleep(2**intento)
        raise RuntimeError(f"embed_content falló tras {self.reintentos} intentos") from ultimo_error

    def embed(self, textos: list[str]) -> np.ndarray:
        faltantes = [t for t in textos if self._clave(t) not in self._cache]
        # Deduplicar preservando orden.
        faltantes = list(dict.fromkeys(faltantes))
        if faltantes:
            for i in range(0, len(faltantes), self.lote):
                if i and self.pausa_lote:
                    time.sleep(self.pausa_lote)
                trozo = faltantes[i : i + self.lote]
                for texto, vector in zip(trozo, self._embeber_lote(trozo)):
                    self._cache[self._clave(texto)] = vector
                # guardar por lote: un 429 a mitad de camino no pierde lo hecho
                self._guardar_cache()
        return _normalizar_filas(np.array([self._cache[self._clave(t)] for t in textos]))
