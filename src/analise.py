"""Etapa 3 — ANÁLISE.

Transforma o dataset tratado em um "dossiê" de inteligência: líderes de
crescimento, países estagnados, ranking de investimento, comparação e alertas
de limites. Esse dossiê é a entrada da análise executiva por IA (src/ia.py).
"""
from __future__ import annotations

import pandas as pd

import config
from src import tratamento


def detectar_alertas(df_long: pd.DataFrame) -> list[dict]:
    """Sinaliza países cujo indicador (valor mais recente) cruza o limite (bônus)."""
    alertas: list[dict] = []
    ultimos = tratamento.ultimo_valor(df_long)
    for _, linha in ultimos.iterrows():
        regra = config.ALERTAS.get(linha["Indicator Code"])
        if not regra:
            continue
        disparou = (
            (regra["operador"] == "<" and linha["valor"] < regra["limite"])
            or (regra["operador"] == ">" and linha["valor"] > regra["limite"])
        )
        if disparou:
            alertas.append({
                "Country Name": linha["Country Name"],
                "Country Code": linha["Country Code"],
                "Indicator Code": linha["Indicator Code"],
                "valor": round(float(linha["valor"]), 2),
                "ano": int(linha["ano"]),
                "mensagem": regra["mensagem"],
            })
    return alertas


def montar_dossie(
    df_long: pd.DataFrame,
    indicador_foco: str,
    ano_inicio: int,
    ano_fim: int,
    indicador_investimento: str = "SE.XPD.TOTL.GD.ZS",
) -> dict:
    """Consolida as métricas quantitativas que a IA vai interpretar."""
    print("[3/4] Análise e montagem do dossiê...")

    crescimento = tratamento.calcular_crescimento(df_long, ano_inicio, ano_fim)
    cres_foco = (
        crescimento[crescimento["Indicator Code"] == indicador_foco]
        if not crescimento.empty else crescimento
    )
    colunas_cres = ["Country Name", "Country Code", "cagr_pct", "var_percentual"]

    lideres = cres_foco.head(5)[colunas_cres].to_dict(orient="records") if not cres_foco.empty else []
    estagnados = (
        cres_foco.tail(5).sort_values("cagr_pct")[colunas_cres].to_dict(orient="records")
        if not cres_foco.empty else []
    )

    ranking_foco = tratamento.ranking(df_long, indicador_foco).head(10).to_dict(orient="records")
    ranking_invest = tratamento.ranking(df_long, indicador_investimento).head(10).to_dict(orient="records")
    alertas = detectar_alertas(df_long)

    dossie = {
        "indicador_foco": {
            "codigo": indicador_foco,
            "nome": config.INDICADORES_CHAVE.get(indicador_foco, indicador_foco),
        },
        "janela": {"inicio": ano_inicio, "fim": ano_fim},
        "lideres_crescimento": lideres,
        "estagnados": estagnados,
        "ranking_indicador_foco": ranking_foco,
        "ranking_investimento": ranking_invest,
        "alertas": alertas,
        "total_paises": int(df_long["Country Code"].nunique()),
        "total_indicadores": int(df_long["Indicator Code"].nunique()),
    }
    print(
        f"  [análise] {dossie['total_paises']} países | "
        f"{len(lideres)} líderes | {len(alertas)} alertas"
    )
    return dossie
