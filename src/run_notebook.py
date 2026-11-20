"""Execute a notebook in place with the *current* Python interpreter as the kernel.

A temporary kernelspec named python3 is put first on JUPYTER_PATH, so the notebook
always runs in the same virtual environment as this script, whatever kernels are
installed elsewhere on the machine.

Usage:
    python -m src.run_notebook notebooks/<name>.ipynb
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def execute(path: Path, timeout: int = 1200) -> None:
    tmp = Path(tempfile.mkdtemp())
    spec = tmp / "kernels" / "python3"
    spec.mkdir(parents=True)
    (spec / "kernel.json").write_text(json.dumps({
        "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "Python 3", "language": "python"}))
    os.environ["JUPYTER_PATH"] = os.pathsep.join(filter(None, [str(tmp), os.environ.get("JUPYTER_PATH")]))
    nb = nbformat.read(path, as_version=4)
    client = NotebookClient(nb, kernel_name="python3", timeout=timeout,
                            resources={"metadata": {"path": str(path.parent)}})
    client.execute()
    nbformat.write(nb, path)
    print(f"executed {path}")


if __name__ == "__main__":
    execute(Path(sys.argv[1]).resolve())
