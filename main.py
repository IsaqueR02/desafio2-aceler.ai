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
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
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


# ------------------------------------------------------------------
# Execução assíncrona: registro de jobs em memória.
#
# Por quê: processar um CSV grande leva minutos. Se fizermos isso DENTRO da
# requisição HTTP, o proxy do Render (e o nó HTTP do n8n) estoura o timeout e
# devolve 502. A solução é responder 202 na hora com um job_id e processar em
# background; o n8n consulta GET /pipeline/status/{job_id} até terminar.
#
# Analogia .NET: um ConcurrentDictionary<string, JobStatus> alimentado por um
# BackgroundService. LIMITAÇÃO consciente: este dicionário vive na MEMÓRIA do
# processo — some se o serviço reiniciar e não é compartilhado entre instâncias.
# Para o escopo atual (1 instância) é suficiente; se um dia escalar, troque por
# Redis/banco. Veja "Pontos de atenção".
# ------------------------------------------------------------------
ARTEFATOS = {
    "serie_base": str(S3),
    "agregacoes": str(AGREGACOES),
    "rankings": str(RANKINGS),
    "crescimento": str(CRESCIMENTO),
    "comparacao": str(COMPARACAO),
    "final": str(FINAL),
}

JOBS: dict[str, dict] = {}


def _processar_job(job_id: str, req: PipelineRequest) -> None:
    """Roda o pipeline em background e atualiza o status do job.

    Como é uma função síncrona (def), o BackgroundTasks a executa num THREADPOOL,
    então o subprocess.run bloqueante NÃO congela o event loop do uvicorn — o
    /health e o polling de status continuam respondendo enquanto o ETL roda.
    """
    JOBS[job_id]["status"] = "processando"
    try:
        JOBS[job_id]["logs"] = executar_pipeline(req)
        JOBS[job_id]["artefatos"] = ARTEFATOS
        JOBS[job_id]["status"] = "concluido"
    except HTTPException as exc:
        # Erros de validação/execução tratados no pipeline (404/422/500).
        JOBS[job_id]["status"] = "erro"
        JOBS[job_id]["erro"] = exc.detail
    except Exception as exc:  # rede de segurança para qualquer falha inesperada
        JOBS[job_id]["status"] = "erro"
        JOBS[job_id]["erro"] = str(exc)


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


@app.post("/pipeline/run", status_code=202)
async def run_pipeline(
    background_tasks: BackgroundTasks,
    # O CSV bruto enviado pelo n8n (nó Google Drive -> HTTP Request, body
    # multipart/form-data). Opcional: se ausente, cai no settings.raw_data_path —
    # útil ao rodar localmente com o arquivo já em disco.
    arquivo: UploadFile | None = File(default=None),
    # Em multipart os demais parâmetros chegam como campos de formulário, não JSON.
    estrategia_ausentes: str = Form(default="descartar"),
    indicadores: str | None = Form(default=None),  # códigos separados por vírgula
    indicador_comparacao: str | None = Form(default=None),
) -> dict:
    """Recebe o CSV bruto (upload), ENFILEIRA o pipeline em background e devolve
    202 + job_id na hora. O n8n acompanha por GET /pipeline/status/{job_id}.

    Por que assíncrono: processar o CSV grande leva minutos; fazer isso dentro da
    requisição estoura o timeout do proxy (Render) e do n8n -> 502. Aqui só o
    trabalho RÁPIDO (salvar o upload) roda na requisição; o ETL pesado vai pro
    background.

    Por que salvar o arquivo AGORA e não no background: o UploadFile é fechado
    quando a resposta é enviada — não daria para lê-lo depois. Então persistimos
    em RAW_DIR (efêmero/descartável, resolvido pela raiz do projeto) e passamos
    apenas o CAMINHO para o job.
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

    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"status": "pendente", "logs": None, "artefatos": None, "erro": None}
    # add_task só dispara DEPOIS que esta resposta 202 for enviada ao n8n.
    background_tasks.add_task(_processar_job, job_id, req)

    return {
        "status": "aceito",
        "job_id": job_id,
        "status_url": f"/pipeline/status/{job_id}",
        "parametros": req.model_dump(),
    }

@app.get("/pipeline/status/{job_id}")
def pipeline_status(job_id: str) -> dict:
    """Consulta o andamento de um job. O n8n faz polling aqui até status virar
    'concluido' ou 'erro'. Estados: pendente -> processando -> concluido | erro.
    """
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job_id desconhecido: {job_id}")
    return {"job_id": job_id, **job}

@app.get("/pipeline/artifacts/{job_id}/{nome}")
def get_artifact(job_id: str, nome: str):
    path = f"data/processed/{nome}.csv"
    return FileResponse(path, media_type="text/csv", filename=f"{nome}.csv")
# ------------------------------------------------------------------
# Compatibilidade: ainda dá para rodar o pipeline pelo terminal.
# ------------------------------------------------------------------
if __name__ == "__main__":
    for linha in executar_pipeline(PipelineRequest()):
        print(linha)
    print(f"\nPipeline concluído. Resultado final em: {FINAL}")
