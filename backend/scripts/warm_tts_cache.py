"""Pre-genera y cachea la voz de TODO el guion de demo (docs/DEMO.md).

    ELEVENLABS_API_KEY=... uv run python -m scripts.warm_tts_cache

Los .mp3 quedan en data/tts_cache/ (indexados por hash de modelo:voz:texto)
y SE COMMITEAN: la demo habla con la voz de ElevenLabs sin red y sin key.
Re-correrlo con la caché caliente hace 0 llamadas a la API. Si cambias
ELEVENLABS_VOICE_ID, el hash cambia y se regenera todo.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import tts

# Todo lo que la app dice en voz alta durante el guion (docs/DEMO.md):
# confirmaciones "cantidad unidad de ARTICULO", preguntas de anomalía con los
# valores del guion, ambigüedad, y las plantillas fijas de la UI.
FRASES_GUION = [
    # Confirmaciones (mensajeConfirmacion) de los conteos del guion
    "33 Liter de ACEITE DE OLIVA",
    "90 Unidad de CAZUELA 16 ONZ",
    "1 Unidad de CAZUELA 16 ONZ",
    "7 Kilogram de ARROZ BASMATI",
    "12 Kilogram de POLLO ENTERO",
    "5 Unidad de ABRELATAS MARIPOSA",
    # Las 5 preguntas de anomalía con los valores del guion
    "¿Confirmas 90 unidades de CAZUELA 16 ONZ? El corte anterior registró 10.",
    "¿Confirmas 12 kilos de POLLO ENTERO? El corte anterior registró 1596,2.",
    "Contaste ACEITE DE OLIVA en kilos, pero suele medirse en litros. ¿Es correcto?",
    "Registraste 3,5 de CAZUELA 16 ONZ, pero este artículo se cuenta por unidades enteras. ¿Seguro?",
    "Registraste cero de POLLO ENTERO, pero es un artículo del que suele haber bastante. ¿Confirmas que no queda ninguno?",
    "No estoy seguro de haber entendido bien. ¿Contaste 14 unidades de CINTA SELLAMIENTO 48 MM X 50 MTS?",
    # Ambigüedad y plantillas fijas de la UI
    "¿Cuál artículo es?",
    "¿Correcto?",
    "Conteo descartado",
    "Descartado. Puedes dictar el siguiente conteo.",
    "No pude entender. Usa el teclado o repite el conteo.",
    'No encontré "flurbos galacticos" en el catálogo de esta bodega.',
]


def main() -> None:
    hits = misses = 0
    t0 = time.perf_counter()
    for frase in FRASES_GUION:
        _, hit = tts.sintetizar(frase)
        hits += hit
        misses += not hit
        print(f"{'HIT ' if hit else 'MISS'} {tts.clave(frase)[:12]}  {frase[:60]}")
    dt = time.perf_counter() - t0
    print(
        f"\n{len(FRASES_GUION)} frases: {hits} en caché, {misses} generadas "
        f"({tts.llamadas_api} llamadas a la API) — {dt:.1f}s"
    )
    print(f"caché en {tts._dir_cache()}")


if __name__ == "__main__":
    main()
