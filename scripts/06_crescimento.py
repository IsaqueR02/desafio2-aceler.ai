"""Etapa 6 — CÁLCULO DE CRESCIMENTO.

Calcula a variação percentual ano a ano de cada série país/indicador
(`crescimento_pct`) e a variação absoluta (`variacao_abs`). Revela quem está
evoluindo e quem está estagnando/regredindo.

Uso:
    python 06_crescimento.py <entrada.csv> <saida.csv>
"""
from __future__ import annotations

import sys

import pandas as pd

CHAVES = ["pais_codigo", "indicador_codigo"]


def calcular_crescimento(entrada: str, saida: str) -> pd.DataFrame:
    """Calcula variação anual (%) e absoluta por série e grava em `saida`."""
    df = pd.read_csv(entrada, low_memory=False)

    # Ordena por série e por ano para o pct_change refletir a linha do tempo.
    df = df.sort_values([*CHAVES, "ano"]).reset_index(drop=True)

    grupo = df.groupby(CHAVES)["valor"]
    df["variacao_abs"] = grupo.diff().round(2)
    df["crescimento_pct"] = (grupo.pct_change() * 100).round(2)

    df.to_csv(saida, index=False, encoding="utf-8")
    print(f"[06] crescimento: {len(df):,} linhas com variação anual -> {saida}")
    return df


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Uso: python 06_crescimento.py <entrada.csv> <saida.csv>")
    calcular_crescimento(sys.argv[1], sys.argv[2])
