"""CLI de demo e iteración del pipeline (tarea A7).

    python cli.py "noventa cajas de cazuelas" --bodega "almacen general"
    python cli.py --audio conteo.ogg --bodega "almacen general"

Imprime el flujo completo: parser NLU → matching → anomalías → resultado del
contrato. Sin GEMINI_API_KEY usa el modo replay (respuestas grabadas, sin red);
con la key llama a Gemini real. Es la herramienta de iteración diaria y el
material de demo de emergencia.
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.pipeline.anomalias.reglas import evaluar
from app.pipeline.datos.repos import RepoCSV
from app.pipeline.matching.embeddings import EmbedderLexico
from app.pipeline.matching.matcher import match
from app.pipeline.nlu.parser import parse_conteo

REPLAY_DIR = Path(__file__).resolve().parents[1] / "data" / "replay" / "nlu"

# La consola de Windows suele venir en cp1252 y no puede imprimir '─'/'✓'.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
VERDE, AMARILLO, ROJO, GRIS, FIN = (
    ("\033[92m", "\033[93m", "\033[91m", "\033[90m", "\033[0m") if _COLOR else ("",) * 5
)


def _construir_nlu_y_embedder():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        from app.pipeline.matching.embeddings import EmbedderGemini
        from app.pipeline.nlu.cliente import ClienteGemini

        cache = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "embeddings.pkl"
        return ClienteGemini(api_key=key), EmbedderGemini(api_key=key, ruta_cache=cache), "Gemini"
    replay = Path(os.environ.get("REPLAY_DIR", REPLAY_DIR))
    from app.pipeline.nlu.cliente import ClienteReplay

    return ClienteReplay(replay), EmbedderLexico(), "replay (sin red)"


def _titulo(t: str) -> None:
    print(f"\n{GRIS}── {t} ──{FIN}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("texto", nargs="?", help="lo que dice el operario")
    p.add_argument("--bodega", required=True, help="nombre de la bodega (ej: 'almacen general')")
    p.add_argument("--audio", type=Path, help="archivo de audio (ogg/webm/wav)")
    args = p.parse_args()

    if not args.texto and not args.audio:
        p.error("da un texto o un --audio")

    nlu, embedder, modo = _construir_nlu_y_embedder()
    audio_bytes = args.audio.read_bytes() if args.audio else None
    print(f"{GRIS}modo NLU: {modo}  |  bodega: {args.bodega!r}{FIN}")

    _titulo("1. Parser NLU")
    parse = parse_conteo(args.texto, audio_bytes, cliente=nlu)
    print(json.dumps(parse.model_dump(), ensure_ascii=False, indent=2))

    _titulo("2. Matching de artículo")
    catalogo = RepoCSV().catalogo_por_nombre(args.bodega)
    if not catalogo:
        print(f"{ROJO}bodega sin catálogo en los fixtures{FIN}")
        return
    m = match(parse.articulo_texto, catalogo, embedder=embedder)
    if m.tipo == "match":
        print(f"{VERDE}✓ {m.articulo.nombre}{FIN}  (método {m.metodo}, score {m.score:.2f})")
    elif m.tipo == "ambiguedad":
        print(f"{AMARILLO}? ambigüedad ({m.metodo}) — candidatos:{FIN}")
        for c in m.candidatos:
            print(f"    · {c.nombre}")
    else:
        print(f"{ROJO}✗ no catalogado{FIN}")

    _titulo("3. Anomalías")
    if m.tipo == "match" and parse.cantidad is not None:
        anomalia = evaluar(parse, m.articulo)
        if anomalia.flag:
            print(f"{AMARILLO}⚠ {anomalia.tipo}{FIN}")
            print(f"    pregunta: {anomalia.pregunta}")
        else:
            print(f"{VERDE}sin anomalías{FIN}")
    else:
        print(f"{GRIS}(no aplica: primero hay que resolver artículo/cantidad){FIN}")


if __name__ == "__main__":
    main()
