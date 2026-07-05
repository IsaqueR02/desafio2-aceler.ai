"""Etapa 8 — GERAÇÃO DO CSV FINAL.

Recebe qualquer DataFrame tratado das etapas anteriores e exporta um CSV final
"otimizado":

  - arredonda floats (reduz ruído/decimais infinitos);
  - faz downcast dos numéricos (int64->int32/valor menor) para arquivo mais leve;
  - remove colunas totalmente vazias;
  - ordena de forma estável;
  - grava SEM o índice do pandas (index=False).

Uso:
    python 08_export.py <entrada.csv> <saida.csv>
"""
from __future__ import annotations

import sys

import pandas as pd


def exportar_csv_final(entrada: str, saida: str) -> pd.DataFrame:
    """Otimiza os tipos/colunas e grava o CSV final sem índice."""
    df = pd.read_csv(entrada, low_memory=False)

    # Remove colunas 100% vazias.
    df = df.dropna(axis=1, how="all")

    # Arredonda floats e faz downcast dos numéricos para aliviar o arquivo.
    for col in df.select_dtypes(include="float").columns:
        df[col] = pd.to_numeric(df[col].round(4), downcast="float")
    for col in df.select_dtypes(include="integer").columns:
        df[col] = pd.to_numeric(df[col], downcast="integer")

    # Ordenação estável pelas colunas de identificação, quando existirem.
    chaves = [c for c in ("indicador_codigo", "pais_codigo", "ano") if c in df.columns]
    if chaves:
        df = df.sort_values(chaves).reset_index(drop=True)

    df.to_csv(saida, index=False, encoding="utf-8")
    print(f"[08] CSV final: {len(df):,} linhas x {df.shape[1]} colunas -> {saida}")
    return df


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Uso: python 08_export.py <entrada.csv> <saida.csv>")
    exportar_csv_final(sys.argv[1], sys.argv[2])
