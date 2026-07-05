# 🌍 Pipeline de Tratamento EdStats — scripts modulares para n8n

Conjunto de **8 scripts Python independentes**, um por etapa de tratamento de
dados do **World Bank EdStats**. Cada script é uma função única, recebe um CSV
de entrada e grava um CSV de saída — desenhados para virar **nós no n8n**
(Execute Command), mas rodam também isolados no terminal.

## Fluxo

```
raw.csv
  │
  ▼ 01_limpeza      limpa + wide→long
  ▼ 02_ausentes     trata valores faltantes
  ▼ 03_selecao      totais + colunas essenciais (série única)  ──► base "tidy"
        ├─► 04_agregacoes    estatísticas por indicador×ano
        ├─► 05_rankings      posição dos países por indicador×ano
        ├─► 06_crescimento   variação % ano a ano
        └─► 07_comparacao    pivot países × anos (1 indicador)
  ▼ 08_export       CSV final otimizado (sem índice)
```

As etapas **01→02→03** formam a cadeia de limpeza. A partir da base *tidy*
(saída de `03`), as etapas **04–07** são análises independentes (podem rodar em
paralelo). `08` exporta qualquer resultado tratado como CSV final.

## Contrato de cada script

```bash
python scripts/NN_nome.py <entrada.csv> <saida.csv> [arg_opcional]
```

| Script | Função | Arg. opcional |
|---|---|---|
| `01_limpeza.py` | `limpar_dados` | — |
| `02_ausentes.py` | `tratar_ausentes` | estratégia: `descartar`(padrão)`\|mediana\|media\|zero` |
| `03_selecao.py` | `selecionar_indicadores` | lista de códigos: `COD1,COD2,...` |
| `04_agregacoes.py` | `agregar` | — |
| `05_rankings.py` | `rankear` | — |
| `06_crescimento.py` | `calcular_crescimento` | — |
| `07_comparacao.py` | `comparar_paises` | código do indicador |
| `08_export.py` | `exportar_csv_final` | — |

**Schema da base tidy** (saída de `03`): `pais_codigo, pais_nome,
indicador_codigo, indicador_nome, ano, valor`.

## Instalação

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

## Uso rápido (terminal)

```bash
R=data/raw/WB_EDSTATS_WIDEF.csv
P=data/processed

python scripts/01_limpeza.py     $R              $P/s1.csv
python scripts/02_ausentes.py    $P/s1.csv       $P/s2.csv
python scripts/03_selecao.py     $P/s2.csv       $P/s3.csv
python scripts/04_agregacoes.py  $P/s3.csv       $P/agregacoes.csv
python scripts/05_rankings.py    $P/s3.csv       $P/rankings.csv
python scripts/06_crescimento.py $P/s3.csv       $P/crescimento.csv
python scripts/07_comparacao.py  $P/s3.csv       $P/comparacao.csv
python scripts/08_export.py      $P/crescimento.csv $P/edstats_final.csv
```

## Integração com o n8n

Cada etapa vira um nó **Execute Command** encadeado. O host do n8n precisa ter
Python + `pandas`/`numpy` instalados (ou usar uma imagem custom).

Exemplo de comando em um nó:

```bash
python /data/scripts/02_ausentes.py /data/processed/s1.csv /data/processed/s2.csv mediana
```

Padrão de wiring:

```
[Manual/Schedule Trigger]
   -> [Execute Command: 01_limpeza]
   -> [Execute Command: 02_ausentes]
   -> [Execute Command: 03_selecao]   (produz a base tidy)
        |-> [Execute Command: 04_agregacoes]
        |-> [Execute Command: 05_rankings]
        |-> [Execute Command: 06_crescimento] -> [Execute Command: 08_export]
        |-> [Execute Command: 07_comparacao]
```

Dicas:
- Use caminhos **absolutos** nos comandos (o working dir do n8n varia).
- Cada script loga um resumo no **stdout** (linha `[NN] ...`) — aparece na saída
  do nó e ajuda no debug.
- Erros de uso saem com **exit code ≠ 0**, então o nó falha corretamente.

## Estrutura

```
.
├── scripts/            # os 8 scripts (um por etapa)
├── data/
│   ├── raw/            # CSV de entrada (WB_EDSTATS_WIDEF.csv)
│   └── processed/      # saídas (ignoradas pelo git)
├── requirements.txt
└── README.md
```
