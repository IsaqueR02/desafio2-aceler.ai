"""Serviço HTTP (FastAPI) que expõe o pipeline EdStats para o n8n.

Por que existe:
    O nó 'Execute Command' do n8n foi descontinuado. Agora o n8n dispara o
    pipeline pelo nó 'HTTP Request' (POST /pipeline/run). Este arquivo mantém a
    orquestração por SUBPROCESS (cada etapa é um processo Python isolado — se uma
    falhar, o pipeline para; e a memória do CSV é liberada entre etapas), mas
    embrulha tudo numa API com validação, tratamento de erro e resposta JSON.

Rodar em desenvolvimento:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    # docs interativas: http://localhost:8000/docs

Ainda funciona como CLI (compatibilidade):
    python main.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

# Importar config ancora a raiz no sys.path e carrega o .env (fonte única de config).
from config import settings

# ------------------------------------------------------------------
# Diretórios e caminhos dos artefatos (vindos do config central).
# ------------------------------------------------------------------
SCRIPTS = settings.project_root / "scripts"
PROC = settings.processed_path
# Pasta onde o CSV enviado pelo n8n é gravado antes de processar. Resolvida pela
# raiz do projeto (absoluta) — NUNCA um "data/raw" relativo, que dependeria do
# diretório de trabalho e quebraria no Render.
RAW_DIR = settings.raw_data_path.parent

S1 = PROC / "s1.csv"
S2 = PROC / "s2.csv"
S3 = PROC / "s3.csv"  # base "tidy" — entrada das análises 04–07
AGREGACOES = PROC / "agregacoes.csv"
RANKINGS = PROC / "rankings.csv"
CRESCIMENTO = PROC / "crescimento.csv"
COMPARACAO = PROC / "comparacao.csv"
FINAL = PROC / "edstats_final.csv"


# ------------------------------------------------------------------
# Contrato de entrada (DTO). Pydantic valida e documenta sozinho.
# Todos os campos são opcionais e caem em defaults sensatos.
# ------------------------------------------------------------------
class PipelineRequest(BaseModel):
    entrada: str | None = Field(
        default=None,
        description="Caminho do CSV bruto. Se omitido, usa settings.raw_data_path.",
    )
    estrategia_ausentes: str = Field(
        default="descartar",
        description="Etapa 02: descartar | mediana | media | zero.",
    )
    indicadores: list[str] | None = Field(
        default=None,
        description="Etapa 03: filtra estes códigos de indicador. Vazio = todos.",
    )
    indicador_comparacao: str | None = Field(
        default=None,
        description="Etapa 07: indicador da matriz país×ano. Vazio = o de maior cobertura.",
    )


def montar_etapas(entrada: Path, req: PipelineRequest) -> list[tuple[str, Path, Path, list[str]]]:
    """Monta a lista de etapas (script, entrada, saída, args_extra) já com os
    parâmetros opcionais do request injetados nas etapas que os aceitam.

    O DAG: 01→02→03 (base tidy) → 04/05/07 partem da base; 06 parte de 05;
    08 finaliza a série com crescimento.
    """
    return [
        ("01_limpeza.py", entrada, S1, []),
        ("02_ausentes.py", S1, S2, [req.estrategia_ausentes]),
        ("03_selecao.py", S2, S3, [",".join(req.indicadores)] if req.indicadores else []),
        ("04_agregacoes.py", S3, AGREGACOES, []),
        ("05_rankings.py", S3, RANKINGS, []),
        ("06_crescimento.py", RANKINGS, CRESCIMENTO, []),
        ("07_comparacao.py", S3, COMPARACAO, [req.indicador_comparacao] if req.indicador_comparacao else []),
        ("08_export.py", CRESCIMENTO, FINAL, []),
    ]


def executar_pipeline(req: PipelineRequest) -> list[str]:
    """Roda todas as etapas em sequência via subprocess. Devolve os logs (stdout)
    de cada etapa. Levanta HTTPException em caso de entrada ou execução inválida.
    """
    PROC.mkdir(parents=True, exist_ok=True)

    entrada = Path(req.entrada) if req.entrada else settings.raw_data_path
    if not entrada.exists():
        raise HTTPException(status_code=404, detail=f"Entrada não encontrada: {entrada}")

    # Força o processo-filho a EMITIR UTF-8 no stdout/stderr (no Windows o
    # default seria cp1252), casando com o encoding que usamos para capturar.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    logs: list[str] = []
    for script, ent, saida, extra in montar_etapas(entrada, req):
        # sys.executable => o MESMO python do venv, não um "python" qualquer do PATH.
        cmd = [sys.executable, str(SCRIPTS / script), str(ent), str(saida), *extra]
        try:
            # check=True: exit code != 0 vira CalledProcessError e o pipeline para.
            # capture_output: guardamos stdout/stderr para observabilidade na resposta.
            # encoding=utf-8: no Windows o default é cp1252 e truncaria acentos dos logs.
            resultado = subprocess.run(
                cmd, check=True, capture_output=True, text=True,
                encoding="utf-8", errors="replace", env=env,
            )
        except subprocess.CalledProcessError as exc:
            # Os scripts usam sys.exit(msg) para erros de validação; a mensagem
            # cai no stderr. Surface isso ao chamador (n8n) em vez de engolir.
            detalhe = (exc.stderr or exc.stdout or "").strip() or f"Falha em {script}"
            # Traceback => bug inesperado (500). Mensagem simples => validação (422).
            status = 500 if "Traceback" in detalhe else 422
            raise HTTPException(status_code=status, detail=f"[{script}] {detalhe}") from exc
        logs.append(resultado.stdout.strip())
    return logs

API_KEY = os.getenv("PIPELINE_API_KEY")


app = FastAPI(
    title="Pipeline EdStats",
    version="1.0.0",
    description="Orquestra as 8 etapas de ETL do World Bank EdStats para o n8n.",
)

@app.get("/")
def root():
    return {"message": "Servidor FastAPI está rodando!"}


@app.get("/health")
def health() -> dict:
    """Health check — o n8n/monitoramento verifica se o serviço está no ar."""
    return {"status": "ok", "raw_data_path": str(settings.raw_data_path)}


@app.post("/pipeline/run")
async def run_pipeline(
    # O CSV bruto enviado pelo n8n (nó Google Drive -> HTTP Request, body
    # multipart/form-data). Opcional: se ausente, cai no settings.raw_data_path —
    # útil ao rodar localmente com o arquivo já em disco.
    arquivo: UploadFile | None = File(default=None),
    # Em multipart os demais parâmetros chegam como campos de formulário, não JSON.
    estrategia_ausentes: str = Form(default="descartar"),
    indicadores: str | None = Form(default=None),  # códigos separados por vírgula
    indicador_comparacao: str | None = Form(default=None),
) -> dict:
    """Recebe o CSV bruto (upload), roda o pipeline completo e devolve os
    caminhos dos artefatos + logs — tudo numa única requisição.

    Por que upload+run juntos: o filesystem do Render é EFÊMERO (some a cada
    deploy/restart/spin-down). Separar 'upload' de 'run' em duas chamadas guardaria
    estado entre requisições numa plataforma stateless — frágil. Aqui o arquivo só
    precisa existir durante o processamento, então gravamos em RAW_DIR (descartável)
    e apontamos o pipeline para ele.
    """
    entrada: str | None = None
    if arquivo is not None:
        # Grava o upload via streaming (copyfileobj) — não carrega o CSV inteiro
        # na memória, o que importa para o dataset grande do EdStats.
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        destino = RAW_DIR / (arquivo.filename or "upload.csv")
        with destino.open("wb") as f:
            shutil.copyfileobj(arquivo.file, f)
        entrada = str(destino)

    req = PipelineRequest(
        entrada=entrada,
        estrategia_ausentes=estrategia_ausentes,
        indicadores=[c.strip() for c in indicadores.split(",") if c.strip()] if indicadores else None,
        indicador_comparacao=indicador_comparacao,
    )

    logs = executar_pipeline(req)
    return {
        "status": "ok",
        "parametros": req.model_dump(),
        "artefatos": {
            "serie_base": str(S3),
            "agregacoes": str(AGREGACOES),
            "rankings": str(RANKINGS),
            "crescimento": str(CRESCIMENTO),
            "comparacao": str(COMPARACAO),
            "final": str(FINAL),
        },
        "logs": logs,
    }



# ------------------------------------------------------------------
# Compatibilidade: ainda dá para rodar o pipeline pelo terminal.
# ------------------------------------------------------------------
if __name__ == "__main__":
    for linha in executar_pipeline(PipelineRequest()):
        print(linha)
    print(f"\nPipeline concluído. Resultado final em: {FINAL}")
