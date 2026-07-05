"""Etapa 5 — RANKINGS.

Adiciona uma coluna de classificação (`ranking`) que ordena os países dentro de
cada (indicador, ano): posição 1 = maior valor. Útil para responder "quem lidera
cada indicador em cada ano".

Uso:
    python 05_rankings.py <entrada.csv> <saida.csv>
"""
from __future__ import annotations

import sys

import pandas as pd


def rankear(entrada: str, saida: str) -> pd.DataFrame:
    """Cria o ranking por (indicador, ano) e grava em `saida`."""
    df = pd.read_csv(entrada, low_memory=False)

    # method="dense" -> empates recebem a mesma posição, sem pular números.
    df["ranking"] = (
        df.groupby(["indicador_codigo", "ano"])["valor"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )

    df = df.sort_values(["indicador_codigo", "ano", "ranking"]).reset_index(drop=True)

    df.to_csv(saida, index=False, encoding="utf-8")
    print(f"[05] rankings: {len(df):,} linhas classificadas -> {saida}")
    return df


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Uso: python 05_rankings.py <entrada.csv> <saida.csv>")
    rankear(sys.argv[1], sys.argv[2])
