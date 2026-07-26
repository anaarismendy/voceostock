"""Modelos SQLAlchemy — espejo del modelo de datos de la Fase 1."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

UNIDADES_CANONICAS = ("Unidad", "Kilogram", "Liter", "Portion")
FUENTES = ("voz-tablet", "whatsapp", "manual", "rfid", "bascula")


class Base(DeclarativeBase):
    pass


class Sede(Base):
    """Agrupa varias bodegas de un mismo sitio físico (Fase 2 — punto 0). El
    aprendizaje de sinónimos se llavea por sede, no por bodega, para compartir
    entre bodegas del mismo lugar."""

    __tablename__ = "sedes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(Text)
    nombre_normalizado: Mapped[str] = mapped_column(Text, unique=True)


class Bodega(Base):
    __tablename__ = "bodegas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(Text)
    nombre_normalizado: Mapped[str] = mapped_column(Text, unique=True)
    alias: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    # Fase 2: a qué sede pertenece (nullable; se asigna en E1/ingesta).
    sede_id: Mapped[int | None] = mapped_column(ForeignKey("sedes.id"))


class Articulo(Base):
    __tablename__ = "articulos"
    __table_args__ = (
        Index(
            "ux_articulos_nr_articulo",
            "nr_articulo",
            unique=True,
            postgresql_where=text("nr_articulo IS NOT NULL"),
        ),
        Index("ix_articulos_nombre_normalizado", "nombre_normalizado"),
        CheckConstraint(
            "unidad_base IN ('Unidad','Kilogram','Liter','Portion')",
            name="ck_articulos_unidad_base",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nr_articulo: Mapped[int | None] = mapped_column(BigInteger)
    nombre: Mapped[str] = mapped_column(Text)
    nombre_normalizado: Mapped[str] = mapped_column(Text)
    unidad_base: Mapped[str] = mapped_column(Text)
    familia: Mapped[str | None] = mapped_column(Text)
    factor_empaque: Mapped[Decimal | None] = mapped_column(Numeric)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))


class StockTeorico(Base):
    __tablename__ = "stock_teorico"

    bodega_id: Mapped[int] = mapped_column(ForeignKey("bodegas.id"), primary_key=True)
    articulo_id: Mapped[int] = mapped_column(ForeignKey("articulos.id"), primary_key=True)
    sd: Mapped[Decimal] = mapped_column(Numeric)
    corte_fecha: Mapped[date] = mapped_column(
        Date, primary_key=True, server_default=text("CURRENT_DATE")
    )
    orden_original: Mapped[int]


class Operario(Base):
    __tablename__ = "operarios"
    __table_args__ = (
        CheckConstraint("rol IN ('operario','auditor','lider')", name="ck_operarios_rol"),
        # El PIN identifica al operario: duplicarlo hace que el login devuelva
        # una fila al azar y parte en dos su historial de precisión (D5).
        Index("ux_operarios_pin", "pin", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    nombre: Mapped[str] = mapped_column(Text)
    # ponytail: PIN en claro. NO es una credencial: 4 dígitos son 10.000 combos,
    # hashearlos es teatro (una rainbow table completa se arma en milisegundos).
    # Identifica, no autentica. Auth real = otro factor, no un hash aquí.
    pin: Mapped[str] = mapped_column(Text)
    rol: Mapped[str | None] = mapped_column(Text)
    telefono: Mapped[str | None] = mapped_column(Text)


class Inventario(Base):
    """Un ciclo de conteo completo de una bodega: "Inventario #2, del 25 al 26
    de julio". Agrupa las sesiones (una por operario) para que el cierre compare
    UN ciclo contra el SD, y no la suma histórica de todo lo contado nunca.

    El `numero` es consecutivo POR bodega, para que el líder diga "el 2" y sea
    el 2 de SU bodega."""

    __tablename__ = "inventarios"
    __table_args__ = (
        CheckConstraint("estado IN ('abierto','cerrado')", name="ck_inventarios_estado"),
        # Dos inventarios abiertos a la vez en una bodega volverían a mezclar los
        # conteos: es justo lo que esta tabla existe para evitar.
        Index(
            "ux_inventarios_bodega_abierto",
            "bodega_id",
            unique=True,
            postgresql_where=text("estado = 'abierto'"),
        ),
        Index("ux_inventarios_bodega_numero", "bodega_id", "numero", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bodega_id: Mapped[int] = mapped_column(ForeignKey("bodegas.id"))
    numero: Mapped[int]
    estado: Mapped[str] = mapped_column(Text, server_default=text("'abierto'"))
    # Contra qué corte del ERP se compara este ciclo (stock_teorico.corte_fecha).
    # NULL = el corte más reciente de la bodega.
    corte_fecha: Mapped[date | None] = mapped_column(Date)
    abierto_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    cerrado_en: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class SesionConteo(Base):
    __tablename__ = "sesiones_conteo"
    __table_args__ = (
        CheckConstraint("tipo IN ('primario','auditoria')", name="ck_sesiones_tipo"),
        CheckConstraint(
            "estado IN ('abierta','pausada','cerrada')", name="ck_sesiones_estado"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    bodega_id: Mapped[int] = mapped_column(ForeignKey("bodegas.id"))
    # A qué ciclo pertenece esta sesión. Nullable por las sesiones anteriores a
    # la migración 0010 (el backfill las engancha al Inventario #1).
    inventario_id: Mapped[int | None] = mapped_column(ForeignKey("inventarios.id"))
    operario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("operarios.id"))
    tipo: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Text, server_default=text("'abierta'"))
    iniciada_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    cerrada_en: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class Conteo(Base):
    """Append-only: una corrección crea un registro nuevo con supersede_id.

    Nunca UPDATE de cantidad (regla de CLAUDE.md)."""

    __tablename__ = "conteos"
    __table_args__ = (
        CheckConstraint(
            "unidad IN ('Unidad','Kilogram','Liter','Portion')", name="ck_conteos_unidad"
        ),
        CheckConstraint(
            "fuente IN ('voz-tablet','whatsapp','manual','rfid','bascula')",
            name="ck_conteos_fuente",
        ),
        # Evita duplicados activos dentro de una sesión; entre sesiones no bloquea.
        Index(
            "ux_conteos_sesion_articulo_activo",
            "sesion_id",
            "articulo_id",
            unique=True,
            postgresql_where=text("activo = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sesion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sesiones_conteo.id"))
    articulo_id: Mapped[int | None] = mapped_column(ForeignKey("articulos.id"))
    texto_capturado: Mapped[str | None] = mapped_column(Text)
    cantidad: Mapped[Decimal] = mapped_column(Numeric)
    unidad: Mapped[str] = mapped_column(Text)
    fuente: Mapped[str] = mapped_column(Text)
    payload_crudo: Mapped[str | None] = mapped_column(Text)
    confianza: Mapped[Decimal | None] = mapped_column(Numeric)
    anomalia_flag: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    anomalia_tipo: Mapped[str | None] = mapped_column(Text)
    anomalia_resuelta: Mapped[bool | None] = mapped_column(Boolean)
    supersede_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conteos.id"))
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    evidencia_url: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class TokenPendiente(Base):
    """Captura en espera de confirmación humana (B5). Expira a los 10 min."""

    __tablename__ = "tokens_pendientes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    sesion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sesiones_conteo.id"))
    payload_original: Mapped[dict] = mapped_column(JSONB)
    resultado_pipeline: Mapped[dict] = mapped_column(JSONB)
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    expira_en: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    resuelto: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class AliasArticulo(Base):
    __tablename__ = "alias_articulos"

    articulo_id: Mapped[int] = mapped_column(ForeignKey("articulos.id"), primary_key=True)
    alias: Mapped[str] = mapped_column(Text, primary_key=True)


class UmbralConfianza(Base):
    """Umbrales de confianza configurables (Fase 2 — D1).

    Reemplaza el `0.8` hardcodeado del motor de anomalías. La fila con
    `sede_id IS NULL` es la config global; `sede_id` (nullable, sin FK todavía)
    queda para el scope por sede que introduce E1/D3."""

    __tablename__ = "umbrales_confianza"
    __table_args__ = (
        CheckConstraint(
            "aclaracion >= 0 AND aclaracion <= rapida AND rapida <= auto AND auto <= 1",
            name="ck_umbrales_orden",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sede_id: Mapped[int | None] = mapped_column(BigInteger)
    auto: Mapped[Decimal] = mapped_column(Numeric)
    rapida: Mapped[Decimal] = mapped_column(Numeric)
    aclaracion: Mapped[Decimal] = mapped_column(Numeric)
    actualizado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class EstadisticaOperario(Base):
    """Estadísticas agregadas por operario (Fase 2 — D5). La precisión histórica
    (`correctas/totales`) ajusta la sensibilidad de confirmación: un operario muy
    acertado recibe menos confirmaciones. Se actualiza por job/evento (capa E)."""

    __tablename__ = "estadisticas_operario"

    operario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("operarios.id"), primary_key=True
    )
    capturas_totales: Mapped[int] = mapped_column(server_default=text("0"))
    capturas_correctas: Mapped[int] = mapped_column(server_default=text("0"))
    actualizado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class RiesgoArticulo(Base):
    """Nivel de riesgo histórico por artículo (Fase 2 — E5), recalculado por un
    job a partir de D6 (frecuencia de inconsistencia en los últimos N ciclos).
    Se expone en el payload del catálogo; NO usa ni revela el SD del ciclo
    actual. `sede_id` NULL = global; queda espacio para riesgo por sede."""

    __tablename__ = "riesgo_articulo"
    __table_args__ = (
        CheckConstraint("nivel IN ('alto','medio','bajo')", name="ck_riesgo_nivel"),
        Index("ux_riesgo_articulo_sede", "articulo_id", "sede_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    articulo_id: Mapped[int] = mapped_column(ForeignKey("articulos.id"))
    sede_id: Mapped[int | None] = mapped_column(ForeignKey("sedes.id"))
    nivel: Mapped[str] = mapped_column(Text)
    actualizado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class SinonimoArticulo(Base):
    """Sinónimo aprendido/manual de un artículo, por sede (Fase 2 — D3).

    NUNCA modifica `articulos` (catálogo oficial): es una capa aparte que el
    matching consulta ANTES de la cascada. `sede_id` NULL = sinónimo global.
    Registrar 'garrafa'→X en la sede A no afecta a la sede B."""

    __tablename__ = "sinonimos_articulo"
    __table_args__ = (
        CheckConstraint("origen IN ('aprendido','manual')", name="ck_sinonimos_origen"),
        # Un sinónimo por (sede, texto). nulls_not_distinct: sin esto Postgres
        # trata cada NULL como distinto y los sinónimos GLOBALES (sede_id NULL,
        # el caso por defecto del endpoint) se duplicarían sin dar 409.
        Index(
            "ux_sinonimos_sede_texto", "sede_id", "texto_normalizado",
            unique=True, postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sede_id: Mapped[int | None] = mapped_column(ForeignKey("sedes.id"))
    articulo_id: Mapped[int] = mapped_column(ForeignKey("articulos.id"))
    texto_sinonimo: Mapped[str] = mapped_column(Text)
    texto_normalizado: Mapped[str] = mapped_column(Text)
    origen: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
