"""``Plug(type=...)`` is deprecated in favour of ``Plug(kind=...)``.

The old keyword shadowed the built-in ``type``.  The ``Plug.type`` attribute is
unchanged; only the constructor argument was renamed.
"""

from __future__ import annotations

import warnings

import pytest

from bdsim.blocks import Mux
from bdsim.connect import Plug


def test_kind_sets_type_attribute() -> None:
    assert Plug(Mux(2), kind="end").type == "end"
    assert Plug(Mux(2), 1, "start").type == "start"  # third positional argument
    assert Plug(Mux(2)).type == ""


def test_kind_does_not_warn(recwarn: pytest.WarningsRecorder) -> None:
    Plug(Mux(2), kind="end")

    assert not [w for w in recwarn if issubclass(w.category, DeprecationWarning)]


def test_type_keyword_is_deprecated_but_works() -> None:
    with pytest.warns(DeprecationWarning, match="use 'kind' instead") as record:
        plug = Plug(Mux(2), type="end")

    assert plug.type == "end"
    assert record[0].filename == __file__  # warning points at the caller


def test_kind_and_type_together_is_an_error() -> None:
    with pytest.raises(TypeError, match="only one of"):
        Plug(Mux(2), kind="start", type="end")


def test_type_is_keyword_only() -> None:
    with pytest.raises(TypeError):
        Plug(Mux(2), 0, "start", "end")  # type: ignore[misc]


def test_library_code_does_not_use_the_deprecated_keyword() -> None:
    """Wires are made of StartPlug and EndPlug; building a diagram must not warn."""
    from bdsim import BDSim

    sim = BDSim(
        toolboxes=False, load=True, banner=False, graphics=False, progress=False
    )
    bd = sim.blockdiagram()

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        bd.connect(bd.CONSTANT(1), bd.GAIN(2))
        bd.compile(verbose=False)
