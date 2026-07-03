# 🎓 Agente Inteligente de Monitoramento Educacional

Automatiza o fluxo completo de **coleta → tratamento → análise → relatório**
de dados educacionais, usando **IA (OpenAI)** para gerar insights pedagógicos
e distribuindo o resultado em **Markdown, PDF e e-mail**.

## Como funciona

```
┌──────────┐   ┌────────────┐   ┌───────────┐   ┌────────────┐
│  COLETA  │──▶│ TRATAMENTO │──▶│  ANÁLISE  │──▶│ RELATÓRIO  │
│ CSV/XLSX │   │ limpa e    │   │ métricas  │   │ MD + PDF   │
│          │   │ consolida  │   │ + IA (GPT)│   │ + e-mail   │
└──────────┘   └────────────┘   └───────────┘   └────────────┘
```

- **Coleta** (`src/coleta.py`): lê `alunos`, `notas` e `frequencia` de `data/raw` (CSV ou Excel).
- **Tratamento** (`src/tratamento.py`): limpa, valida, consolida por aluno e classifica situação/risco de evasão.
- **Análise** (`src/analise.py`): calcula indicadores por escola/turma e gera insights com a OpenAI (com fallback local se a IA não estiver configurada).
- **Relatório** (`src/relatorio.py`): monta Markdown, converte para PDF e envia por e-mail.
- **Agente** (`src/agente.py`): orquestra tudo de ponta a ponta.

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
```

## Configuração

Copie `.env.example` para `.env` e preencha:

```bash
copy .env.example .env
```

- `OPENAI_API_KEY` — chave da OpenAI (sem ela, o agente usa análise local).
- Bloco `SMTP_*` / `EMAIL_*` — credenciais de e-mail (Gmail: use uma **Senha de app**).
- `NOTA_MINIMA_APROVACAO`, `FREQUENCIA_MINIMA` — regras de negócio.

> Tudo é opcional para testar: sem chave e sem SMTP, o pipeline roda e gera o Markdown/PDF localmente.

## Uso

```bash
# 1) Gerar dados de exemplo e rodar o fluxo completo
python main.py --gerar-dados

# 2) Rodar com seus próprios dados (colocados em data/raw)
python main.py
```

Saídas em `reports/` (`.md` e `.pdf`) e tabela consolidada em `data/processed/consolidado.csv`.

## Formato dos dados de entrada (`data/raw/`)

**alunos.csv**

| id_aluno | nome        | turma | serie   |
|----------|-------------|-------|---------|
| 1        | Ana Silva   | 9A    | 9º Ano  |

**notas.csv**

| id_aluno | disciplina | bimestre | nota |
|----------|------------|----------|------|
| 1        | Matemática | 1        | 7.5  |

**frequencia.csv**

| id_aluno | disciplina | aulas_dadas | faltas |
|----------|------------|-------------|--------|
| 1        | Matemática | 80          | 4      |

## Estrutura

```
desafio2/
├── main.py              # entrypoint (CLI)
├── config.py           # configuração e regras de negócio
├── requirements.txt
├── .env.example
├── data/
│   ├── raw/            # entrada (CSV/Excel)
│   └── processed/      # consolidado gerado
├── reports/            # relatórios (.md / .pdf)
└── src/
    ├── gerar_dados.py  # gerador de dataset fictício
    ├── coleta.py       # etapa 1
    ├── tratamento.py   # etapa 2
    ├── analise.py      # etapa 3 (métricas + IA)
    ├── relatorio.py    # etapa 4 (MD/PDF/e-mail)
    └── agente.py       # orquestrador
```
