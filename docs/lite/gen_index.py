"""Generate pypi/all.json piplite index from wheels in pypi/.

piplite checks this index before falling back to PyPI, so a locally-built
wheel takes priority over the released version.
Run from docs/lite/.
"""

import json
from pathlib import Path

pypi = Path("pypi")
index: dict = {}

for whl in sorted(pypi.glob("*.whl")):
    # wheel filename: {name}-{version}-{python}-{abi}-{platform}.whl
    parts = whl.stem.split("-")
    name = parts[0].lower().replace("_", "-")
    version = parts[1]
    entry = {
        "name": parts[0],
        "version": version,
        "filename": whl.name,
        "url": whl.name,
    }
    index.setdefault(name, []).append(entry)

(pypi / "all.json").write_text(json.dumps(index, indent=2) + "\n")
print(
    f"wrote pypi/all.json ({', '.join(f'{k} {v[0]['version']}' for k, v in index.items())})"
)
