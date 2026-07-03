"""Camada de IA (OpenAI) — produz ANÁLISE EXECUTIVA, não resumo de números.

Recebe um "dossiê" de métricas já calculadas (rankings, crescimento,
comparações, alertas) e pede à OpenAI uma leitura interpretativa: quem evoluiu,
quem estagnou, prováveis explicações e recomendações acionáveis.

O import da lib openai é tardio e há fallback determinístico offline, para o
pipeline nunca quebrar por falta de chave ou de dependência.
"""
from __future__ import annotations

import json

import config

SYSTEM_PROMPT = (
    "Você é um economista-chefe especialista em políticas educacionais, analisando "
    "indicadores do World Bank EdStats. Não repita números crus: interprete-os. "
    "Produza análise executiva em português (markdown) com estas seções:\n"
    "## Diagnóstico geral\n## Quem mais evoluiu e por quê\n## Quem estagnou ou regrediu\n"
    "## Investimento vs. resultado\n## Alertas e riscos\n## Recomendações acionáveis\n"
    "Seja específico: cite países e magnitudes, levante hipóteses causais plausíveis "
    "(sem inventar dados fora do dossiê) e proponha ações concretas."
)


def analise_executiva(dossie: dict) -> str:
    """Gera a análise executiva via OpenAI; cai no fallback local se indisponível."""
    if not config.ia_disponivel():
        print("  [ia] OPENAI_API_KEY ausente — usando análise local (fallback).")
        return _analise_local(dossie)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Analise o dossiê de indicadores educacionais a seguir "
                        "(JSON) e produza a análise executiva.\n\n"
                        f"{json.dumps(dossie, ensure_ascii=False, indent=2, default=str)}"
                    ),
                },
            ],
            temperature=0.4,
        )
        print(f"  [ia] análise executiva gerada via {config.OPENAI_MODEL}")
        return resp.choices[0].message.content.strip()
    except Exception as e:  # noqa: BLE001 — IA nunca derruba o pipeline
        print(f"  [ia] falha na OpenAI ({e}); usando análise local.")
        return _analise_local(dossie)


def _analise_local(dossie: dict) -> str:
    """Análise textual sem IA, para garantir relatório utilizável offline."""
    linhas = ["## Diagnóstico geral (fallback local, sem IA)"]

    lideres = dossie.get("lideres_crescimento", [])[:3]
    if lideres:
        txt = ", ".join(f"{d['Country Name']} ({d['cagr_pct']}%/ano)" for d in lideres)
        linhas.append(f"- **Maior crescimento (CAGR):** {txt}.")

    estagnados = dossie.get("estagnados", [])[:3]
    if estagnados:
        txt = ", ".join(f"{d['Country Name']} ({d['cagr_pct']}%/ano)" for d in estagnados)
        linhas.append(f"- **Estagnados/em queda:** {txt}.")

    alertas = dossie.get("alertas", [])
    if alertas:
        linhas.append(f"- **{len(alertas)} alertas** de indicadores abaixo do limite:")
        for a in alertas[:5]:
            linhas.append(f"  - {a['Country Name']}: {a['mensagem']} (valor {a['valor']}).")

    linhas.append(
        "\n> Configure `OPENAI_API_KEY` no `.env` para gerar a análise interpretativa completa."
    )
    return "\n".join(linhas)
