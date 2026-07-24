"""Tipos internos del pipeline (NLU → matching → anomalías).

Son distintos de los tipos CONGELADOS de `core.py` y de los schemas del
contrato (`app/schemas/conteos.py`): estos son el lenguaje interno del cerebro;
`core.py` los traduce al `ResultadoPipeline` congelado al final.
"""

from typing import Literal

from pydantic import BaseModel, Field

UnidadCanonica = Literal["Unidad", "Kilogram", "Liter", "Portion"]


class Empaque(BaseModel):
    """Conteo expresado por empaque: "una caja y tres sueltas".

    La conversión a unidad base necesita `factor_empaque` del artículo
    (cuántas unidades trae la caja). Ver docs/factor_empaque.md."""

    cajas: float = 0.0
    sueltas: float = 0.0


class ConteoParseado(BaseModel):
    """Salida del parser NLU (tarea A1). Lo que el operario *dijo*, entendido."""

    articulo_texto: str
    cantidad: float | None = None
    unidad_texto: str | None = None
    unidad_normalizada: UnidadCanonica | None = None
    hubo_correccion: bool = False
    confianza: float = Field(ge=0.0, le=1.0, default=1.0)
    ambiguedad: str | None = None
    empaque: Empaque | None = None


class ArticuloCtx(BaseModel):
    """Un artículo del catálogo de una bodega, con su contexto de validación.

    `sd` (stock teórico) vive aquí porque el motor de anomalías lo necesita,
    pero NUNCA se serializa hacia el operario (conteo ciego)."""

    articulo_id: int
    nr_articulo: int | None = None
    nombre: str
    nombre_normalizado: str
    unidad_base: str
    sd: float
    factor_empaque: float | None = None
    embedding: list[float] | None = None


MetodoMatch = Literal["exacto", "fuzzy", "embedding", "ninguno"]
TipoMatch = Literal["match", "ambiguedad", "no_catalogado"]


class ResultadoMatch(BaseModel):
    """Salida del matcher en cascada (tarea A4)."""

    tipo: TipoMatch
    articulo: ArticuloCtx | None = None
    candidatos: list[ArticuloCtx] = Field(default_factory=list)
    score: float = 0.0
    metodo: MetodoMatch = "ninguno"

    model_config = {"arbitrary_types_allowed": True}


TipoAnomalia = Literal[
    "ratio_sd",
    "unidad_incoherente",
    "decimal_en_entero",
    "cero_sospechoso",
    "baja_confianza",
]


class Anomalia(BaseModel):
    """Salida del motor de anomalías (tarea A6). `pregunta` en español natural."""

    flag: bool
    tipo: TipoAnomalia | None = None
    pregunta: str | None = None
