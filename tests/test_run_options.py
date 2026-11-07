"""Options given to BDSim.run: they apply to that run, and the command line wins.

run(**options) takes the options that can differ from one run to the next.  The
ones that are fixed when BDSim is constructed (the block library, the banner) raise
TypeError rather than being silently ignored.
"""

import contextlib
import io
import os
import sys
import unittest
from unittest import mock

os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np

import bdsim


def make(sysargs: bool = False, argv: list[str] | None = None, **options):
    """A BDSim and a diagram: a constant 1, a gain named ``g`` and an integrator.

    The output at time T is ``K * T`` where K is the gain.
    """
    kwargs = dict(banner=False, quiet=True, progress=False, graphics=False)
    kwargs.update(options)
    with mock.patch.object(sys, "argv", ["prog"] + (argv or [])):
        sim = bdsim.BDSim(sysargs=sysargs, **kwargs)
    bd = sim.blockdiagram()
    gain = bd.GAIN(2.0, name="g")
    integrator = bd.INTEGRATOR(x0=0.0, name="i")
    bd.connect(bd.CONSTANT(1.0), gain)
    bd.connect(gain, integrator)
    bd.connect(integrator, bd.NULL(1))
    bd.compile(verbose=False)
    return sim, bd


def captured(function, *args, **kwargs):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        result = function(*args, **kwargs)
    return result, out.getvalue()


class RejectedTest(unittest.TestCase):
    def test_an_unknown_option_is_a_type_error_with_a_suggestion(self):
        sim, bd = make()
        with self.assertRaises(TypeError) as cm:
            sim.run(bd, animaton=True)
        self.assertIn("'animaton'", str(cm.exception))
        self.assertIn("did you mean 'animation'", str(cm.exception))

    def test_a_construction_only_option_is_a_type_error_with_the_reason(self):
        sim, bd = make()
        for name, value in (("blocks", True), ("verbose", True), ("banner", False)):
            with self.subTest(name):
                with self.assertRaises(TypeError) as cm:
                    sim.run(bd, **{name: value})
                self.assertIn(f"{name!r}", str(cm.exception))
                self.assertIn("constructed", str(cm.exception))

    def test_simtime_and_method_point_to_the_parameters_to_use(self):
        sim, bd = make()
        with self.assertRaisesRegex(TypeError, r"as T"):
            sim.run(bd, simtime="3")
        with self.assertRaisesRegex(TypeError, r"as solver"):
            sim.run(bd, method="BDF")

    def test_a_bad_value_is_refused(self):
        sim, bd = make()
        with self.assertRaisesRegex(ValueError, "max_frames must be >= 0"):
            sim.run(bd, max_frames=-1)


class ForThisRunTest(unittest.TestCase):
    def test_an_option_applies_to_one_run_only(self):
        sim, bd = make(graphics=True)
        self.assertEqual(sim.run(bd, T=2)[".stats"].animation_frames, 0)
        self.assertGreater(
            sim.run(bd, T=2, animation=True)[".stats"].animation_frames, 0
        )
        self.assertEqual(sim.run(bd, T=2)[".stats"].animation_frames, 0)
        self.assertFalse(sim.options.animation)

    def test_an_option_overrides_the_constructor(self):
        sim, bd = make(graphics=True, animation=True)
        self.assertEqual(
            sim.run(bd, T=2, animation=False)[".stats"].animation_frames, 0
        )

    def test_the_named_parameters_are_options_too(self):
        sim, bd = make()
        out = sim.run(bd, T=1, dt=0.25)
        np.testing.assert_allclose(np.diff(out.t), 0.25)

    def test_block_is_the_hold_option(self):
        sim, bd = make()
        with mock.patch.object(
            sim, "_make_run_options", wraps=sim._make_run_options
        ) as m:
            sim.run(bd, T=1, block=False, hold=True)
        # block wins over hold, as the named parameter
        self.assertIs(m.call_args.kwargs["hold"], False)

    def test_animation_turns_graphics_on_as_it_does_in_the_constructor(self):
        sim, bd = make(graphics=False)
        out = sim.run(bd, T=1, animation=True)
        self.assertGreater(out[".stats"].animation_frames, 0)

    def test_submit_passes_the_options_on(self):
        sim, bd = make()
        job = sim.submit(bd, T=1, dt=0.5)
        np.testing.assert_allclose(np.diff(job.result().t), 0.5)

    def test_a_backend_that_cannot_be_selected_raises(self):
        sim, bd = make(graphics=True)
        scope = bd.SCOPE()
        bd.connect(bd["i"], scope)
        bd.compile(verbose=False)
        with self.assertRaisesRegex(RuntimeError, "can't select matplotlib backend"):
            sim.run(bd, T=1, backend="nosuchbackend")


class CommandLineWinsTest(unittest.TestCase):
    def test_the_command_line_beats_an_option(self):
        sim, bd = make(sysargs=True, argv=["--dt", "0.5"])
        out, text = captured(sim.run, bd, T=1, quiet=False, dt=0.1)
        np.testing.assert_allclose(np.diff(out.t), 0.5)
        self.assertIn("overriden by command line option dt=0.5", text)

    def test_the_command_line_beats_an_option_that_is_not_a_named_parameter(self):
        sim, bd = make(sysargs=True, argv=["--max-frames", "7"], graphics=True)
        out, _ = captured(sim.run, bd, T=10, animation=True, max_frames=500)
        # one frame per 10/7 s, and the first
        self.assertEqual(out[".stats"].animation_frames, 8)

    def test_an_option_the_command_line_does_not_set_still_applies(self):
        sim, bd = make(sysargs=True, argv=["--dt", "0.5"])
        out = sim.run(bd, T=1, atol=1e-9)
        np.testing.assert_allclose(np.diff(out.t), 0.5)

    def test_no_graphics_on_the_command_line_stops_an_animation(self):
        sim, bd = make(sysargs=True, argv=["--no-graphics"])
        out, text = captured(sim.run, bd, T=1, animation=True)
        self.assertEqual(out[".stats"].animation_frames, 0)
        self.assertIn("option animation=True is overriden by command line", text)
        self.assertIn("option graphics=True is overriden by command line", text)


class NoGraphicsEnvironmentTest(unittest.TestCase):
    """BDSIM_NO_GRAPHICS, for tests and CI, outranks anything run() is given."""

    def test_graphics_stay_off_whatever_run_is_given(self):
        with mock.patch.dict(os.environ, {"BDSIM_NO_GRAPHICS": "1"}):
            sim, bd = make(graphics=True)
            out, text = captured(
                sim.run, bd, T=1, graphics=True, animation=True, backend="nosuchbackend"
            )
        self.assertEqual(out[".stats"].animation_frames, 0)
        self.assertIn("option graphics=True is overriden by command line", text)


class SetParamTest(unittest.TestCase):
    def final(self, out) -> float:
        return float(out.x[-1, 0])

    def test_a_dict_sets_the_parameters_with_python_values(self):
        sim, bd = make()
        out, text = captured(sim.run, bd, T=2, quiet=False, setparam={"g:K": 3})
        self.assertAlmostEqual(self.final(out), 6.0, places=6)
        self.assertIn("changed value of g:K from 2.0 -> 3", text)

    def test_quiet_suppresses_the_report_of_the_change(self):
        sim, bd = make()  # quiet
        out, text = captured(sim.run, bd, T=2, setparam={"g:K": 3})
        self.assertAlmostEqual(self.final(out), 6.0, places=6)
        self.assertNotIn("changed value", text)

    def test_quiet_suppresses_the_report_of_the_command_line_too(self):
        sim, bd = make(sysargs=True, argv=["-s", "g:K=4"])
        out, text = captured(sim.run, bd, T=2)
        self.assertAlmostEqual(self.final(out), 8.0, places=6)
        self.assertNotIn("changed value", text)

    def test_the_block_can_be_given_by_id(self):
        sim, bd = make()
        out, _ = captured(sim.run, bd, T=2, setparam={f"{bd['g'].id}:K": 4})
        self.assertAlmostEqual(self.final(out), 8.0, places=6)

    def test_it_changes_the_block_for_the_runs_that_follow(self):
        # documented: setparam is not for this run only
        sim, bd = make()
        captured(sim.run, bd, T=2, setparam={"g:K": 3})
        self.assertEqual(bd["g"].K, 3)
        out = sim.run(bd, T=2)
        self.assertAlmostEqual(self.final(out), 6.0, places=6)

    def test_the_command_line_beats_the_dict(self):
        sim, bd = make(sysargs=True, argv=["-s", "g:K=4"])
        out, _ = captured(sim.run, bd, T=2, setparam={"g:K": 3})
        self.assertAlmostEqual(self.final(out), 8.0, places=6)
        self.assertEqual(bd["g"].K, 4)

    def test_a_value_of_the_wrong_kind_is_refused_as_set_param_does(self):
        sim, bd = make()
        with self.assertRaisesRegex(ValueError, r"cannot set g:K"):
            sim.run(bd, T=1, setparam={"g:K": "three"})

    def test_an_unknown_block_or_parameter_is_refused(self):
        sim, bd = make()
        with self.assertRaisesRegex(ValueError, r"cannot set g:nope"):
            sim.run(bd, T=1, setparam={"g:nope": 1})
        with self.assertRaises(Exception):
            sim.run(bd, T=1, setparam={"nosuchblock:K": 1})

    def test_a_key_without_a_parameter_is_refused(self):
        sim, bd = make()
        with self.assertRaisesRegex(ValueError, r"want 'block:param'"):
            sim.run(bd, T=1, setparam={"g": 1})

    def test_the_command_line_text_form_is_not_accepted_from_code(self):
        sim, bd = make()
        with self.assertRaisesRegex(TypeError, r"takes a dict"):
            sim.run(bd, T=1, setparam=["g:K=3"])


if __name__ == "__main__":
    unittest.main()
