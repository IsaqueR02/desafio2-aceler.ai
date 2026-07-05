"""Etapa 3 — SELEÇÃO DE INDICADORES / COLUNAS ESSENCIAIS.

Reduz o dataset ao mínimo necessário para a análise macro/social:

  - mantém apenas os TOTAIS (sexo `_T` e idade `_T`), descartando recortes
    demográficos que duplicariam a série do país/indicador;
  - guarda só as colunas essenciais: país, indicador, ano, valor;
  - garante UNICIDADE por (país, indicador, ano) agregando por média
    (ainda restam breakdowns como urbanização/método de agregação);
  - opcionalmente filtra uma lista de indicadores (3º argumento, separado por
    vírgula) — sem lista, mantém todos.

Uso:
    python 03_selecao.py <entrada.csv> <saida.csv> [COD1,COD2,...]
"""
from __future__ import annotations

import sys

import pandas as pd

COLUNAS_FINAIS = ["pais_codigo", "pais_nome", "indicador_codigo", "indicador_nome", "ano", "valor"]


def selecionar_indicadores(entrada: str, saida: str, indicadores: list[str] | None = None) -> pd.DataFrame:
    """Filtra totais + colunas essenciais e devolve série única por país/indicador/ano."""
    df = pd.read_csv(entrada, low_memory=False)

    # Mantém só os agregados totais, quando as colunas de recorte existirem.
    if "sexo" in df.columns:
        df = df[df["sexo"] == "_T"]
    if "idade" in df.columns:
        df = df[df["idade"] == "_T"]

    df = df[[c for c in COLUNAS_FINAIS if c in df.columns]]

    if indicadores:
        df = df[df["indicador_codigo"].isin(indicadores)]

    # Garante 1 valor por país/indicador/ano (média dos breakdowns remanescentes).
    df = (
        df.groupby(["pais_codigo", "pais_nome", "indicador_codigo", "indicador_nome", "ano"],
                   as_index=False)["valor"]
        .mean()
    )

    df.to_csv(saida, index=False, encoding="utf-8")
    n_ind = df["indicador_codigo"].nunique()
    print(f"[03] seleção: {len(df):,} linhas | {n_ind} indicadores -> {saida}")
    return df


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Uso: python 03_selecao.py <entrada.csv> <saida.csv> [COD1,COD2,...]")
    lista = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    selecionar_indicadores(sys.argv[1], sys.argv[2], lista)
