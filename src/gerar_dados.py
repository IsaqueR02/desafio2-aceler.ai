"""Gera um dataset educacional fictício em CSV para testar o agente.

Cria três arquivos em data/raw:
  - alunos.csv       (cadastro)
  - notas.csv        (notas por disciplina/bimestre)
  - frequencia.csv   (aulas e faltas por disciplina)

Uso: python -m src.gerar_dados
"""
from __future__ import annotations

import random

import pandas as pd

from config import RAW_DIR

TURMAS = ["9A", "9B", "1A", "1B"]
DISCIPLINAS = ["Matemática", "Português", "Ciências", "História", "Geografia"]
NOMES = [
    "Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela", "Henrique",
    "Isabela", "João", "Karina", "Lucas", "Mariana", "Nathan", "Olívia", "Pedro",
    "Quezia", "Rafael", "Sofia", "Thiago", "Ursula", "Vitor", "Wesley", "Yasmin",
]
SOBRENOMES = ["Silva", "Souza", "Oliveira", "Santos", "Lima", "Costa", "Pereira", "Alves"]


def gerar(n_alunos: int = 40, seed: int = 42) -> None:
    rnd = random.Random(seed)

    alunos = []
    for i in range(1, n_alunos + 1):
        nome = f"{rnd.choice(NOMES)} {rnd.choice(SOBRENOMES)}"
        alunos.append({
            "id_aluno": i,
            "nome": nome,
            "turma": rnd.choice(TURMAS),
            "serie": rnd.choice(["9º Ano", "1ª Série EM"]),
        })
    df_alunos = pd.DataFrame(alunos)

    notas, frequencia = [], []
    for a in alunos:
        # Cada aluno tem um "perfil" que enviesa notas e presença.
        perfil = rnd.random()
        for disc in DISCIPLINAS:
            for bim in (1, 2, 3, 4):
                base = 8.5 if perfil > 0.7 else 6.0 if perfil > 0.3 else 4.0
                nota = round(min(10, max(0, rnd.gauss(base, 1.5))), 1)
                notas.append({
                    "id_aluno": a["id_aluno"],
                    "disciplina": disc,
                    "bimestre": bim,
                    "nota": nota,
                })
            aulas = 80
            faltas_base = 3 if perfil > 0.7 else 10 if perfil > 0.3 else 22
            faltas = max(0, int(rnd.gauss(faltas_base, 4)))
            frequencia.append({
                "id_aluno": a["id_aluno"],
                "disciplina": disc,
                "aulas_dadas": aulas,
                "faltas": min(faltas, aulas),
            })

    df_notas = pd.DataFrame(notas)
    df_freq = pd.DataFrame(frequencia)

    df_alunos.to_csv(RAW_DIR / "alunos.csv", index=False, encoding="utf-8")
    df_notas.to_csv(RAW_DIR / "notas.csv", index=False, encoding="utf-8")
    df_freq.to_csv(RAW_DIR / "frequencia.csv", index=False, encoding="utf-8")

    print(f"Dados gerados em {RAW_DIR}:")
    print(f"  alunos.csv     ({len(df_alunos)} linhas)")
    print(f"  notas.csv      ({len(df_notas)} linhas)")
    print(f"  frequencia.csv ({len(df_freq)} linhas)")


if __name__ == "__main__":
    gerar()
