"""Etapa 7 — COMPARAÇÃO ENTRE PAÍSES.

Pivota a série de UM indicador para expor os países lado a lado ao longo dos
anos: linhas = países, colunas = anos, células = valor. Formato ideal para
comparar trajetórias nacionais e alimentar tabelas/heatmaps.

O indicador é escolhido pelo 3º argumento; sem ele, usa o indicador com mais
observações (o de melhor cobertura).

Uso:
    python 07_comparacao.py <entrada.csv> <saida.csv> [INDICADOR_CODIGO]
"""
from __future__ import annotations

import sys

import pandas as pd


def comparar_paises(entrada: str, saida: str, indicador: str | None = None) -> pd.DataFrame:
    """Pivota países x anos para um indicador e grava a matriz em `saida`."""
    df = pd.read_csv(entrada, low_memory=False)

    # Guarda-chuva: se a entrada não trouxer NENHUM indicador válido (ex.: a etapa
    # 03 filtrou por um código inexistente e devolveu um CSV vazio), falha com uma
    # mensagem clara. Sem isto, value_counts().idxmax() abaixo estoura um
    # "ValueError: attempt to get argmax of an empty sequence" (Traceback feio =>
    # 500 no main.py), escondendo a verdadeira causa: o filtro da etapa 03.
    serie = df["indicador_codigo"].dropna() if "indicador_codigo" in df.columns else pd.Series(dtype="object")
    if serie.empty:
        sys.exit(
            "[07] entrada sem indicadores válidos — nada a comparar. "
            "Provavelmente o filtro de indicadores da etapa 03 não casou com "
            "nenhum código (confira se está usando um 'indicador_codigo' real)."
        )

    if indicador is None:
        # Indicador com maior cobertura (mais linhas) = comparação mais rica.
        indicador = serie.value_counts().idxmax()

    dados = df[df["indicador_codigo"] == indicador]
    if dados.empty:
        sys.exit(f"[07] indicador não encontrado: {indicador!r}")

    matriz = dados.pivot_table(
        index=["pais_codigo", "pais_nome"],
        columns="ano",
        values="valor",
        aggfunc="mean",
    ).reset_index()
    matriz.columns.name = None  # remove o rótulo "ano" do eixo de colunas

    matriz.to_csv(saida, index=False, encoding="utf-8")
    print(f"[07] comparação [{indicador}]: {len(matriz):,} países x anos -> {saida}")
    return matriz


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Uso: python 07_comparacao.py <entrada.csv> <saida.csv> [INDICADOR]")
    ind = sys.argv[3] if len(sys.argv) > 3 else None
    comparar_paises(sys.argv[1], sys.argv[2], ind)
