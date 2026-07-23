"""Ingesta contra el mini-Excel de suciedades, sobre una BD de prueba.

El Excel real NO se usa aquí (estas pruebas corren en CI)."""

import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.models import Articulo, Base, Bodega, StockTeorico
from tests.make_mini_excel import crear

sys.path.insert(0, str(Path(__file__).parents[2] / "data"))
import ingest

TEST_DB = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://voceo:voceo@localhost:5433/voceostock_test"
)


@pytest.fixture(scope="session")
def mini_excel(tmp_path_factory):
    return crear()


@pytest.fixture(scope="session")
def engine():
    admin_url = TEST_DB.rsplit("/", 1)[0] + "/voceostock"
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    nombre_db = TEST_DB.rsplit("/", 1)[1]
    with admin.connect() as conn:
        existe = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": nombre_db}
        ).scalar()
        if not existe:
            conn.execute(text(f'CREATE DATABASE "{nombre_db}"'))
    admin.dispose()
    eng = create_engine(TEST_DB)
    with eng.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine


@pytest.fixture()
def resumen(db, mini_excel):
    return ingest.cargar(mini_excel, db)


def test_fusion_bodegas(db, resumen):
    with Session(db) as s:
        bodegas = s.scalars(select(Bodega)).all()
        nombres = sorted(b.nombre for b in bodegas)
    assert nombres == ["bodega central", "kiosco nuevo", "kiosco parqueadero", "movil fonda"]
    assert len(resumen.fusiones) == 3  # espacios, sufijo, typo


def test_hoja_sin_match_crea_bodega_y_reporta(db, resumen):
    assert len(resumen.hojas_sin_match) == 1
    assert "STOCK KIOSCO NUEVO AYB" in resumen.hojas_sin_match[0]


def test_alias_conservan_originales(db, resumen):
    with Session(db) as s:
        fonda = s.scalar(select(Bodega).where(Bodega.nombre == "movil fonda"))
        parqueadero = s.scalar(select(Bodega).where(Bodega.nombre == "kiosco parqueadero"))
    assert "movil fonda suministros" in fonda.alias
    assert "kiosco paqueadero suministros" in parqueadero.alias


def test_mismo_nr_en_dos_hojas_es_un_articulo_dos_stock(db, resumen):
    with Session(db) as s:
        aceites = s.scalars(select(Articulo).where(Articulo.nr_articulo == 100)).all()
        stock = s.scalars(
            select(StockTeorico).where(StockTeorico.articulo_id == aceites[0].id)
        ).all()
    assert len(aceites) == 1
    assert len(stock) == 2


def test_articulo_sin_codigo(db, resumen):
    with Session(db) as s:
        sin_codigo = s.scalars(select(Articulo).where(Articulo.nr_articulo.is_(None))).all()
    assert len(sin_codigo) == 1
    assert sin_codigo[0].nombre == "AGUA MINI"
    assert resumen.articulos_sin_codigo == 1


def test_conflicto_unidad_gana_primera(db, resumen):
    assert len(resumen.conflictos_unidad) == 1
    assert "CAFE" in resumen.conflictos_unidad[0]
    with Session(db) as s:
        cafe = s.scalar(select(Articulo).where(Articulo.nr_articulo == 300))
    assert cafe.unidad_base == "Kilogram"  # la primera aparición gana


def test_encabezado_cantida_tolerado(db, resumen):
    # La hoja con CANTIDA cargó sus 2 filas con orden_original correcto.
    with Session(db) as s:
        fonda = s.scalar(select(Bodega).where(Bodega.nombre == "movil fonda"))
        stock = s.scalars(
            select(StockTeorico).where(StockTeorico.bodega_id == fonda.id)
        ).all()
    assert sorted(st.orden_original for st in stock) == [1, 2]


def test_sd_decimal_preservado(db, resumen):
    with Session(db) as s:
        aceite = s.scalar(select(Articulo).where(Articulo.nr_articulo == 100))
        central = s.scalar(select(Bodega).where(Bodega.nombre == "bodega central"))
        st = s.scalar(
            select(StockTeorico).where(
                StockTeorico.articulo_id == aceite.id,
                StockTeorico.bodega_id == central.id,
            )
        )
    assert st.sd == Decimal("10.5")


def test_idempotencia(db, mini_excel, resumen):
    segunda = ingest.cargar(mini_excel, db)
    assert segunda.inserciones == 0
    assert segunda.stock_nuevo == 0
    assert segunda.articulos_nuevos == 0
    assert segunda.bodegas_nuevas == 0
