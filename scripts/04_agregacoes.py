"""Etapa 4 — AGREGAÇÕES.

Agrupa a série tratada (saída da etapa 3) por indicador e ano, calculando
métricas estatísticas entre os países: contagem, soma, média e mediana.

É a visão "panorâmica" — como cada indicador se comporta globalmente ao longo
do tempo, independentemente de país.

Uso:
    python 04_agregacoes.py <entrada.csv> <saida.csv>
"""
from __future__ import annotations

import sys

import pandas as pd


def agregar(entrada: str, saida: str) -> pd.DataFrame:
    """Agrega por (indicador, ano) e grava as estatísticas em `saida`."""
    df = pd.read_csv(entrada, low_memory=False)

    agregado = (
        df.groupby(["indicador_codigo", "indicador_nome", "ano"])["valor"]
        .agg(n_paises="count", soma="sum", media="mean", mediana="median")
        .reset_index()
    )
    for col in ("soma", "media", "mediana"):
        agregado[col] = agregado[col].round(2)

    agregado.to_csv(saida, index=False, encoding="utf-8")
    print(f"[04] agregações: {len(agregado):,} linhas (indicador x ano) -> {saida}")
    return agregado


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Uso: python 04_agregacoes.py <entrada.csv> <saida.csv>")
    agregar(sys.argv[1], sys.argv[2])
