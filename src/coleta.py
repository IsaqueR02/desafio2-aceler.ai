"""Etapa 1 — COLETA.

Lê o dataset World Bank EdStats (formato wide) da pasta data/raw e,
opcionalmente, enriquece com a API pública do World Bank (outra fonte).

Arquivo principal esperado (Kaggle):
    EdStatsData.csv
    colunas: Country Name | Country Code | Indicator Name | Indicator Code | 1970 | ... | 2017
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import RAW_DIR

ARQUIVO_PRINCIPAL = "EdStatsData"


def _achar_arquivo(nome_base: str) -> Path | None:
    """Retorna o caminho do arquivo aceitando .csv/.xlsx/.xls, ou None."""
    for ext in (".csv", ".xlsx", ".xls"):
        caminho = RAW_DIR / f"{nome_base}{ext}"
        if caminho.exists():
            return caminho
    return None


def carregar_edstats() -> pd.DataFrame:
    """Carrega o EdStatsData bruto (wide). Levanta erro claro se ausente."""
    print("[1/4] Coleta de dados...")
    caminho = _achar_arquivo(ARQUIVO_PRINCIPAL)
    if caminho is None:
        raise FileNotFoundError(
            f"Não encontrei '{ARQUIVO_PRINCIPAL}.csv' em {RAW_DIR}.\n"
            "Baixe o dataset World Bank EdStats do Kaggle e coloque o arquivo lá:\n"
            "  https://www.kaggle.com/code/paultimothymooney/how-to-query-the-world-bank-education-data"
        )

    print(f"  [coleta] lendo {caminho.name}")
    if caminho.suffix == ".csv":
        df = pd.read_csv(caminho, low_memory=False)
    else:
        df = pd.read_excel(caminho)

    # O EdStats costuma trazer uma coluna final vazia ("Unnamed: NN") — remove.
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    print(f"  [coleta] {len(df):,} linhas x {df.shape[1]} colunas".replace(",", "."))
    return df


def carregar_metadados_series() -> pd.DataFrame | None:
    """Metadados dos indicadores (EdStatsSeries.csv), se disponível."""
    caminho = _achar_arquivo("EdStatsSeries")
    if caminho is None:
        return None
    return pd.read_csv(caminho, low_memory=False)


def enriquecer_worldbank_api(
    codigo_pais: str, codigo_indicador: str, timeout: int = 20
) -> pd.DataFrame:
    """Busca a série de um indicador via API pública do World Bank (sem chave).

    Retorna DataFrame com colunas [ano, valor]. Fonte complementar ao Kaggle,
    útil para preencher anos mais recentes ausentes no CSV estático.
    """
    import requests

    url = (
        f"https://api.worldbank.org/v2/country/{codigo_pais}"
        f"/indicator/{codigo_indicador}?format=json&per_page=200"
    )
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        return pd.DataFrame(columns=["ano", "valor"])

    registros = [
        {"ano": int(item["date"]), "valor": item["value"]}
        for item in payload[1]
        if item.get("value") is not None
    ]
    return pd.DataFrame(registros).sort_values("ano").reset_index(drop=True)


if __name__ == "__main__":
    carregar_edstats()
