"""Etapa 4 — RELATÓRIO.

Monta o relatório em Markdown, converte para PDF e envia por e-mail.
Cada saída é independente: falha em PDF/e-mail não impede as demais.
"""
from __future__ import annotations

import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import pandas as pd

import config


def montar_markdown(df: pd.DataFrame, indicadores: dict, insights: str, data: str) -> str:
    """Gera o corpo do relatório em Markdown."""
    ind = indicadores
    tabela_turmas = "| Turma | Alunos | Média | Freq. média | Risco alto |\n|---|---|---|---|---|\n"
    for t in ind["por_turma"]:
        tabela_turmas += (
            f"| {t['turma']} | {t['alunos']} | {t['media_geral']} | "
            f"{t['frequencia_media']}% | {t['risco_alto']} |\n"
        )

    tabela_risco = "| Aluno | Turma | Média | Frequência |\n|---|---|---|---|\n"
    for a in ind["alunos_risco_alto"]:
        tabela_risco += (
            f"| {a['nome']} | {a['turma']} | {a['media_geral']} | {a['frequencia_pct']}% |\n"
        )
    if not ind["alunos_risco_alto"]:
        tabela_risco += "| _Nenhum aluno em risco alto_ | | | |\n"

    return f"""# Relatório de Monitoramento Educacional

**Gerado em:** {data}
**Total de alunos:** {ind['total_alunos']}

## 1. Indicadores gerais

- **Média geral da escola:** {ind['media_geral_escola']}
- **Frequência média:** {ind['frequencia_media_escola']}%
- **Aprovados:** {ind['pct_aprovados']}% | **Recuperação:** {ind['pct_recuperacao']}% | **Reprovados:** {ind['pct_reprovados']}%
- **Risco de evasão:** {ind['risco_evasao_alto']} alto / {ind['risco_evasao_medio']} médio

## 2. Desempenho por turma

{tabela_turmas}
## 3. Alunos em risco alto de evasão

{tabela_risco}
## 4. Análise inteligente (IA)

{insights}

---
*Relatório gerado automaticamente pelo Agente Inteligente de Monitoramento Educacional.*
"""


def salvar_markdown(conteudo: str, nome: str) -> Path:
    caminho = config.REPORTS_DIR / f"{nome}.md"
    caminho.write_text(conteudo, encoding="utf-8")
    print(f"  [relatório] Markdown salvo: {caminho}")
    return caminho


def salvar_pdf(conteudo_md: str, nome: str) -> Path | None:
    """Converte Markdown -> HTML -> PDF (puro Python, funciona no Windows)."""
    try:
        import markdown2
        from xhtml2pdf import pisa

        html_corpo = markdown2.markdown(conteudo_md, extras=["tables", "fenced-code-blocks"])
        html = f"""<html><head><meta charset="utf-8"><style>
            body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11px; color: #222; }}
            h1 {{ color: #1a4f8b; }} h2 {{ color: #1a4f8b; border-bottom: 1px solid #ccc; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #bbb; padding: 4px 6px; text-align: left; }}
            th {{ background: #eef3fa; }}
        </style></head><body>{html_corpo}</body></html>"""

        caminho = config.REPORTS_DIR / f"{nome}.pdf"
        with open(caminho, "wb") as f:
            resultado = pisa.CreatePDF(html, dest=f)
        if resultado.err:
            print("  [relatório] erro ao gerar PDF.")
            return None
        print(f"  [relatório] PDF salvo: {caminho}")
        return caminho
    except Exception as e:  # noqa: BLE001
        print(f"  [relatório] PDF indisponível ({e}).")
        return None


def enviar_email(assunto: str, corpo_md: str, anexo_pdf: Path | None) -> bool:
    """Envia o relatório por e-mail (SMTP) com o PDF anexado, se houver."""
    if not config.email_disponivel():
        print("  [relatório] e-mail não configurado — envio ignorado.")
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = assunto
        msg["From"] = config.EMAIL_REMETENTE
        msg["To"] = ", ".join(config.EMAIL_DESTINATARIOS)
        msg.set_content(corpo_md)

        if anexo_pdf and anexo_pdf.exists():
            msg.add_attachment(
                anexo_pdf.read_bytes(),
                maintype="application",
                subtype="pdf",
                filename=anexo_pdf.name,
            )

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
            smtp.send_message(msg)
        print(f"  [relatório] e-mail enviado para: {', '.join(config.EMAIL_DESTINATARIOS)}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  [relatório] falha ao enviar e-mail: {e}")
        return False


def gerar_relatorios(df: pd.DataFrame, indicadores: dict, insights: str) -> dict:
    """Orquestra as saídas do relatório e devolve os caminhos gerados."""
    print("[4/4] Geração de relatórios...")
    agora = datetime.now()
    nome = f"relatorio_{agora:%Y%m%d_%H%M}"
    data_fmt = agora.strftime("%d/%m/%Y %H:%M")

    md = montar_markdown(df, indicadores, insights, data_fmt)
    caminho_md = salvar_markdown(md, nome)
    caminho_pdf = salvar_pdf(md, nome)
    enviado = enviar_email("Relatório de Monitoramento Educacional", md, caminho_pdf)

    return {"markdown": caminho_md, "pdf": caminho_pdf, "email_enviado": enviado}
