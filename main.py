"""Orquestrador do pipeline EdStats.

Executa os 8 scripts na ordem correta, encadeando a saída de uma etapa como
entrada da próxima (ver diagrama no README). Cada etapa é um processo Python
separado — se qualquer uma falhar, o pipeline para imediatamente.

Uso:
    python main.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from fastapi import FastAPI

app = FastAPI()

# Diretórios base, relativos a este arquivo (não ao working dir de quem chama).
RAIZ = Path(__file__).resolve().parent
SCRIPTS = RAIZ / "scripts"
RAW = RAIZ / "data" / "raw"
PROC = RAIZ / "data" / "processed"

# Arquivo bruto de entrada do World Bank EdStats.
ENTRADA = RAW / "WB_EDSTATS_WIDEF.csv"

# Cada etapa: (script, entrada, saida, *args_opcionais).
# A ordem respeita as dependências: 01→02→03 (base tidy) → análises → export.
S1 = PROC / "s1.csv"
S2 = PROC / "s2.csv"
S3 = PROC / "s3.csv"  # base "tidy" — entrada das análises 04–07
CRESCIMENTO = PROC / "crescimento.csv"

ETAPAS = [
    ("01_limpeza.py",     ENTRADA,     S1),
    ("02_ausentes.py",    S1,          S2),
    ("03_selecao.py",     S2,          S3),
    ("04_agregacoes.py",  S3,          PROC / "agregacoes.csv"),
    ("05_rankings.py",    S3,          PROC / "rankings.csv"),
    ("06_crescimento.py", S3,          CRESCIMENTO),
    ("07_comparacao.py",  S3,          PROC / "comparacao.csv"),
    ("08_export.py",      CRESCIMENTO, PROC / "edstats_final.csv"),
]


def main() -> None:
    if not ENTRADA.exists():
        sys.exit(f"Arquivo bruto não encontrado: {ENTRADA}")

    PROC.mkdir(parents=True, exist_ok=True)

    for script, entrada, saida, *extra in ETAPAS:
        print(f"Executando {script}...")
        # sys.executable garante o MESMO python (o do venv), não um "python" do PATH.
        cmd = [sys.executable, str(SCRIPTS / script), str(entrada), str(saida), *extra]
        # check=True: se a etapa retornar exit code != 0, levanta erro e o
        # pipeline para aqui — evita rodar as etapas seguintes com lixo/vazio.
        subprocess.run(cmd, check=True)

    print(f"\nPipeline concluído. Resultado final em: {PROC / 'edstats_final.csv'}")


if __name__ == "__main__":
    main()


@app.get("/run")
def run_pipeline():
    subprocess.run(["python", "main.py"])
    return {"status": "Pipeline executado com sucesso"}