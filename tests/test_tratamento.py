"""Testes unitários do núcleo de processamento (src/tratamento.py).

Exercitam as funções que tratam o arquivo EdStats: limpeza/melt, tratamento
de ausentes, seleção, agregação, ranking, crescimento (CAGR) e comparação.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src import tratamento as t


def test_limpar_e_derreter_formato_e_ausentes(edstats_wide):
    limpo = edstats_wide.loc[:, ~edstats_wide.columns.str.startswith("Unnamed")]
    longo = t.limpar_e_derreter(limpo)

    # Vira long com as colunas esperadas.
    assert {"ano", "valor"}.issubset(longo.columns)
    assert longo["ano"].dtype.kind in "iu"  # inteiro
    # 3 países x 3 anos = 9 células, menos 2 ausentes (2005 de BRA e IND) = 7.
    assert len(longo) == 7
    assert longo["valor"].notna().all()


def test_limpar_sem_coluna_ano_levanta_erro():
    df = pd.DataFrame({"Country Name": ["X"], "Country Code": ["X"],
                       "Indicator Name": ["i"], "Indicator Code": ["I"]})
    try:
        t.limpar_e_derreter(df)
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass


def test_tratar_ausentes_interpola(edstats_long):
    # A série é reindexada para o intervalo anual contínuo [2000..2010]:
    # 11 anos x 3 países = 33 linhas, todas com valor preenchido.
    tratado = t.tratar_ausentes(edstats_long, metodo="interpolar")
    assert len(tratado) == 33
    assert tratado["valor"].notna().all()
    # Cada país passa a ter a série anual completa.
    for pais in ("BRA", "FIN", "IND"):
        anos = sorted(tratado[tratado["Country Code"] == pais]["ano"])
        assert anos == list(range(2000, 2011))
    # Interpolação linear entre 4.0 (2000) e 5.5 (2010) -> 4.75 em 2005.
    bra_2005 = tratado[(tratado["Country Code"] == "BRA") & (tratado["ano"] == 2005)]
    assert np.isclose(bra_2005["valor"].iloc[0], 4.75)


def test_tratar_ausentes_descartar_nao_imputa(edstats_long):
    igual = t.tratar_ausentes(edstats_long, metodo="descartar")
    assert len(igual) == len(edstats_long)


def test_selecionar_filtra_pais_e_ano(edstats_long):
    sel = t.selecionar(edstats_long, paises=["BRA"], ano_inicio=2000, ano_fim=2000)
    assert set(sel["Country Code"]) == {"BRA"}
    assert set(sel["ano"]) == {2000}


def test_ultimo_valor_pega_ano_mais_recente(edstats_long):
    ult = t.ultimo_valor(edstats_long)
    bra = ult[ult["Country Code"] == "BRA"].iloc[0]
    assert bra["ano"] == 2010
    assert bra["valor"] == 5.5


def test_ranking_ordena_desc(edstats_long):
    rk = t.ranking(edstats_long, "SE.XPD.TOTL.GD.ZS", ano=2010)
    # Finlândia (7.0) > Brasil (5.5) > Índia (3.8)
    assert list(rk["Country Code"]) == ["FIN", "BRA", "IND"]
    assert list(rk["posicao"]) == [1, 2, 3]


def test_ranking_indicador_inexistente_retorna_vazio(edstats_long):
    rk = t.ranking(edstats_long, "NAO.EXISTE")
    assert rk.empty


def test_calcular_crescimento_cagr(edstats_long):
    # Usa dados tratados p/ garantir os dois anos-âncora.
    tratado = t.tratar_ausentes(edstats_long)
    cres = t.calcular_crescimento(tratado, ano_inicio=2000, ano_fim=2010)
    bra = cres[cres["Country Code"] == "BRA"].iloc[0]
    # 4.0 -> 5.5 em 10 anos: var% = 37.5; CAGR = (5.5/4)^(1/10)-1 ≈ 3.24%
    assert np.isclose(bra["var_percentual"], 37.5)
    assert np.isclose(bra["cagr_pct"], 3.24, atol=0.05)


def test_comparar_paises_pivota(edstats_long):
    comp = t.comparar_paises(
        edstats_long, paises=["BRA", "FIN"], indicadores=["SE.XPD.TOTL.GD.ZS"]
    )
    assert set(comp["Country Code"]) == {"BRA", "FIN"}
    # Uma coluna por indicador (nome amigável).
    assert "Gasto público em educação (% do PIB)" in comp.columns


def test_salvar_csv_final(edstats_long, tmp_path, monkeypatch):
    monkeypatch.setattr(t, "PROCESSED_DIR", tmp_path)
    caminho = t.salvar_csv_final(edstats_long, nome="teste")
    assert caminho.endswith("teste.csv")
    recarregado = pd.read_csv(caminho)
    assert len(recarregado) == len(edstats_long)
