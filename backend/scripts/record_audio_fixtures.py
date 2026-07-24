"""Genera fixtures de replay para la ruta de AUDIO del guion de demo.

El replay de NLU indexa los audios por hash de bytes (`audio-<sha1[:16]>`),
así que un audio recién grabado jamás matchea un fixture viejo. Este script
cierra ese hueco para el guion de demo:

1. Graba cada frase del guion con cualquier grabadora y guarda el archivo en
   `data/replay/audio/` con el SLUG de la frase como nombre:
       treinta-y-tres-litros-de-aceite-de-oliva.webm
       noventa-cajas-de-cazuelas.webm
       una-cazuela.webm
       siete-kilos-de-arroz-basmati.webm
2. Corre:  uv run python -m scripts.record_audio_fixtures
   Para cada archivo copia el fixture de TEXTO ya grabado del slug
   (`data/replay/nlu/<slug>.json`) a `data/replay/nlu/audio-<hash>.json`.
   Sin red y sin API key: el contenido del parse es el mismo que dictado.
3. En la demo, la ruta B debe enviar ESOS archivos (los bytes exactos).

Con `--live` (y GEMINI_API_KEY) ignora los fixtures de texto y le pide a
Gemini el parse real de cada audio — útil si la frase no tiene fixture.
"""

import json
import shutil
import sys
from hashlib import sha1
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

RAIZ = Path(__file__).resolve().parents[2]
DIR_AUDIO = RAIZ / "data" / "replay" / "audio"
DIR_NLU = RAIZ / "data" / "replay" / "nlu"
EXTENSIONES = (".webm", ".ogg", ".mp3", ".wav", ".m4a")


def clave_audio(datos: bytes) -> str:
    return "audio-" + sha1(datos).hexdigest()[:16]


def _fixture_live(ruta: Path) -> dict:
    import os

    from app.pipeline.nlu.cliente import ClienteGemini
    from app.pipeline.nlu.parser import parse_conteo

    cliente = ClienteGemini(api_key=os.environ["GEMINI_API_KEY"])
    parse = parse_conteo(None, ruta.read_bytes(), cliente=cliente)
    return parse.model_dump()


def main() -> None:
    live = "--live" in sys.argv
    audios = [p for p in sorted(DIR_AUDIO.glob("*")) if p.suffix.lower() in EXTENSIONES]
    if not audios:
        sys.exit(f"no hay audios en {DIR_AUDIO} (nómbralos con el slug de la frase)")

    for ruta in audios:
        destino = DIR_NLU / f"{clave_audio(ruta.read_bytes())}.json"
        if live:
            destino.write_text(
                json.dumps(_fixture_live(ruta), ensure_ascii=False, indent=2), "utf-8"
            )
            print(f"{ruta.name} → {destino.name} (live)")
            continue
        origen = DIR_NLU / f"{ruta.stem}.json"
        if not origen.exists():
            print(f"OJO: {ruta.name} sin fixture de texto {origen.name}; sáltalo o usa --live")
            continue
        shutil.copyfile(origen, destino)
        print(f"{ruta.name} → {destino.name} (copiado de {origen.name})")


if __name__ == "__main__":
    main()
