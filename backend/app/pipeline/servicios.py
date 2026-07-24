"""Orquestador del pipeline y su fábrica configurable por entorno.

`Pipeline.procesar` es el flujo real: parsear → matchear → validar anomalías →
traducir al `ResultadoPipeline` congelado. `get_pipeline()` lo arma según el
entorno (Gemini vs replay, BD vs CSV) para que `core.procesar_conteo` no tenga
que saber nada de esa configuración.

Variables de entorno:
- PIPELINE_MODE = live | replay | auto (auto: live si hay GEMINI_API_KEY).
- PIPELINE_DATA = db | csv | auto (auto: db si hay DATABASE_URL).
- REPLAY_DIR    = carpeta de respuestas grabadas de NLU (modo replay/demo A10).
"""

import base64
import os
from pathlib import Path

from app.pipeline.anomalias.reglas import evaluar
from app.pipeline.core import Candidato, ContextoBodega, PayloadConteo, ResultadoPipeline
from app.pipeline.datos.repos import RepoCatalogo, RepoCSV
from app.pipeline.matching.embeddings import Embedder, EmbedderLexico
from app.pipeline.matching.matcher import match
from app.pipeline.nlu.cliente import ClienteNLU, ClienteReplay
from app.pipeline.nlu.parser import parse_conteo
from app.pipeline.tipos import ConteoParseado

RAIZ = Path(__file__).resolve().parents[3]
REPLAY_DIR_DEFECTO = RAIZ / "data" / "replay" / "nlu"
CACHE_EMB_DEFECTO = RAIZ / "data" / "fixtures" / "embeddings.pkl"


class Pipeline:
    """Cerebro completo: NLU + matching + anomalías sobre un origen de datos."""

    def __init__(self, nlu: ClienteNLU, embedder: Embedder, repo: RepoCatalogo):
        self.nlu = nlu
        self.embedder = embedder
        self.repo = repo

    def _parsear(self, payload: PayloadConteo) -> ConteoParseado:
        audio = base64.b64decode(payload.payload_audio_b64) if payload.payload_audio_b64 else None
        return parse_conteo(payload.payload_texto, audio, cliente=self.nlu)

    def procesar(self, payload: PayloadConteo, contexto: ContextoBodega) -> ResultadoPipeline:
        parse = self._parsear(payload)
        articulos = self.repo.catalogo(contexto.bodega_id)
        resultado = match(parse.articulo_texto, articulos, embedder=self.embedder)

        if resultado.tipo == "no_catalogado":
            return ResultadoPipeline(
                status="no_catalogado",
                texto_capturado=parse.articulo_texto,
                cantidad=parse.cantidad,
                unidad=parse.unidad_normalizada,
            )

        if resultado.tipo == "ambiguedad":
            return ResultadoPipeline(
                status="requiere_confirmacion",
                motivo="ambiguedad",
                pregunta="¿Cuál artículo es?",
                candidatos=[
                    Candidato(articulo_id=c.articulo_id, articulo_nombre=c.nombre)
                    for c in resultado.candidatos
                ],
            )

        art = resultado.articulo
        # Artículo resuelto pero sin cantidad: pedirla (no inventarla).
        if parse.cantidad is None:
            return ResultadoPipeline(
                status="requiere_confirmacion",
                motivo="ambiguedad",
                articulo_id=art.articulo_id,
                articulo_nombre=art.nombre,
                pregunta=parse.ambiguedad or f"¿Qué cantidad de {art.nombre} contaste?",
            )

        anomalia = evaluar(parse, art)
        if anomalia.flag:
            motivo = "baja_confianza" if anomalia.tipo == "baja_confianza" else "anomalia"
            return ResultadoPipeline(
                status="requiere_confirmacion",
                motivo=motivo,
                articulo_id=art.articulo_id,
                articulo_nombre=art.nombre,
                cantidad=parse.cantidad,
                unidad=_unidad_final(parse, art),
                pregunta=anomalia.pregunta,
            )

        return ResultadoPipeline(
            status="confirmado",
            articulo_id=art.articulo_id,
            articulo_nombre=art.nombre,
            cantidad=parse.cantidad,
            unidad=_unidad_final(parse, art),
            confianza=parse.confianza,
        )


def _unidad_final(parse: ConteoParseado, art) -> str | None:
    """La unidad dicha manda; si no se dijo, la del catálogo (si es canónica)."""
    if parse.unidad_normalizada:
        return parse.unidad_normalizada
    if art.unidad_base in ("Unidad", "Kilogram", "Liter", "Portion"):
        return art.unidad_base
    return None


# --- fábrica configurable por entorno ---

_pipeline: Pipeline | None = None


def _modo() -> str:
    modo = os.environ.get("PIPELINE_MODE", "auto").lower()
    if modo == "auto":
        return "live" if os.environ.get("GEMINI_API_KEY") else "replay"
    return modo


def _data() -> str:
    data = os.environ.get("PIPELINE_DATA", "auto").lower()
    if data == "auto":
        return "db" if os.environ.get("DATABASE_URL") else "csv"
    return data


def construir_pipeline() -> Pipeline:
    """Arma un Pipeline nuevo según el entorno. Sin efectos globales."""
    if _modo() == "live":
        api_key = os.environ["GEMINI_API_KEY"]
        from app.pipeline.matching.embeddings import EmbedderGemini
        from app.pipeline.nlu.cliente import ClienteGemini

        nlu: ClienteNLU = ClienteGemini(api_key=api_key)
        embedder: Embedder = EmbedderGemini(api_key=api_key, ruta_cache=CACHE_EMB_DEFECTO)
    else:
        replay_dir = Path(os.environ.get("REPLAY_DIR", REPLAY_DIR_DEFECTO))
        nlu = ClienteReplay(replay_dir)
        embedder = EmbedderLexico()

    if _data() == "db":
        from sqlalchemy import create_engine

        from app.pipeline.datos.repos import RepoDB

        repo: RepoCatalogo = RepoDB(create_engine(os.environ["DATABASE_URL"]))
    else:
        repo = RepoCSV()

    return Pipeline(nlu, embedder, repo)


def get_pipeline() -> Pipeline:
    """Singleton perezoso. `configurar_pipeline`/`reset_pipeline` para pruebas."""
    global _pipeline
    if _pipeline is None:
        _pipeline = construir_pipeline()
    return _pipeline


def configurar_pipeline(pipeline: Pipeline) -> None:
    global _pipeline
    _pipeline = pipeline


def reset_pipeline() -> None:
    global _pipeline
    _pipeline = None
