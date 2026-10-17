from unittest.mock import patch

import numpy as np

from bdsim import BDSim, BlockDiagram
from bdsim.blocks.functions import Gain
from bdsim.blocks.sinks import Null
from bdsim.blocks.sources import Step


def test_load_false_blockdiagram() -> None:
    with patch.object(BDSim, "_blocklibrary", None):
        sim = BDSim(load=False)
        bd = sim.blockdiagram()

        assert isinstance(bd, BlockDiagram)
        assert bd.runtime is sim
        assert not any(name.isupper() for name in vars(bd))
        assert sim._blocklibrary is None


def test_load_false_imported_blocks_run() -> None:
    with patch.object(BDSim, "_blocklibrary", None):
        sim = BDSim(load=False, graphics=False, progress=False, banner=False)
        bd = sim.blockdiagram()
        step = Step(T=0.1, off=0, on=2, bd=bd)
        gain = Gain(3, bd=bd)
        sink = Null(bd=bd)
        bd.connect(step, gain)
        bd.connect(gain, sink)
        bd.compile()

        out = sim.run(bd, T=0.2, dt=0.01, watch=[gain])

        assert out.t[-1] >= 0.2
        np.testing.assert_allclose(out.y[out.t < 0.1, 0], 0)
        np.testing.assert_allclose(out.y[out.t > 0.1, 0], 6)
        assert sim._blocklibrary is None


def test_load_true_binds_factory_methods() -> None:
    with patch.object(BDSim, "_blocklibrary", None):
        sim = BDSim(load=True, graphics=False, progress=False, banner=False)
        bd = sim.blockdiagram()

        assert bd.runtime is sim
        assert sim._blocklibrary
        for name in sim._blocklibrary:
            assert callable(vars(bd)[name])
            assert vars(bd)[name].__self__ is sim
        assert isinstance(bd.STEP(), Step)
        assert isinstance(bd.GAIN(3), Gain)
        assert isinstance(bd.NULL(), Null)
