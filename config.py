"""Configuração central do projeto — fonte única de verdade.

Todos os scripts (scripts/*.py) e o main.py devem importar daqui em vez de
chamar os.getenv() por conta própria. Assim evitamos:

  - repetição de leitura de variáveis em cada arquivo;
  - erros de digitação em nomes de variáveis (falham em silêncio no getenv);
  - segredos espalhados pelo código.

O carregamento acontece a partir do arquivo .env (NUNCA versionado — veja o
.gitignore). Se uma variável obrigatória estiver faltando, o programa falha
imediatamente com uma mensagem clara (fail-fast), em vez de quebrar lá na
frente com um erro obscuro.

Uso:
    from config import settings
    df = pd.read_csv(settings.raw_data_path)
    modelo = settings.openai_model
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# ------------------------------------------------------------------
# Raiz do projeto: ancorada no local DESTE arquivo, não no diretório
# de trabalho (cwd). Isso garante que o .env é encontrado mesmo quando
# um script é executado de dentro de scripts/ ou pelo n8n.
# Garantindo que a raiz do projeto esteja no sys.path
# ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Carrega o .env para dentro de os.environ. override=False => variáveis já
# definidas no ambiente (ex.: injetadas pelo n8n ou pelo Docker) têm
# prioridade sobre o arquivo .env.
load_dotenv(PROJECT_ROOT / ".env", override=False)


# ------------------------------------------------------------------
# Helpers de leitura — cada um resolve um tipo de valor.
# ------------------------------------------------------------------
def _get(chave: str, padrao: str | None = None, *, obrigatoria: bool = False) -> str | None:
    """Lê uma variável de texto do ambiente.

    obrigatoria=True => falha imediatamente se estiver ausente/vazia,
    protegendo contra segredos esquecidos (ex.: OPENAI_API_KEY).
    """
    valor = os.getenv(chave, padrao)
    if obrigatoria and not valor:
        raise RuntimeError(
            f"[config] Variável obrigatória '{chave}' ausente. "
            f"Copie o .env.example para .env e preencha o valor."
        )
    return valor


def _get_path(chave: str, padrao: str, *, obrigatoria: bool = False) -> Path:
    """Lê um caminho e o resolve a partir da raiz do projeto.

    Caminhos relativos (ex.: 'data/raw/x.csv') viram absolutos ancorados na
    PROJECT_ROOT — funcionam igual em Windows e Linux.
    """
    bruto = _get(chave, padrao, obrigatoria=obrigatoria) or padrao
    caminho = Path(bruto)
    return caminho if caminho.is_absolute() else PROJECT_ROOT / caminho


def _get_list(chave: str, padrao: str = "", *, separador: str = ",") -> list[str]:
    """Lê uma lista separada por vírgula (ex.: 'BR,US,PT' -> ['BR','US','PT'])."""
    bruto = _get(chave, padrao) or ""
    return [item.strip() for item in bruto.split(separador) if item.strip()]


# ------------------------------------------------------------------
# Objeto de configuração — imutável (frozen) para ninguém alterar um
# valor em tempo de execução por engano. Equivalente a uma classe de
# Options do .NET populada uma única vez no startup.
# ------------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    # ---- Caminhos base ----
    project_root: Path = PROJECT_ROOT

    # ---- Banco de dados / origem dos dados ----
    database_url: str | None = field(default_factory=lambda: _get("DATABASE_URL"))

    # ---- IA (OpenAI) ----
    # Opcional: o ETL roda sem IA. A validação de presença da chave deve ficar
    # a cargo do código que REALMENTE chama a OpenAI (ex.: settings.require_openai()),
    # e não travar os scripts de tratamento puro de dados.
    openai_api_key: str | None = field(
        default_factory=lambda: _get("OPENAI_API_KEY")
    )
    openai_model: str = field(
        default_factory=lambda: _get("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini"
    )

    # ---- Caminhos de dados ----
    raw_data_path: Path = field(
        default_factory=lambda: _get_path("RAW_DATA_PATH", "data/raw/WB_EDSTATS_WIDEF.csv")
    )
    processed_path: Path = field(
        default_factory=lambda: _get_path("PROCESSED_PATH", "data/processed/")
    )

    # ---- Parâmetros globais do sistema ----
    default_countries: list[str] = field(
        default_factory=lambda: _get_list("DEFAULT_COUNTRIES")
    )
    default_indicators: list[str] = field(
        default_factory=lambda: _get_list("DEFAULT_INDICATORS")
    )

    def require_openai(self) -> str:
        """Retorna a chave da OpenAI ou falha na hora, com mensagem clara.

        Chame isto SOMENTE no código que de fato usa IA:
            client = OpenAI(api_key=settings.require_openai())
        Assim os scripts de ETL puro seguem rodando sem exigir a chave.
        """
        if not self.openai_api_key:
            raise RuntimeError(
                "[config] OPENAI_API_KEY ausente, mas esta etapa usa IA. "
                "Preencha a chave no .env."
            )
        return self.openai_api_key

    def __repr__(self) -> str:
        """Repr seguro: NUNCA imprime a chave de API inteira em logs."""
        chave = self.openai_api_key or ""
        chave_mascarada = f"{chave[:6]}...{chave[-4:]}" if len(chave) > 12 else "<oculta>"
        return (
            "Settings("
            f"database_url={self.database_url!r}, "
            f"openai_model={self.openai_model!r}, "
            f"openai_api_key={chave_mascarada!r}, "
            f"raw_data_path={str(self.raw_data_path)!r}, "
            f"processed_path={str(self.processed_path)!r}, "
            f"default_countries={self.default_countries!r}, "
            f"default_indicators={self.default_indicators!r})"
        )


# Instância única, importada por todo o projeto: `from config import settings`.
# Como o Python cacheia módulos, isto é lido do .env uma só vez por processo.
settings = Settings()
