"""Sinónimos por sede (Fase 2 — D3).

Verifica la resolución pura, el scope por sede del repo, y —el DoD— que un
sinónimo registrado en la sede A no afecta el matching de la sede B, por el
mismo camino que usa el pipeline (`Pipeline._resolver`).
"""

from app.pipeline.datos.repos import RepoSinonimosMem, RepoSinonimosVacio
from app.pipeline.matching.embeddings import EmbedderLexico
from app.pipeline.matching.sinonimos import resolver_sinonimo
from app.pipeline.normalizacion import normalizar
from app.pipeline.servicios import Pipeline
from app.pipeline.tipos import ArticuloCtx


def _art(nombre, articulo_id) -> ArticuloCtx:
    return ArticuloCtx(
        articulo_id=articulo_id, nombre=nombre,
        nombre_normalizado=normalizar(nombre), unidad_base="Unidad", sd=10.0,
    )


# Artículo X (el "mismo artículo" en ambas sedes) + ruido que no matchea 'garrafa'.
X = _art("BIDON PLASTICO 20 L", articulo_id=500)
CATALOGO = [X, _art("CAZUELA 16 ONZ", articulo_id=1)]


def test_resolver_sinonimo_normaliza_y_falla_limpio():
    mapa = {"garrafa": 500}
    assert resolver_sinonimo("GARRAFA", mapa) == 500       # normaliza mayúsculas
    assert resolver_sinonimo("  garrafa ", mapa) == 500     # y espacios
    assert resolver_sinonimo("botellon", mapa) is None      # no registrado
    assert resolver_sinonimo("garrafa", {}) is None         # mapa vacío
    assert resolver_sinonimo(None, mapa) is None


def test_repo_mem_scopea_por_sede():
    repo = RepoSinonimosMem(
        sede_de_bodega={1: 10, 2: 20},
        sinonimos_por_sede={10: {"garrafa": 500}},
    )
    assert repo.para_bodega(1) == {"garrafa": 500}  # bodega de la sede 10
    assert repo.para_bodega(2) == {}                # sede 20 no tiene
    assert repo.para_bodega(99) == {}               # bodega sin sede


def _pipeline(repo_sinonimos) -> Pipeline:
    # _resolver solo usa embedder + repo_sinonimos; nlu/repo no intervienen aquí.
    return Pipeline(nlu=None, embedder=EmbedderLexico(), repo=None, repo_sinonimos=repo_sinonimos)


def test_dod_sinonimo_de_sede_A_no_afecta_sede_B():
    # Bodega 1 -> sede A (tiene 'garrafa'->X); bodega 2 -> sede B (no tiene).
    repo = RepoSinonimosMem(
        sede_de_bodega={1: 10, 2: 20},
        sinonimos_por_sede={10: {"garrafa": 500}},
    )
    pipe = _pipeline(repo)

    # Sede A: 'garrafa' resuelve al artículo X por sinónimo.
    r_a = pipe._resolver(1, "garrafa", CATALOGO)
    assert r_a.tipo == "match" and r_a.metodo == "sinonimo"
    assert r_a.articulo.articulo_id == 500

    # Sede B: el MISMO 'garrafa' no tiene sinónimo → cae a la cascada → no_catalogado.
    r_b = pipe._resolver(2, "garrafa", CATALOGO)
    assert r_b.tipo == "no_catalogado"


def test_sinonimo_a_articulo_ausente_cae_a_cascada():
    # El sinónimo apunta a un id que no está en el catálogo de esta bodega.
    repo = RepoSinonimosMem(
        sede_de_bodega={1: 10},
        sinonimos_por_sede={10: {"garrafa": 999}},  # 999 no está en CATALOGO
    )
    r = _pipeline(repo)._resolver(1, "garrafa", CATALOGO)
    assert r.tipo == "no_catalogado"  # no inventa el match


def test_default_sin_sinonimos_es_transparente():
    # Sin repo de sinónimos, todo cae a la cascada (comportamiento previo intacto).
    pipe = _pipeline(RepoSinonimosVacio())
    r = pipe._resolver(1, "cazuela 16 onz", CATALOGO)
    assert r.tipo == "match" and r.metodo == "exacto"
