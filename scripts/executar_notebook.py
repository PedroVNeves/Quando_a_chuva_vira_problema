"""Executa em processo limpo; --kernel usa um kernel Jupyter separado."""
import argparse
import os
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import AsyncKernelManager
from jupyter_core.utils import run_sync

raiz = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--timeout", type=int, default=1800)
parser.add_argument("--kernel", action="store_true")
args = parser.parse_args()
os.environ.setdefault("MPLCONFIGDIR", str(raiz / "tmp/matplotlib"))
os.environ.setdefault("IPYTHONDIR", str(raiz / "tmp/ipython"))
os.environ.setdefault("JUPYTER_RUNTIME_DIR", str(raiz / "tmp/jupyter"))
for diretorio in ["tmp/matplotlib", "tmp/ipython", "tmp/jupyter"]:
    (raiz / diretorio).mkdir(parents=True, exist_ok=True)
nb = nbformat.read(raiz / "analise.ipynb", as_version=4)
if not args.kernel:
    # Sem sockets: útil em ambientes que restringem a comunicação com kernels.
    import matplotlib
    matplotlib.use("module://matplotlib_inline.backend_inline")
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.utils.capture import capture_output
    os.chdir(raiz)
    sys.path.insert(0, str(raiz))
    shell = InteractiveShell.instance()
    numero = 0
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        numero += 1
        print(f"Executando célula {i}: {cell.id}", flush=True)
        with capture_output() as capturado:
            resultado = shell.run_cell(cell.source, store_history=False)
        cell.execution_count = numero
        cell.outputs = []
        for nome, valor in [("stdout", capturado.stdout), ("stderr", capturado.stderr)]:
            if valor:
                cell.outputs.append(nbformat.v4.new_output("stream", name=nome, text=valor))
        for saida in capturado.outputs:
            cell.outputs.append(nbformat.v4.new_output("display_data", data=saida.data, metadata=saida.metadata))
        if not resultado.success:
            nbformat.write(nb, raiz / "tmp/execucao_falhou.ipynb")
            print(capturado.stdout, capturado.stderr)
            raise resultado.error_in_exec or resultado.error_before_exec
    nbformat.validate(nb)
    nbformat.write(nb, raiz / "analise.ipynb")
    print("Notebook concluído em processo limpo e salvo sem erros.", flush=True)
    sys.exit(0)
km = AsyncKernelManager(kernel_name="python3")
km.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
def progresso(cell, cell_index, **kwargs):
    if cell.cell_type == "code":
        print(f"Executando célula {cell_index}: {cell.id}", flush=True)
client = NotebookClient(nb, km=km, timeout=args.timeout, resources={"metadata": {"path": str(raiz)}},
                        on_cell_start=progresso)
try:
    client.execute(cwd=str(raiz))
except Exception:
    nbformat.write(nb, raiz / "tmp/execucao_falhou.ipynb")
    raise
finally:
    if km.has_kernel:
        run_sync(km.shutdown_kernel)(now=True)
nbformat.write(nb, raiz / "analise.ipynb")
print("Notebook concluído e salvo sem erros.", flush=True)
