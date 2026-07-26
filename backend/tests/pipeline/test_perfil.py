"""Perfil de confianza por operario (Fase 2 — D5).

Verifica el ajuste puro, el scope del repo por operario, y —el DoD— que dos
operarios con distinto historial reciben distinta cantidad de confirmaciones
para la misma captura, por el camino real del pipeline.
"""

from app.pipeline.confianza import clasificar
from app.pipeline.datos.repos import RepoPerfilMem, RepoPerfilVacio
from app.pipeline.matching.embeddings import EmbedderLexico
from app.pipeline.perfil import AjusteConfianza, PerfilOperario, ajustar_confianza
from app.pipeline.servicios import Pipeline

OP_BUENO = "11111111-1111-1111-1111-111111111111"
OP_FLOJO = "22222222-2222-2222-2222-222222222222"


# --- ajuste puro --------------------------------------------------------------

def test_operario_acertado_sube_la_confianza():
    perfil = PerfilOperario(OP_BUENO, precision=0.98, total_capturas=100)
    assert ajustar_confianza(0.86, perfil) > 0.86


def test_operario_impreciso_baja_la_confianza():
    perfil = PerfilOperario(OP_FLOJO, precision=0.70, total_capturas=100)
    assert ajustar_confianza(0.86, perfil) < 0.86


def test_muestra_insuficiente_no_ajusta():
    perfil = PerfilOperario(OP_BUENO, precision=0.99, total_capturas=3)  # < minimo_muestras
    assert ajustar_confianza(0.86, perfil) == 0.86


def test_sin_perfil_no_ajusta():
    assert ajustar_confianza(0.86, None) == 0.86


def test_ajuste_tiene_tope():
    # Precisión perfecta no puede empujar más allá del tope (maximo=0.08).
    perfil = PerfilOperario(OP_BUENO, precision=1.0, total_capturas=1000)
    assert ajustar_confianza(0.86, perfil) <= 0.86 + AjusteConfianza().maximo + 1e-9


def test_parametros_configurables_por_entorno(monkeypatch):
    monkeypatch.setenv("AJUSTE_CONF_MIN_MUESTRAS", "1000")
    cfg = AjusteConfianza.desde_entorno()
    perfil = PerfilOperario(OP_BUENO, precision=0.99, total_capturas=100)  # < 1000
    assert ajustar_confianza(0.86, perfil, cfg) == 0.86  # ya no ajusta


# --- repo por operario --------------------------------------------------------

def test_repo_mem_scopea_por_operario():
    repo = RepoPerfilMem({OP_BUENO: PerfilOperario(OP_BUENO, 0.98, 100)})
    assert repo.para_operario(OP_BUENO).precision == 0.98
    assert repo.para_operario(OP_FLOJO) is None


# --- DoD: dos operarios, misma captura, distinto nº de confirmaciones ---------

def _pipeline(repo_perfil) -> Pipeline:
    return Pipeline(
        nlu=None, embedder=EmbedderLexico(), repo=None, repo_perfil=repo_perfil
    )


def test_dod_dos_operarios_distinta_cantidad_de_confirmaciones():
    repo = RepoPerfilMem({
        OP_BUENO: PerfilOperario(OP_BUENO, precision=0.98, total_capturas=100),
        OP_FLOJO: PerfilOperario(OP_FLOJO, precision=0.70, total_capturas=100),
    })
    pipe = _pipeline(repo)

    # Misma captura base: confianza 0.88 (zona de "aclaración" con umbrales default).
    conf_bueno = pipe._confianza_operario(0.88, OP_BUENO)
    conf_flojo = pipe._confianza_operario(0.88, OP_FLOJO)

    # El operario acertado sube a >=0.90 → 'rapida' (no se pregunta); el flojo
    # baja y sigue en 'aclaracion' (se pregunta). Distinto nº de confirmaciones.
    assert clasificar(conf_bueno) in ("auto", "rapida")
    assert clasificar(conf_flojo) == "aclaracion"
    assert conf_bueno > conf_flojo


def test_sin_perfil_pipeline_no_cambia_la_confianza():
    pipe = _pipeline(RepoPerfilVacio())
    assert pipe._confianza_operario(0.86, OP_BUENO) == 0.86
