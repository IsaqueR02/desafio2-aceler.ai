import subprocess

scripts = [
    "01_limpeza.py",
    "02_ausentes.py",
    "03_selecao.py",
    "04_agregacoes.py",
    "05_rankings.py",
    "06_crescimento.py",
    "07_comparacao.py",
    "08_export.py"
]

for script in scripts:
    print(f"Executando {script}...")
    subprocess.run(["python", f"scripts/{script}"])