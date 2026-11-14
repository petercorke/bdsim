"""
The ``projection`` argument of the ``ANIMATION`` block, which gives ``init`` 2D or 3D axes.
"""

from __future__ import annotations

import unittest
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless, must be set before pyplot is imported

import bdsim
from bdsim.exceptions import BlockCreationError


_UNSET: Any = (
    object()
)  # None is a real value of projection, so it cannot mean "not given"


def _run(
    projection: str | None = None,
    set_param: Any = _UNSET,
    **options: Any,
) -> dict[str, Any]:
    """
    Run a short diagram with an ``ANIMATION`` block, and record what ``init`` was given.

    :param projection: the ``projection`` argument of the block
    :param set_param: if given (``None`` included), the value set with ``set_param`` after the
        block is made
    :param options: options of the simulator, for example ``tiles``
    :return: the axes name, and the number of times ``update`` was called
    """
    seen: dict[str, Any] = {"updates": 0}

    def init(block: Any, fig: Any, ax: Any) -> None:
        seen["ax_name"] = ax.name  # "3d" or "rectilinear"
        seen["block_ax_is_ax"] = block.ax is ax
        if ax.name == "3d":
            (block.point,) = ax.plot([0], [0], [0], "ro")
        else:
            (block.point,) = ax.plot([0], [0], "ro")

    def update(block: Any, t: float, inports: list[Any]) -> None:
        seen["updates"] += 1
        if block.ax.name == "3d":
            block.point.set_data_3d([t], [0], [inports[0]])
        else:
            block.point.set_data([t], [inports[0]])

    sim = bdsim.BDSim(animation=False, backend="Agg", quiet=True, **options)
    bd = sim.blockdiagram()
    integrator = bd.INTEGRATOR(0.0)
    bd.connect(bd.CONSTANT(1.0), integrator)
    kwargs = {} if projection is None else {"projection": projection}
    anim = bd.ANIMATION(init, update, **kwargs)
    if set_param is not _UNSET:
        anim.set_param("projection", set_param)
    bd.connect(integrator, anim)
    bd.compile()
    sim.run(bd, T=0.5, dt=0.1)
    bd.done()
    return seen


class AnimationProjectionTest(unittest.TestCase):
    def test_default_is_2d(self) -> None:
        seen = _run()
        self.assertEqual(seen["ax_name"], "rectilinear")
        self.assertGreater(seen["updates"], 0)

    def test_3d(self) -> None:
        seen = _run(projection="3d")
        self.assertEqual(seen["ax_name"], "3d")
        self.assertTrue(seen["block_ax_is_ax"])  # init is given the block's own axes
        self.assertGreater(seen["updates"], 0)  # and update can move a 3D artist

    def test_none_is_2d(self) -> None:
        self.assertEqual(_run(projection=None)["ax_name"], "rectilinear")

    def test_set_param_before_the_run(self) -> None:
        # the axes are made when the run starts, so the projection can be changed until then
        self.assertEqual(_run(set_param="3d")["ax_name"], "3d")
        self.assertEqual(
            _run(projection="3d", set_param=None)["ax_name"], "rectilinear"
        )

    def test_tiled_layout(self) -> None:
        # a tiled figure gets its dark styling applied to the axes, which must work for 3D
        self.assertEqual(_run(projection="3d", tiles="1x2")["ax_name"], "3d")

    def test_bad_projection_is_rejected(self) -> None:
        for bad in ("2d", "3D", "polar", 3):
            with self.subTest(projection=bad):
                with self.assertRaises(BlockCreationError) as cm:
                    _run(projection=bad)  # type: ignore[arg-type]
                self.assertIn(
                    "projection", str(cm.exception.__context__)
                )  # the ValueError raised

    def test_bad_set_param_is_rejected(self) -> None:
        sim = bdsim.BDSim(animation=False, backend="Agg", quiet=True)
        bd = sim.blockdiagram()
        anim = bd.ANIMATION(lambda b, f, a: None, lambda b, t, u: None)
        with self.assertRaises(ValueError):
            anim.set_param("projection", "2d")
        self.assertIsNone(anim.projection)  # unchanged


if __name__ == "__main__":
    unittest.main()
