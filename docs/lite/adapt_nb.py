"""Adapt bouncing-ball.ipynb for JupyterLite/Pyodide.

Sets Pyodide kernelspec, prepends micropip install cell, removes !shell lines.
Run from docs/lite/ — reads from examples/ via the Makefile copy, writes
adapted result to docs/notebooks/.
"""

import json
from pathlib import Path

nb_path = Path("../notebooks/bouncing-ball.ipynb")
nb = json.loads(nb_path.read_text())

meta = nb.setdefault("metadata", {})
meta["kernelspec"] = {
    "name": "python",
    "display_name": "Python (Pyodide)",
    "language": "python",
}
meta.setdefault("language_info", {})["name"] = "python"

first_code = next((c for c in nb["cells"] if c.get("cell_type") == "code"), None)
has_piplite = first_code and "piplite" in "".join(
    first_code["source"]
    if isinstance(first_code["source"], list)
    else [first_code["source"]]
)
if not has_piplite:
    nb["cells"].insert(
        0,
        {
            "cell_type": "code",
            "id": "lite-install",
            "metadata": {},
            "outputs": [],
            "execution_count": None,
            "source": [
                "# Install bdsim.  In JupyterLite, piplite checks the local wheel\n",
                "# (built with 'make wheel') before falling back to PyPI.\n",
                "# In a regular Jupyter server this is a no-op (piplite is not available).\n",
                "try:\n",
                "    import piplite\n",
                "    await piplite.install('bdsim')\n",
                "except ImportError:\n",
                "    pass  # already installed (classic Jupyter)\n",
            ],
        },
    )

for cell in nb["cells"]:
    if cell.get("cell_type") != "code":
        continue
    src = cell["source"]
    lines = src.splitlines(keepends=True) if isinstance(src, str) else src
    cell["source"] = [l for l in lines if not l.lstrip().startswith("!")]

nb_path.write_text(json.dumps(nb, indent=1) + "\n")
print(f"adapted {nb_path}")
