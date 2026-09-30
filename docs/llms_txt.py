"""Write llms.txt and llms-full.txt for the documentation site.

``llms.txt`` (see https://llmstxt.org) is a short Markdown index that tells AI assistants
what the package is and where its documentation lives. ``llms-full.txt`` is the whole
documentation as plain text, so an assistant can read it in a single fetch.

Two sources are combined:

- this Sphinx site, rendered by Sphinx's ``text`` builder, so the autodoc API reference
  (block library, simulation API) is included, not just the ``.rst`` sources. Pages are
  taken in the order of the toctree in ``index.rst``;
- the bdsim wiki (tutorials, worked examples, design notes), cloned fresh from GitHub and
  taken in the order of its sidebar, with the sidebar's headings and notes.

In ``llms-full.txt`` the introductory pages come first, then the wiki, then the API
reference, so the how-to material is not buried behind the reference. Run after the HTML
build::

    make html llms          # from docs/

The files are written into ``build/html`` so they are published with the site. If the
wiki can't be cloned, they are written without it and a warning is printed.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from importlib.metadata import metadata
from pathlib import Path

DOCS = Path(__file__).resolve().parent
SOURCE = DOCS / "source"
BUILD = DOCS / "build"
TEXT = BUILD / "text"
HTML = BUILD / "html"
WIKI = BUILD / "wiki"
WIKI_GIT = "https://github.com/petercorke/bdsim.wiki.git"
WIKI_URL = "https://github.com/petercorke/bdsim/wiki/"

# Sphinx pages that are API reference; they go last in llms-full.txt
API_PAGES = {"bdsim.blocks", "internals"}

# Links that belong in llms.txt but are neither pages of this site nor wiki pages
EXTRA_LINKS = [
    ("Example notebooks", "https://github.com/petercorke/bdsim/tree/main/docs/notebooks", "Jupyter notebooks, also runnable in the browser from the documentation site"),
    ("Source code", "https://github.com/petercorke/bdsim", "GitHub repository; examples are in examples/"),
    ("PyPI", "https://pypi.org/project/bdsim/", "install with pip install bdsim"),
    ("RVC ecosystem", "https://github.com/petercorke/rvc-ecosystem", "how bdsim relates to the Robotics and Machine Vision Toolboxes"),
]


@dataclass
class WikiSection:
    """A heading of the wiki sidebar and the pages listed under it."""

    heading: str
    note: str = ""  # any prose under the heading, e.g. "under development"
    pages: list[tuple[str, str]] = field(default_factory=list)  # (title, page name)


def toctree_pages(index: Path) -> list[str]:
    """Document names listed in the toctrees of the master document, in order.

    :param index: the master document, ``index.rst``
    :return: document names such as ``"bdsim.blocks"``
    """
    pages, in_toctree = [], False
    for line in index.read_text().splitlines():
        if line.startswith(".. toctree::"):
            in_toctree = True
        elif in_toctree and line.strip() and not line.startswith((" ", "\t")):
            in_toctree = False  # the directive's indented body has ended
        elif in_toctree and line.strip() and not line.strip().startswith(":"):
            pages.append(line.strip())
    return pages


def title(text: str) -> str:
    """The page title: the first line, which the text builder underlines."""
    return text.splitlines()[0].strip()


def clone_wiki() -> bool:
    """Clone the wiki into ``build/wiki``, replacing any earlier copy.

    :return: whether the clone succeeded
    """
    shutil.rmtree(WIKI, ignore_errors=True)
    result = subprocess.run(["git", "clone", "-q", "--depth", "1", WIKI_GIT, str(WIKI)], capture_output=True, text=True)
    if result.returncode:
        print(f"warning: wiki not included, clone failed: {result.stderr.strip()}", file=sys.stderr)
    return result.returncode == 0


def wiki_sections() -> list[WikiSection]:
    """The wiki's pages grouped and ordered as in its sidebar.

    Links to pages that don't exist yet, and links off the wiki, are skipped; headings
    left with no pages are dropped.

    :return: sidebar sections, in order
    """
    sections: list[WikiSection] = []
    for line in (WIKI / "_Sidebar.md").read_text().splitlines():
        if heading := re.match(r"#+\s+(.*)", line):
            sections.append(WikiSection(heading[1].strip()))
        elif link := re.match(r"\s*[-*]\s+\[([^]]+)\]\(([^)]+)\)", line):
            name = link[2]
            if "://" not in name and (WIKI / f"{name}.md").exists() and sections:
                sections[-1].pages.append((link[1], name))
        elif line.strip() and sections:
            sections[-1].note += (" " if sections[-1].note else "") + line.strip()
    return [s for s in sections if s.pages]


def main() -> None:
    # Read the name, summary and documentation URL from the installed package's metadata
    # (built from pyproject.toml). Reading pyproject.toml directly would need tomllib,
    # which is Python 3.11+, and the Pages workflow still builds the docs on 3.10. 3.10
    # reaches end of life in October 2026; once CI moves past it, tomllib is an option.
    meta = metadata("bdsim")
    urls = dict(u.split(", ", 1) for u in meta.get_all("Project-URL"))
    base = urls["documentation"].rstrip("/") + "/"
    name, summary = meta["Name"], meta["Summary"]

    subprocess.run(
        [os.environ.get("SPHINXBUILD", "sphinx-build"), "-q", "-b", "text", str(SOURCE), str(TEXT)],
        check=True,
    )
    pages = ["index"] + toctree_pages(SOURCE / "index.rst")
    texts = {p: (TEXT / f"{p}.txt").read_text() for p in pages}
    wiki = wiki_sections() if clone_wiki() else []

    # llms.txt: the index
    index = [
        f"# {name}",
        "",
        f"> {summary}. This is the documentation site for the `{name}` Python package.",
        "",
        f"Two sources document {name}: this site, which is the API reference (every class, method "
        f"and block), and the [bdsim wiki]({WIKI_URL}Home), which has the tutorials, worked "
        f"examples and design notes. Both are available together as a single text file: "
        f"[llms-full.txt]({base}llms-full.txt).",
        "",
        "## API reference",
        "",
        *(f"- [{title(texts[p])}]({base}{p}.html)" for p in pages),
        "",
    ]
    for s in wiki:
        index += [f"## Wiki: {s.heading}", ""]
        if s.note:
            index += [s.note, ""]
        index += [f"- [{t}]({WIKI_URL}{n})" for t, n in s.pages] + [""]
    index += ["## Optional", "", *(f"- [{label}]({url}): {note}" for label, url, note in EXTRA_LINKS), ""]
    HTML.mkdir(parents=True, exist_ok=True)
    (HTML / "llms.txt").write_text("\n".join(index))

    # llms-full.txt: everything, introduction first, API reference last
    def block(url: str, body: str) -> str:
        return f"\n{'=' * 72}\nPage: {url}\n{'=' * 72}\n\n{body.strip()}\n"

    parts = [f"# {name}: {summary}\n\nAPI reference: {base}\nWiki: {WIKI_URL}Home\n"]
    parts += [block(f"{base}{p}.html", texts[p]) for p in pages if p not in API_PAGES]
    for s in wiki:
        note = f"\n({s.note})\n" if s.note else ""
        for t, n in s.pages:
            parts.append(block(f"{WIKI_URL}{n}", f"# {t}\n{note}\n" + (WIKI / f"{n}.md").read_text()))
    parts += [block(f"{base}{p}.html", texts[p]) for p in pages if p in API_PAGES]
    full = re.sub(r"\n{3,}", "\n\n", "".join(parts))  # the text builder leaves runs of blank lines
    (HTML / "llms-full.txt").write_text(full)
    n_wiki = sum(len(s.pages) for s in wiki)
    print(f"llms.txt: {len(pages)} site pages, {n_wiki} wiki pages; llms-full.txt: {len(full) // 1000} kB", file=sys.stderr)


if __name__ == "__main__":
    main()
