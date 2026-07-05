"""Etapa 1 — LIMPEZA DE DADOS.

Lê o EdStats bruto no formato *wide* (anos em colunas) do World Bank e entrega
um dataset *long* (uma linha por país/indicador/ano) já limpo:

  - remove colunas técnicas irrelevantes para a análise (FREQ, DATABASE_ID, ...);
  - padroniza strings (remove espaços, normaliza caixa dos códigos);
  - remove linhas duplicadas;
  - converte tipos (ano -> int, valor -> float).

Uso (n8n / Execute Command):
    python 01_limpeza.py <entrada.csv> <saida.csv>
"""
from __future__ import annotations

import sys

import pandas as pd

# Colunas do arquivo wide que interessam à análise -> nome amigável em pt.
COLUNAS_ESSENCIAIS = {
    "REF_AREA": "pais_codigo",
    "REF_AREA_LABEL": "pais_nome",
    "INDICATOR": "indicador_codigo",
    "INDICATOR_LABEL": "indicador_nome",
    "SEX": "sexo",
    "AGE": "idade",
    "UNIT_MEASURE_LABEL": "unidade",
}


def limpar_dados(entrada: str, saida: str) -> pd.DataFrame:
    """Limpa o wide do EdStats e derrete para long, gravando em `saida`."""
    df = pd.read_csv(entrada, low_memory=False)

    # Remove a coluna final vazia que o EdStats costuma trazer ("Unnamed: NN").
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]

    # Padroniza strings: tira espaços das bordas em todas as colunas de texto.
    colunas_texto = [c for c in df.columns if pd.api.types.is_string_dtype(df[c])]
    for col in colunas_texto:
        df[col] = df[col].str.strip()

    # Normaliza a caixa dos códigos (país/indicador em MAIÚSCULAS).
    for col in ("REF_AREA", "INDICATOR", "SEX", "AGE"):
        if col in df.columns:
            df[col] = df[col].str.upper()

    # Remove linhas totalmente duplicadas.
    df = df.drop_duplicates()

    # Seleciona só as colunas essenciais que existem no arquivo.
    presentes = {k: v for k, v in COLUNAS_ESSENCIAIS.items() if k in df.columns}
    colunas_ano = [c for c in df.columns if str(c).isdigit()]
    if not colunas_ano:
        sys.exit("[01] Nenhuma coluna de ano encontrada — schema inesperado.")

    df = df[list(presentes) + colunas_ano].rename(columns=presentes)

    # wide -> long: cada ano/valor vira uma linha.
    longo = df.melt(
        id_vars=list(presentes.values()),
        value_vars=colunas_ano,
        var_name="ano",
        value_name="valor",
    )

    # Conversão de tipos.
    longo["ano"] = longo["ano"].astype(int)
    longo["valor"] = pd.to_numeric(longo["valor"], errors="coerce")

    longo.to_csv(saida, index=False, encoding="utf-8")
    print(f"[01] limpeza OK: {len(longo):,} linhas -> {saida}")
    return longo


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Uso: python 01_limpeza.py <entrada.csv> <saida.csv>")
    limpar_dados(sys.argv[1], sys.argv[2])
