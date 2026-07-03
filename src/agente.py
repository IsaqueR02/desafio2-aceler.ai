"""Agente orquestrador.

Executa o fluxo completo de ponta a ponta:
    coleta -> tratamento -> análise -> relatório
Também persiste a tabela consolidada em data/processed para auditoria.
"""
from __future__ import annotations

import config
from src import analise, coleta, relatorio, tratamento


def executar() -> dict:
    """Roda o pipeline inteiro e retorna um resumo da execução."""
    print("=" * 60)
    print("AGENTE INTELIGENTE DE MONITORAMENTO EDUCACIONAL")
    print("=" * 60)

    # 1. Coleta
    dados = coleta.coletar()

    # 2. Tratamento
    df = tratamento.tratar(dados)
    consolidado = config.PROCESSED_DIR / "consolidado.csv"
    df.to_csv(consolidado, index=False, encoding="utf-8")
    print(f"  [tratamento] consolidado salvo: {consolidado}")

    # 3. Análise
    indicadores = analise.calcular_indicadores(df)
    insights = analise.gerar_insights_ia(indicadores)

    # 4. Relatório
    saidas = relatorio.gerar_relatorios(df, indicadores, insights)

    print("=" * 60)
    print("CONCLUÍDO.")
    print(f"  Markdown: {saidas['markdown']}")
    print(f"  PDF:      {saidas['pdf'] or 'não gerado'}")
    print(f"  E-mail:   {'enviado' if saidas['email_enviado'] else 'não enviado'}")
    print("=" * 60)

    return {"consolidado": consolidado, **saidas}


if __name__ == "__main__":
    executar()
