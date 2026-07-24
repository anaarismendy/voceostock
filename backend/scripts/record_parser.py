"""Regraba las fixtures de NLU llamando a Gemini real (tarea A2).

    GEMINI_API_KEY=... python -m scripts.record_parser --record

Sin --record solo lista qué grabaría. Persiste la respuesta CRUDA del parser
(antes de la red de seguridad de unidades) para que el modo replay y CI la
reproduzcan sin red.
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.nlu.cliente import ClienteGemini, clave_replay
from app.pipeline.nlu.parser import cargar_prompt
from app.pipeline.tipos import ConteoParseado

RAIZ = Path(__file__).resolve().parents[2]
DIR_A2 = RAIZ / "backend" / "tests" / "fixtures" / "nlu"
DIR_DEMO = RAIZ / "data" / "replay" / "nlu"

CASOS_A2 = [
    "cincuenta kilos de arroz", "medio kilo de sal", "kilo y medio de harina",
    "treinta y tres litros y medio de aceite", "noventa cajas de cazuelas",
    "nueve, no espera, diecinueve unidades de plato blanco", "una arroba de papa",
    "tres cuartos de litro de esencia", "doscientas unidades de vaso",
    "dos porciones de arroz preparado", "mmm eeh cinta pegante como catorce",
    "cero unidades de caldero", "hay harto ibuprofeno",
    "tres coma cinco litros de leche", "diez kilitos de azúcar",
]
CASOS_DEMO = [
    "cincuenta kilos de arroz", "treinta y tres litros de aceite de oliva",
    "diez unidades de cinta de sellamiento", "noventa cajas de cazuelas",
    "una cazuela", "diez destornilladores", "eh como catorce cintas de sellamiento",
]


def grabar(cliente: ClienteGemini, textos: list[str], destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for texto in textos:
        crudo = cliente.parsear(
            sistema=cargar_prompt(), texto=texto, audio_bytes=None,
            mime_audio="audio/ogg", esquema=ConteoParseado,
        )
        ruta = destino / f"{clave_replay(texto, None)}.json"
        ruta.write_text(crudo.model_dump_json(indent=2), encoding="utf-8")
        print(f"  grabado  {texto!r}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--record", action="store_true", help="grabar de verdad (llama a Gemini)")
    args = p.parse_args()

    todos = sorted(set(CASOS_A2) | set(CASOS_DEMO))
    if not args.record:
        print("Casos que se grabarían (usa --record para ejecutar):")
        for t in todos:
            print(f"  {t!r}")
        return

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY no configurada")
    cliente = ClienteGemini(api_key=key)
    print(f"Grabando {len(CASOS_A2)} casos A2 → {DIR_A2}")
    grabar(cliente, CASOS_A2, DIR_A2)
    print(f"Grabando {len(CASOS_DEMO)} casos demo → {DIR_DEMO}")
    grabar(cliente, CASOS_DEMO, DIR_DEMO)
    print("Listo.")


if __name__ == "__main__":
    main()
