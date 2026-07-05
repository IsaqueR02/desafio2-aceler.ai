"""Etapa 2 — TRATAMENTO DE VALORES AUSENTES.

Recebe o dataset long (saída da etapa 1) e resolve as lacunas na coluna `valor`.

Estratégias (3º argumento, opcional):
    descartar  (padrão) -> remove linhas sem valor. É o correto para este
                           painel: só ~21% das células têm dado; imputar o
                           resto fabricaria informação.
    mediana             -> preenche pela mediana de cada país/indicador
                           (fallback: mediana global).
    media               -> idem, pela média.
    zero                -> preenche com 0 (use só se ausência == "sem registro").

Uso:
    python 02_ausentes.py <entrada.csv> <saida.csv> [descartar|mediana|media|zero]
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

CHAVES = ["pais_codigo", "indicador_codigo"]


def tratar_ausentes(entrada: str, saida: str, estrategia: str = "descartar") -> pd.DataFrame:
    """Aplica a estratégia de tratamento de ausentes e grava em `saida`."""
    df = pd.read_csv(entrada, low_memory=False)
    faltantes = int(df["valor"].isna().sum())

    if estrategia == "descartar":
        df = df.dropna(subset=["valor"])
    elif estrategia == "zero":
        df["valor"] = df["valor"].fillna(0)
    elif estrategia in ("media", "mediana"):
        func = "mean" if estrategia == "media" else "median"
        # Imputa pela estatística do grupo (país+indicador)...
        df["valor"] = df["valor"].fillna(
            df.groupby(CHAVES)["valor"].transform(func)
        )
        # ...e o que sobrar (grupo inteiro vazio) pela estatística global.
        global_stat = getattr(df["valor"], func)()
        df["valor"] = df["valor"].fillna(global_stat)
    else:
        sys.exit(f"[02] estratégia inválida: {estrategia!r}")

    # Descarta valores impossíveis para indicadores (negativos).
    df = df[df["valor"] >= 0].reset_index(drop=True)

    df.to_csv(saida, index=False, encoding="utf-8")
    print(f"[02] ausentes ({estrategia}): {faltantes:,} tratados -> {len(df):,} linhas -> {saida}")
    return df


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Uso: python 02_ausentes.py <entrada.csv> <saida.csv> [estrategia]")
    estrategia = sys.argv[3] if len(sys.argv) > 3 else "descartar"
    tratar_ausentes(sys.argv[1], sys.argv[2], estrategia)
