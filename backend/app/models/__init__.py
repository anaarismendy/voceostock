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


class Bodega(Base):
    __tablename__ = "bodegas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(Text)
    nombre_normalizado: Mapped[str] = mapped_column(Text, unique=True)
    alias: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))


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
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    nombre: Mapped[str] = mapped_column(Text)
    pin: Mapped[str] = mapped_column(Text)  # hash, no texto plano
    rol: Mapped[str | None] = mapped_column(Text)
    telefono: Mapped[str | None] = mapped_column(Text)


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
