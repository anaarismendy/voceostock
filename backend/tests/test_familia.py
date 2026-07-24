from scripts.populate_familia import familia_de


def test_familia_primera_palabra_significativa():
    assert familia_de("aceite de oliva") == "ACEITE"
    assert familia_de("tapa cazuela 16 onz") == "TAPA"
    assert familia_de("arroz basmati") == "ARROZ"


def test_familia_ignora_stopwords_y_numeros():
    assert familia_de("de la 16 x cazuela") == "CAZUELA"
    assert familia_de("") == "GENERAL"
