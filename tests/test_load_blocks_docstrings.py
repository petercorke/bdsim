"""Block discovery must cope with the different ways of documenting parameters.

Block libraries are scanned by parsing their source (``BDSim.load_blocks``).  The
convention is to omit ``:type:`` lines for parameters that have type hints in the
signature, so a docstring may have ``:param`` lines and no ``:type`` lines at all.
Older libraries document every parameter with both.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bdsim import BDSim

BLOCKS_SOURCE = '''
class OldStyle(FunctionBlock):
    nin = 1
    nout = 1

    def __init__(self, K=1, mode=None, **blockargs):
        """
        :param K: the gain, defaults to 1
        :type K: float, optional
        :param mode: the mode, defaults to None
        :type mode: str, optional
        :param blockargs: |BlockOptions|
        :type blockargs: dict
        """


class NewStyle(FunctionBlock):
    nin = 1
    nout = 1

    def __init__(self, K: float = 1, mode: str | None = None, **blockargs) -> None:
        """
        :param K: the gain, defaults to 1
        :param mode: the mode, defaults to None
        :param blockargs: |BlockOptions|
        """


class Mixed(FunctionBlock):
    nin = 1
    nout = 1

    def __init__(self, K: float = 1, mode: str | None = None, **blockargs) -> None:
        """
        :param K: the gain, defaults to 1
        :param mode: the mode, defaults to None
        :type mode: str, optional
        """


class Broken(FunctionBlock):
    nin = 1
    nout = 1

    def __init__(self, K: float = 1, **blockargs) -> None:
        """
        :param K: the gain, defaults to 1
        """
'''


def clean(param: tuple[str | None, str]) -> tuple[str | None, str]:
    """Strip the whitespace the parser keeps after each field's closing colon."""
    typ, description = param
    return (None if typ is None else typ.strip(), description.strip())


@pytest.fixture
def library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Load the blocks from a throwaway block library, in addition to bdsim's own."""
    blocks = tmp_path / "mylib_blocks"
    blocks.mkdir()
    (blocks / "gains.py").write_text(BLOCKS_SOURCE, encoding="utf-8")

    # the library is cached on the class, so make sure it is rebuilt, and restored
    monkeypatch.setattr(BDSim, "_blocklibrary", None)

    def load() -> dict:
        BDSim(
            packages=str(blocks),
            toolboxes=False,
            banner=False,
            graphics=False,
            progress=False,
        )
        assert BDSim._blocklibrary is not None
        return BDSim._blocklibrary

    return load


def test_old_style_docstring_has_types(library) -> None:
    params = library()["OLDSTYLE"]["params"]

    assert clean(params["K"]) == ("float, optional", "the gain, defaults to 1")
    assert clean(params["mode"]) == ("str, optional", "the mode, defaults to None")


def test_docstring_without_type_lines(library) -> None:
    """Regression test: this used to raise ``KeyError: 'type'`` from BDSim()."""
    params = library()["NEWSTYLE"]["params"]

    assert clean(params["K"]) == (None, "the gain, defaults to 1")
    assert clean(params["mode"]) == (None, "the mode, defaults to None")


def test_docstring_with_some_type_lines(library) -> None:
    params = library()["MIXED"]["params"]

    assert clean(params["K"]) == (None, "the gain, defaults to 1")
    assert clean(params["mode"]) == ("str, optional", "the mode, defaults to None")


def test_unparseable_docstring_does_not_stop_loading(
    library, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """One block that cannot be parsed is reported, the rest still load."""
    get_docstring = ast.get_docstring

    def fake_get_docstring(node, *args, **kwargs):
        if getattr(node, "name", None) == "Broken":
            return 123  # not a string, so joining the docstrings fails
        return get_docstring(node, *args, **kwargs)

    monkeypatch.setattr(ast, "get_docstring", fake_get_docstring)

    blocks = library()
    out = capsys.readouterr().out

    assert blocks["BROKEN"]["params"] == {}
    assert "could not parse the docstring of block Broken" in out
    assert ":param gain:" in out  # the message shows what a docstring should look like
    assert clean(blocks["NEWSTYLE"]["params"]["K"]) == (
        None,
        "the gain, defaults to 1",
    )
    assert blocks["GAIN"]["params"]  # bdsim's own blocks are unaffected
