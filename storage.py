"""Upload de artefatos para o Supabase Storage.

Por que existe:
    Os CSVs gerados pelo pipeline vivem em data/processed/, mas no Render o
    filesystem é EFÊMERO — some a cada deploy/restart. Este módulo envia cada
    artefato para um bucket do Supabase Storage e devolve a URL pública, dando
    persistência de verdade fora do container.

Uso:
    from storage import upload_csv
    url = upload_csv(settings.processed_path / "edstats_final.csv")
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from supabase import Client, create_client

from config import settings


@lru_cache(maxsize=1)
def _client() -> Client:
    """Cria (uma única vez) o cliente Supabase.

    lru_cache => singleton por processo, equivalente a registrar o cliente como
    Singleton no DI do ASP.NET Core: abrir a conexão a cada upload seria desperdício.

    Usa a SERVICE ROLE key (via require_supabase): o upload é SERVER-SIDE. Essa
    chave ignora as regras de RLS, então NUNCA pode ir para frontend/cliente.
    """
    url, key = settings.require_supabase()
    return create_client(url, key)


def upload_csv(local_path: str | Path, *, destino: str | None = None) -> str:
    """Sobe um CSV local para o bucket e devolve a URL pública.

    Args:
        local_path: caminho do arquivo no disco
            (ex.: data/processed/edstats_final.csv).
        destino: nome/caminho do objeto DENTRO do bucket. Default = nome do arquivo.

    Returns:
        URL pública do arquivo no Supabase Storage.

    Raises:
        FileNotFoundError: se o artefato não existir no disco.
        RuntimeError: se SUPABASE_URL/SUPABASE_KEY não estiverem configuradas.
    """
    caminho = Path(local_path)
    if not caminho.exists():
        raise FileNotFoundError(f"Artefato não encontrado para upload: {caminho}")

    objeto = destino or caminho.name
    bucket = _client().storage.from_(settings.supabase_bucket)

    # upsert="true": re-execuções do pipeline sobrescrevem o MESMO nome de arquivo
    # (ex.: edstats_final.csv). Sem isso, o Supabase recusa com erro "Duplicate".
    bucket.upload(
        path=objeto,
        file=caminho.read_bytes(),
        file_options={"content-type": "text/csv", "upsert": "true"},
    )

    # get_public_url só resolve de verdade se o bucket for PÚBLICO. Se for privado,
    # troque por: bucket.create_signed_url(objeto, 3600)["signedURL"] (link temporário).
    # O .rstrip("?") remove um "?" final que algumas versões do SDK anexam.
    return bucket.get_public_url(objeto).rstrip("?")
