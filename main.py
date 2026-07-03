"""Ponto de entrada do Agente de Monitoramento Educacional.

Uso:
    python main.py                 # roda o pipeline completo
    python main.py --gerar-dados   # gera dados de exemplo antes de rodar
"""
from __future__ import annotations

import argparse

from src import agente


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente de Monitoramento Educacional")
    parser.add_argument(
        "--gerar-dados",
        action="store_true",
        help="Gera um dataset de exemplo em data/raw antes de executar.",
    )
    args = parser.parse_args()

    if args.gerar_dados:
        from src import gerar_dados

        gerar_dados.gerar()

    agente.executar()


if __name__ == "__main__":
    main()
