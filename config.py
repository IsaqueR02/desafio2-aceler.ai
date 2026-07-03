"""Configuração central do Agente de Inteligência Global em Educação.

Baseado no dataset World Bank Education Statistics (EdStats/Kaggle).
Carrega variáveis de ambiente (.env), define caminhos, os indicadores-chave
monitorados e as regras de alerta usadas por todas as etapas do pipeline.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---- Caminhos ----
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"            # arquivos de entrada (EdStatsData.csv etc.)
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = BASE_DIR / "reports"    # relatórios e gráficos gerados

for _dir in (RAW_DIR, PROCESSED_DIR, REPORTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ---- IA (OpenAI) ----
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

# ---- E-mail (opcional, para distribuição do relatório) ----
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", SMTP_USER).strip()
EMAIL_DESTINATARIOS = [
    e.strip() for e in os.getenv("EMAIL_DESTINATARIOS", "").split(",") if e.strip()
]

# ---- Indicadores-chave monitorados (código EdStats -> nome amigável) ----
# Códigos reais do World Bank EdStats. São o "cardápio" padrão de análise;
# o usuário pode escolher outros pela CLI.
INDICADORES_CHAVE: dict[str, str] = {
    "SE.ADT.LITR.ZS": "Taxa de alfabetização adultos (% 15+)",
    "SE.XPD.TOTL.GD.ZS": "Gasto público em educação (% do PIB)",
    "SE.XPD.TOTL.GB.ZS": "Gasto em educação (% do gasto do governo)",
    "SE.PRM.ENRR": "Matrícula ensino primário (% bruta)",
    "SE.SEC.ENRR": "Matrícula ensino secundário (% bruta)",
    "SE.TER.ENRR": "Matrícula ensino superior (% bruta)",
    "SE.PRM.CMPT.ZS": "Taxa de conclusão do primário (%)",
    "SE.PRM.TCAQ.ZS": "Professores treinados no primário (%)",
}

# ---- Alertas (bônus): dispara quando o indicador cruza um limite ----
# Formato: código -> {"operador": "<"|">", "limite": float, "mensagem": str}
ALERTAS: dict[str, dict] = {
    "SE.ADT.LITR.ZS": {
        "operador": "<", "limite": 80.0,
        "mensagem": "Alfabetização adulta abaixo de 80%",
    },
    "SE.XPD.TOTL.GD.ZS": {
        "operador": "<", "limite": 4.0,
        "mensagem": "Investimento em educação abaixo de 4% do PIB (referência UNESCO)",
    },
    "SE.PRM.CMPT.ZS": {
        "operador": "<", "limite": 90.0,
        "mensagem": "Conclusão do primário abaixo de 90%",
    },
}

# ---- Defaults de análise ----
PAISES_PADRAO = ["BRA", "ARG", "CHL", "MEX", "USA", "FIN", "KOR", "PRT"]
ANO_INICIO_PADRAO = 2000
ANO_FIM_PADRAO = 2015


def ia_disponivel() -> bool:
    """Indica se há chave da OpenAI configurada e válida."""
    return bool(OPENAI_API_KEY) and not OPENAI_API_KEY.lower().startswith(("coloque", "sua-", "your"))


def email_disponivel() -> bool:
    """Indica se o envio de e-mail está configurado."""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD and EMAIL_DESTINATARIOS)
