"""Exercise the documented non-factory construction pattern."""

import numpy as np
import pytest

from bdsim import BDSim
from bdsim.blocks import Constant, Gain, Null


def test_non_factory_diagram_without_block_library(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Other tests populate this shared cache, masking the fresh-process failure.
    monkeypatch.setattr(BDSim, "_blocklibrary", None)
    sim = BDSim(load=False, banner=False, graphics=False, progress=False)
    bd = sim.blockdiagram(name="non-factory")

    assert bd.name == "non-factory"
    assert bd.runtime is sim
    assert BDSim._blocklibrary is None

    source = Constant(2, bd=bd)
    gain = Gain(3, bd=bd)
    sink = Null(bd=bd)
    bd.connect(source, gain)
    bd.connect(gain, sink)
    bd.compile(verbose=False)
    out = sim.run(bd, T=0.1, max_step=0.02, watch=[gain])

    np.testing.assert_allclose(out.y, 6)
    assert out.t[-1] == pytest.approx(0.1)


def test_loaded_library_still_binds_factories(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(BDSim, "_blocklibrary", None)
    sim = BDSim(banner=False, graphics=False, progress=False, toolboxes=False)
    bd = sim.blockdiagram()

    assert bd.runtime is sim
    assert isinstance(bd.CONSTANT(2), Constant)
