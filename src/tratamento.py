"""Etapa 2 — TRATAMENTO (núcleo de processamento em Python).

Concentra as atividades de dados exigidas pelo desafio:
  1. limpeza de dados          -> `limpar_e_derreter`
  2. tratamento de ausentes    -> `tratar_ausentes`
  3. seleção de indicadores    -> `selecionar`
  4. agregações                -> `ultimo_valor`
  5. rankings                  -> `ranking`
  6. cálculo de crescimento    -> `calcular_crescimento` (CAGR)
  7. comparação entre países   -> `comparar_paises`
  8. geração de CSV final      -> `salvar_csv_final`

Trabalha com o dataset no formato "long" (uma linha por país/indicador/ano),
obtido a partir do formato "wide" do EdStats.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from config import PROCESSED_DIR

COLS_ID = ["Country Name", "Country Code", "Indicator Name", "Indicator Code"]
_RE_ANO = re.compile(r"^\d{4}$")


def limpar_e_derreter(df_wide: pd.DataFrame) -> pd.DataFrame:
    """(1) Limpeza + transforma wide (anos em colunas) em long.

    - Identifica as colunas de ano (ex.: "1970".."2017").
    - Faz o melt para colunas [ano, valor].
    - Converte tipos e descarta valores ausentes/negativos inválidos.
    """
    colunas_ano = [c for c in df_wide.columns if _RE_ANO.match(str(c))]
    if not colunas_ano:
        raise ValueError("Nenhuma coluna de ano encontrada — schema EdStats inesperado.")

    faltando = [c for c in COLS_ID if c not in df_wide.columns]
    if faltando:
        raise ValueError(f"Colunas de identificação ausentes: {faltando}")

    longo = df_wide.melt(
        id_vars=COLS_ID,
        value_vars=colunas_ano,
        var_name="ano",
        value_name="valor",
    )
    longo["ano"] = longo["ano"].astype(int)
    longo["valor"] = pd.to_numeric(longo["valor"], errors="coerce")

    # Remove ausentes reais e valores impossíveis para indicadores educacionais.
    longo = longo.dropna(subset=["valor"])
    longo = longo[longo["valor"] >= 0]
    return longo.reset_index(drop=True)


def tratar_ausentes(df_long: pd.DataFrame, metodo: str = "interpolar") -> pd.DataFrame:
    """(2) Trata lacunas na série temporal de cada país/indicador.

    Como `limpar_e_derreter` remove as linhas sem valor, os anos ausentes
    somem do DataFrame. Aqui, para "interpolar", cada série é reindexada para
    o intervalo contínuo [min(ano)..max(ano)] daquele país/indicador — só então
    a interpolação linear preenche os buracos (e replica as pontas).

    - "interpolar": recria os anos faltantes e imputa por interpolação linear.
    - "descartar": mantém apenas os valores originais (nenhuma imputação).
    """
    if metodo == "descartar":
        return df_long.copy()

    def _preencher(grupo: pd.DataFrame) -> pd.DataFrame:
        grupo = grupo.sort_values("ano").set_index("ano")
        anos_completos = range(int(grupo.index.min()), int(grupo.index.max()) + 1)
        grupo = grupo.reindex(anos_completos)
        # Reconstitui os rótulos de identificação nas linhas recriadas.
        for coluna in COLS_ID:
            grupo[coluna] = grupo[coluna].ffill().bfill()
        grupo["valor"] = grupo["valor"].interpolate(method="linear", limit_direction="both")
        return grupo.reset_index().rename(columns={"index": "ano"})

    return (
        df_long.groupby(["Country Code", "Indicator Code"], group_keys=False)
        .apply(_preencher)
        .reset_index(drop=True)
    )


def selecionar(
    df_long: pd.DataFrame,
    paises: list[str] | None = None,
    indicadores: list[str] | None = None,
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> pd.DataFrame:
    """(3) Filtra por países (ISO3), indicadores (código) e janela de anos."""
    df = df_long
    if paises:
        df = df[df["Country Code"].isin(paises)]
    if indicadores:
        df = df[df["Indicator Code"].isin(indicadores)]
    if ano_inicio is not None:
        df = df[df["ano"] >= ano_inicio]
    if ano_fim is not None:
        df = df[df["ano"] <= ano_fim]
    return df.reset_index(drop=True)


def ultimo_valor(df_long: pd.DataFrame) -> pd.DataFrame:
    """(4) Agregação: último valor disponível por país/indicador."""
    idx = df_long.groupby(["Country Code", "Indicator Code"])["ano"].idxmax()
    return (
        df_long.loc[idx, [*COLS_ID, "ano", "valor"]]
        .sort_values(["Indicator Code", "valor"], ascending=[True, False])
        .reset_index(drop=True)
    )


def ranking(df_long: pd.DataFrame, indicador: str, ano: int | None = None) -> pd.DataFrame:
    """(5) Ranking de países para um indicador, no ano dado (ou o mais recente)."""
    dados = df_long[df_long["Indicator Code"] == indicador]
    if dados.empty:
        return pd.DataFrame(columns=["posicao", "Country Name", "Country Code", "ano", "valor"])

    if ano is None:
        dados = ultimo_valor(dados)
    else:
        dados = dados[dados["ano"] == ano]

    dados = dados.sort_values("valor", ascending=False).reset_index(drop=True)
    dados.insert(0, "posicao", dados.index + 1)
    return dados[["posicao", "Country Name", "Country Code", "ano", "valor"]]


def calcular_crescimento(
    df_long: pd.DataFrame, ano_inicio: int, ano_fim: int
) -> pd.DataFrame:
    """(6) Crescimento por país/indicador entre dois anos.

    Calcula variação absoluta, variação percentual e CAGR (taxa de crescimento
    anual composta) — a métrica que revela quem *evoluiu* vs. *estagnou*.
    """
    if ano_fim <= ano_inicio:
        raise ValueError("ano_fim deve ser maior que ano_inicio para calcular crescimento.")

    janela = df_long[df_long["ano"].isin([ano_inicio, ano_fim])]
    pivot = janela.pivot_table(
        index=[*COLS_ID], columns="ano", values="valor", aggfunc="first"
    )
    if ano_inicio not in pivot.columns or ano_fim not in pivot.columns:
        return pd.DataFrame()

    pivot = pivot.dropna(subset=[ano_inicio, ano_fim]).reset_index()
    inicio, fim = pivot[ano_inicio], pivot[ano_fim]
    anos = ano_fim - ano_inicio

    pivot["var_absoluta"] = (fim - inicio).round(2)
    pivot["var_percentual"] = np.where(
        inicio != 0, ((fim - inicio) / inicio * 100).round(2), np.nan
    )
    # CAGR só faz sentido para valores positivos.
    pivot["cagr_pct"] = np.where(
        (inicio > 0) & (fim > 0),
        ((fim / inicio) ** (1 / anos) - 1) * 100,
        np.nan,
    ).round(2)

    return pivot.sort_values("cagr_pct", ascending=False).reset_index(drop=True)


def comparar_paises(
    df_long: pd.DataFrame, paises: list[str], indicadores: list[str], ano: int | None = None
) -> pd.DataFrame:
    """(7) Tabela comparativa países x indicadores (valor mais recente ou do ano)."""
    dados = selecionar(df_long, paises=paises, indicadores=indicadores)
    if ano is not None:
        dados = dados[dados["ano"] == ano]
    else:
        dados = ultimo_valor(dados)

    return dados.pivot_table(
        index=["Country Code", "Country Name"],
        columns="Indicator Name",
        values="valor",
        aggfunc="first",
    ).reset_index()


def salvar_csv_final(df_long: pd.DataFrame, nome: str = "edstats_tratado") -> str:
    """(8) Persiste o dataset tratado (long) em data/processed."""
    caminho = PROCESSED_DIR / f"{nome}.csv"
    df_long.to_csv(caminho, index=False, encoding="utf-8")
    print(f"  [tratamento] CSV final salvo: {caminho}")
    return str(caminho)
