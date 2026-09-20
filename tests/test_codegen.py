#!/usr/bin/env python3
"""Tests for bdsim.codegen -- the Python-to-C++ transpiler for sampled
block diagrams (see codegen.py's module docstring for the supported
Python subset, and claude-notes/codegen-embedded-plan.md for the design
rationale and the bug writeups these regression tests lock in).

Structure:
  1. Unit-level tests for specific pieces (VarType, CppEmitter, fixname).
  2. Regression tests, one per bug found during development.
  3. "codegen succeeds" tests against known-good diagrams.
  4. Compile-verification / numeric cross-check, skipped without a C++
     toolchain + Eigen.
  5. IR coverage sanity check.
"""

from __future__ import annotations

import glob
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import bdsim
from bdsim.codegen import (
    IR,
    Codegen,
    CppEmitter,
    IRInliner,
    IRSpecializer,
    VarType,
    fixname,
    ir_coverage_report,
    reset_ir_coverage,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_CODEGEN = REPO_ROOT / "examples" / "codegen"


def _find_eigen_include() -> str | None:
    """Best-effort search for an Eigen3 include dir, for compile-verification
    tests. Mirrors examples/codegen/verify_codegen.py's own search."""
    candidates = [
        "/usr/include/eigen3",
        "/usr/local/include/eigen3",
        *glob.glob("/opt/homebrew/Cellar/eigen/*/include/eigen3"),
        *glob.glob("/usr/local/Cellar/eigen/*/include/eigen3"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


CLANGXX = shutil.which("clang++")
EIGEN_INCLUDE = _find_eigen_include()
CAN_COMPILE = CLANGXX is not None and EIGEN_INCLUDE is not None
SKIP_COMPILE_REASON = "no clang++/Eigen3 toolchain found for compile verification"


def _empty_cfg() -> SimpleNamespace:
    """Minimal cfg for constructing a CppEmitter directly, bypassing a real
    block diagram -- enough for vartype_to_str/literal_to_str unit tests."""
    return SimpleNamespace(self={}, itypes=[], otypes=[])


def _generate(bd, **kwargs) -> str:
    """Run Codegen against a compiled diagram; return the generated C++ text."""
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "codegen.cpp")
        Codegen(output_path=out, **kwargs).generate(bd)
        return Path(out).read_text()


def _assert_compiles(test: unittest.TestCase, cpp: str) -> None:
    """Real clang++ compile-check of generated C++ text. No-op (silently)
    when CAN_COMPILE is False -- callers should still assert on the
    generated text itself so there's *some* coverage without a toolchain."""
    if not CAN_COMPILE:
        return
    with tempfile.TemporaryDirectory() as d:
        cpp_path = os.path.join(d, "check.cpp")
        Path(cpp_path).write_text(cpp)
        result = subprocess.run(
            [CLANGXX, "-std=c++17", f"-I{EIGEN_INCLUDE}", "-c", cpp_path,
             "-o", os.path.join(d, "check.o")],
            text=True, capture_output=True, timeout=60,
        )
        test.assertEqual(result.returncode, 0, result.stderr)


def _function_diagram(fn, nin=1, nout=1):
    """CONSTANT(s) -> FUNCTION(fn) -> SCOPE, compiled and ready for codegen.
    The common shape for exercising FUNCTION-block lowering/inlining."""
    sim = bdsim.BDSim(animation=False)
    bd = sim.blockdiagram()
    src = bd.CONSTANT(4.0, name="src")
    block = bd.FUNCTION(fn, nin=nin, nout=nout, name="fn_block")
    scope = bd.SCOPE(nin=nout)
    bd.connect(src, block)
    if nout == 1:
        bd.connect(block, scope[0])
    else:
        for i in range(nout):
            bd.connect(block[i], scope[i])
    bd.compile()
    return bd


# Module-level, not nested in a test method: IRInliner.inline() resolves a
# sibling helper by bare name through the *top-level* callable's own
# __globals__ (IRSpecializer.extra_globals) -- a function nested inside a
# test method has no module-level __globals__ entry for its neighbours, so
# these must be real module globals to exercise that path at all.
def _sibling_helper_a(v):
    tmp = v * 2
    return tmp


def _sibling_helper_b(v):
    tmp = v * 3
    return tmp


def _sibling_outer(u):
    return [_sibling_helper_a(u), _sibling_helper_b(u)]


def _math_pi_helper(u):
    return u + math.pi


def _sqrt_helper(u):
    return math.sqrt(u)


def _unregistered_math_helper(u):
    # math.gamma is deliberately not among the math.* intrinsics
    # registered in codegen.py -- used to keep exercising the "call to an
    # unresolvable name fails loudly and specifically" path now that
    # math.sqrt itself is a real, working intrinsic (see
    # test_math_sqrt_is_a_working_intrinsic).
    return math.gamma(u)


def _norm_helper(u):
    return np.linalg.norm(np.array([u, u]))


def _standalone_integrator_s_diagram():
    """CONSTANT -> INTEGRATOR_S -> SCOPE. A minimal, fully in-scope
    (sampled-only) diagram -- unlike KnownGoodDiagramTests' "original
    demo" (which includes a continuous LTI_SISO block, out of scope for
    this codegen effort and not actually compilable -- see bdsim#93),
    this is safe to use for real compile verification."""
    sim = bdsim.BDSim(animation=False)
    bd = sim.blockdiagram()
    clock = bd.clock(10, "Hz")
    src = bd.CONSTANT(1.0, name="src")
    integ = bd.INTEGRATOR_S(clock, x0=0.0, gain=1.0, name="integ")
    scope = bd.SCOPE(nin=1)
    bd.connect(src, integ)
    bd.connect(integ, scope)
    bd.compile()
    return bd


# ---------------------------------------------------------------------------
# 1. Unit-level tests
# ---------------------------------------------------------------------------


class VarTypeTests(unittest.TestCase):
    def test_numpy_float64_keeps_explicit_width(self):
        # regression: np.float64 is itself a `float` subclass -- must not
        # silently narrow to the plain-Python-float default width.
        vt = VarType(np.float64(1.0))
        self.assertEqual(vt.dtype, "ndarray")
        self.assertEqual(vt.etype, "float64")

    def test_numpy_uint16_scalar_keeps_width(self):
        vt = VarType(np.uint16(5))
        self.assertEqual(vt.etype, "uint16")

    def test_plain_python_float_has_no_explicit_width(self):
        vt = VarType(1.0)
        self.assertEqual(vt.dtype, "float")
        self.assertIsNone(vt.etype)

    def test_unsupported_value_raises(self):
        with self.assertRaises(ValueError):
            VarType(object())


class CppEmitterUnitTests(unittest.TestCase):
    def setUp(self):
        self.emitter = CppEmitter(_empty_cfg())

    def test_string_literal_uses_double_quotes(self):
        # regression: literal_to_str used to render Python repr() (single
        # quotes), which isn't valid C++ string syntax.
        s = self.emitter.literal_to_str("it's a test")
        self.assertTrue(s.startswith('"') and s.endswith('"'))

    def test_string_literal_escapes_embedded_quotes(self):
        self.assertEqual(self.emitter.literal_to_str('say "hi"'), '"say \\"hi\\""')

    def test_numpy_scalar_literal_renders_native_value(self):
        self.assertEqual(self.emitter.literal_to_str(np.float32(1.5)), "1.5")

    def test_numpy_bool_literal(self):
        self.assertEqual(self.emitter.literal_to_str(np.bool_(True)), "true")

    def test_0d_ndarray_vartype_is_plain_scalar_not_eigen(self):
        vt = VarType._make("ndarray", "float64", ())
        self.assertEqual(self.emitter.vartype_to_str(vt), "double")

    def test_default_int_float_types_are_configurable(self):
        emitter = CppEmitter(
            _empty_cfg(), default_int_type="int16_t", default_float_type="double"
        )
        self.assertEqual(emitter.vartype_to_str(VarType(1)), "int16_t")
        self.assertEqual(emitter.vartype_to_str(VarType(1.0)), "double")


class FixnameTests(unittest.TestCase):
    def test_replaces_every_non_alnum_character(self):
        self.assertEqual(fixname("gain.0"), "gain_0")
        self.assertEqual(fixname("motor-out 1"), "motor_out_1")


# ---------------------------------------------------------------------------
# 2. Regression tests -- one per bug found writing/using this codegen
# ---------------------------------------------------------------------------


class RegressionTests(unittest.TestCase):
    def test_sibling_helpers_get_distinct_inlined_locals(self):
        """Two sibling helper calls sharing a local name used to collide
        under IRInliner's old depth-keyed rename prefix -- both outputs
        silently got the *second* helper's value. Fixed via a per-call-site
        unique_id. Also exercises IRSpecializer.extra_globals (sibling
        module-level functions resolved by bare name -- _sibling_helper_a/b
        must be real module globals, not nested in this test, precisely
        because that's the mechanism under test)."""
        cpp = _generate(_function_diagram(_sibling_outer, nin=1, nout=2))
        self.assertIn("_il1_tmp", cpp)
        self.assertIn("_il2_tmp", cpp)
        self.assertIn("_il1_tmp = (inports._0 * 2)", cpp)
        self.assertIn("_il2_tmp = (inports._0 * 3)", cpp)

    def test_math_module_constant_folds_not_emitted_as_raw_attribute(self):
        """math.pi (an IR.Attribute reached inside an inlined helper) used
        to come out as the invalid `_il0_math.pi` -- the alpha-renamer
        renamed the free `math` reference as if it were a local. Then,
        once that was fixed, specialize_expr's IR.Attribute case still
        never attempted constant-folding at all (unlike every sibling
        expression kind), so it emitted literal `math.pi` text instead of
        a numeric literal. Both fixed; this checks the end result."""
        cpp = _generate(_function_diagram(_math_pi_helper))
        self.assertIn("3.14159", cpp)
        self.assertNotIn("math.pi", cpp)
        self.assertNotIn("_il0_math", cpp)

    def test_self_field_access_never_folds_away(self):
        """The IR.Attribute constant-folding fix must not fold a known-
        valued self.<field> reference into a literal -- it must stay a
        real struct-field access in the emitted code (keep_fields /
        live tuning depends on it). Tested directly against
        IRSpecializer.specialize_expr(), rather than through a full
        diagram: in a real diagram, a self.<field> read is often also
        the operand of a BinaryOp that folds via its own (separate,
        pre-existing) eval_expr-based mechanism regardless of this
        guard, which would mask the guard's absence."""
        cfg = SimpleNamespace(self={"gain": (0.5, VarType(0.5))}, itypes=[])
        expr = IR.Attribute(IR.Name("self"), "gain")
        out = IRSpecializer(cfg).specialize_expr(expr)
        self.assertIsInstance(out, IR.Attribute)

    def test_np_array_noop_coercion_still_fires_after_attribute_folding(self):
        """Regression from fixing the above: folding IR.Attribute also
        caught *callables* (np.array resolves to the real function object
        via eval_expr), which defeated the np.array(x) no-op-coercion
        pattern-match in IR.Call handling (it specifically checks
        isinstance(out.func, IR.Attribute) -- a folded IR.Literal doesn't
        match). Fixed by excluding callables from the fold."""

        def outer(u):
            return np.array(u)

        cpp = _generate(_function_diagram(outer))
        self.assertNotIn("numpy", cpp.lower())

    def test_math_sqrt_is_a_working_intrinsic(self):
        """math.sqrt() is now a real, registered intrinsic (std::sqrt) --
        was unresolvable at all until math got added to name resolution,
        then correctly-but-unhelpfully refused once it did (not a
        registered intrinsic). Locks in that it actually transpiles now,
        not just fails with a better message."""
        cpp = _generate(_function_diagram(_sqrt_helper))
        self.assertIn("std::sqrt(", cpp)

    def test_unregistered_math_function_gives_actionable_error(self):
        """A math.* function with no registered intrinsic (math.gamma --
        deliberately not among the ones codegen.py registers) must still
        fail loudly and specifically, naming the actual call -- not
        silently pass through as unresolvable the way it would have
        before math got added to name resolution at all."""
        with self.assertRaisesRegex(NotImplementedError, r"math\.gamma"):
            _generate(_function_diagram(_unregistered_math_helper))

    def test_numpy_internals_refused_with_actionable_message(self):
        """np.linalg.norm has real Python source (a thin wrapper) that the
        inliner would otherwise happily recurse into, hitting genuinely
        complex shape/dtype-branching code deep inside numpy and failing
        with an unhelpful error naming some auto-generated local instead
        of the actual call site."""
        with self.assertRaisesRegex(NotImplementedError, r"numpy\.linalg\.norm"):
            _generate(_function_diagram(_norm_helper))

    def test_inline_depth_limit_is_enforced(self):
        """IRInliner.MAX_DEPTH / max_inline_depth used to be dead code --
        depth was never actually incremented across nested inline calls,
        so a runaway non-cyclic call chain would unroll without bound."""
        # depth >= max_depth must refuse to inline (return None), not
        # unroll further -- this is the bound itself, tested directly.
        result = IRInliner.inline(len, [], depth=5, max_depth=5)
        self.assertIsNone(result)

    def test_fixname_applied_to_wiring_source_side_too(self):
        """Auto-numbered block names (e.g. "constant.0") contain '.', not
        valid inside a C++ identifier -- the wiring-assignment code used
        to apply fixname() to the destination side only, leaving the raw
        dotted name on the source side. Needs two non-sink auto-named
        blocks (a sink like SCOPE is skipped before any wiring line is
        emitted for it)."""
        sim = bdsim.BDSim(animation=False)
        bd = sim.blockdiagram()
        src = bd.CONSTANT(1.0)  # auto-named, e.g. "constant.0"
        gain = bd.GAIN(2.0)  # auto-named, e.g. "gain.0"
        scope = bd.SCOPE(nin=1)
        bd.connect(src, gain)
        bd.connect(gain, scope)
        bd.compile()
        cpp = _generate(bd)
        wiring_lines = [line for line in cpp.splitlines() if "<--" in line]
        self.assertTrue(wiring_lines)
        for line in wiring_lines:
            code = line.split("//")[0]
            self.assertNotIn(src.name, code)  # raw "constant.0" (with the dot)
            self.assertNotIn(gain.name, code)  # raw "gain.0"

    def test_clip_block_codegens_and_compiles(self):
        """The CLIP block's output() does
        `out = min(self.max, max(input, self.min))` -- min/max weren't
        resolvable by name at all (silently UNKNOWN, callable(UNKNOWN) is
        False), so this call never even reached a diagnosis, let alone
        transpiled; CppEmitter failed much later with a generic
        "cannot infer C++ type" error naming no call at all. Also the
        first real exercise of a *nested* intrinsic call as another
        intrinsic's argument (IR.IntrinsicCall deliberately evaluates to
        UNKNOWN, so the outer call's own intrinsic lookup used to be
        skipped too)."""
        sim = bdsim.BDSim(animation=False)
        bd = sim.blockdiagram()
        src = bd.CONSTANT(50.0, name="src")
        clip = bd.CLIP(-40, 40, name="clip")
        scope = bd.SCOPE(nin=1)
        bd.connect(src, clip)
        bd.connect(clip, scope)
        bd.compile()
        cpp = _generate(bd)
        self.assertIn("std::min<double>", cpp)
        self.assertIn("std::max<double>", cpp)
        _assert_compiles(self, cpp)

    def test_deriv_s_state_unwrap_and_state_assignment(self):
        """Deriv_S.output() does `result = self.gain * (u[0] - x) / self.T`
        then the same isinstance(result, np.ndarray)/.ndim/.size/.item()
        scalar-unwrap idiom Integrator_S.output() uses (and already
        folded correctly) -- but here `result` is a *computed* expression,
        not a bare state read. eval_expr's BinaryOp type-propagation only
        handled the case where *both* operands were VarType, so combining
        a concrete self.field (self.gain) with the ndarray-typed state
        lost all type information, and the isinstance/.ndim/.size/.item()
        idiom reached the emitter as raw, uncompilable Python/NumPy text.

        Deriv_S.next() (`return np.array(u[0])`) separately exercises a
        second bug: once np.array()'s no-op-coercion strips down to a
        bare scalar with nothing Eigen-typed left in the expression,
        `self.state = <scalar>;` doesn't type-check against self.state's
        real (size-1 array) C++ type -- Eigen has no implicit scalar ->
        Matrix conversion. Fixed by broadcast-constructing
        (`Type::Constant(...)`) when state's real shape (from
        getstate0()) is exactly one element."""
        sim = bdsim.BDSim(animation=False)
        bd = sim.blockdiagram()
        clock = bd.clock(10, "Hz")
        src = bd.CONSTANT(1.0, name="src")
        deriv = bd.DERIV_S(clock, x0=0.0, gain=0.1, name="deriv")
        scope = bd.SCOPE(nin=1)
        bd.connect(src, deriv)
        bd.connect(deriv, scope)
        bd.compile()
        cpp = _generate(bd)
        # the isinstance/.ndim/.size/.item() idiom must have folded away
        self.assertNotIn("isinstance(", cpp)
        self.assertNotIn(".ndim", cpp)
        self.assertNotIn(".item()", cpp)
        # next()'s state write must broadcast-construct, not assign raw
        self.assertIn("::Constant(", cpp)
        _assert_compiles(self, cpp)

    def test_local_variable_shadowing_a_builtin_not_misresolved(self):
        """A local variable that happens to share a name with a Python
        builtin (`input`, matching FUNCTIONBLOCK-style code's own common
        `input = inputs[0]` idiom -- e.g. CLIP's real output() body) must
        resolve as the local, not silently fall through to the actual
        builtin function once bare-builtin resolution was added (for
        min/max/abs/math.*) -- real Python scoping shadows it too, and
        conflating the two silently corrupted the call's arguments rather
        than failing loudly."""

        def outer(u):
            input = u  # noqa: A001 -- deliberately shadows the builtin
            return input + 1.0

        cpp = _generate(_function_diagram(outer))
        # must read the real local, not e.g. stringify the builtin
        self.assertIn("inports._0", cpp)
        self.assertNotIn("built-in", cpp)

    def test_io_block_self_struct_excludes_bookkeeping_and_sim_fields(self):
        """An IOBlockMixin block's self struct must contain exactly the
        fields the block class registered via add_param() (its genuine,
        user-facing configuration -- channel/device/freq) -- not every
        surviving block.__dict__ attribute. Without this, generic Block
        bookkeeping (nin/nout) and simulator-only fields (sim_value(s),
        never meant for a hand-written C++ body) leaked into the struct
        as dead fields with no meaning there. Also locks in that an
        unset str/float parameter (device/freq) renders as a real,
        usable std::string/float default -- not std::nullptr_t, which a
        Python None default would produce and which can never hold a
        real value afterwards."""
        sim = bdsim.BDSim(animation=False)
        bd = sim.blockdiagram()
        encoder = bd.DEVICEIN(name="encoder")
        pwm = bd.PWMOUT(channel=0, freq=1000.0, name="pwm")
        direction = bd.DIGITALOUT(channel=1, name="direction")
        bd.connect(encoder, pwm)
        bd.connect(encoder, direction)
        bd.compile()
        cpp = _generate(bd)
        self.assertNotIn("nin", cpp)
        self.assertNotIn("nout", cpp)
        self.assertNotIn("sim_value", cpp)
        self.assertNotIn("nullptr_t", cpp)
        self.assertIn("std::string device = \"\";", cpp)
        self.assertIn("float freq = 1000.0;", cpp)
        _assert_compiles(self, cpp)


# ---------------------------------------------------------------------------
# 3. "codegen succeeds" tests against known-good diagrams
# ---------------------------------------------------------------------------


class KnownGoodDiagramTests(unittest.TestCase):
    def test_original_demo_diagram(self):
        """demand(STEP) -> sum -> gain -> plant(LTI_SISO) -> scope, with
        feedback -- the diagram codegen.py's own __main__ has exercised
        throughout development."""
        sim = bdsim.BDSim(animation=False)
        bd = sim.blockdiagram()
        demand = bd.STEP(T=1, name="demand")
        summ = bd.SUM("+-")
        gain = bd.GAIN(10)
        plant = bd.LTI_SISO(0.5, [2, 1], name="plant")
        scope = bd.SCOPE(styles=["k", "r--"], loc="lower right")
        bd.connect(demand, summ[0], scope[1])
        bd.connect(plant, summ[1])
        bd.connect(summ, gain)
        bd.connect(gain, plant)
        bd.connect(plant, scope[0])
        bd.compile()
        cpp = _generate(bd)
        self.assertIn("bdsim_init", cpp)
        self.assertIn("bdsim_tick", cpp)

    def test_standalone_integrator_s(self):
        cpp = _generate(_standalone_integrator_s_diagram())
        self.assertIn("integ_next", cpp)

    def test_motor_control_example_runs_end_to_end(self):
        """Runs the canonical examples/codegen/motor_control.py example
        directly -- it isn't covered by tests/test_examples_smoke.py
        (which only globs top-level examples/*.py and is itself skipped;
        see bdsim#91), so this is the only real-run coverage it gets."""
        env = os.environ.copy()
        env["MPLBACKEND"] = "Agg"
        result = subprocess.run(
            [sys.executable, str(EXAMPLES_CODEGEN / "motor_control.py")],
            cwd=str(EXAMPLES_CODEGEN),
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"motor_control.py failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )


# ---------------------------------------------------------------------------
# 4. Compile-verification / numeric cross-check
# ---------------------------------------------------------------------------


class CompileVerificationTests(unittest.TestCase):
    @unittest.skipUnless(CAN_COMPILE, SKIP_COMPILE_REASON)
    def test_standalone_integrator_s_compiles_with_clang(self):
        # Deliberately not the "original demo" diagram from
        # KnownGoodDiagramTests -- it includes a continuous LTI_SISO
        # block, out of scope for this codegen effort, whose generated
        # C++ does not actually compile (undefined `matmul`, Python-only
        # `.size`/`.item()` usage on an Eigen type -- see bdsim#93). Only
        # sampled/clocked diagrams are expected to produce compilable
        # code; this is a minimal one.
        bd = _standalone_integrator_s_diagram()
        with tempfile.TemporaryDirectory() as d:
            cpp_path = os.path.join(d, "codegen.cpp")
            Codegen(output_path=cpp_path).generate(bd)
            obj_path = os.path.join(d, "codegen.o")
            result = subprocess.run(
                [
                    CLANGXX,
                    "-std=c++17",
                    f"-I{EIGEN_INCLUDE}",
                    "-c",
                    cpp_path,
                    "-o",
                    obj_path,
                ],
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(CAN_COMPILE, SKIP_COMPILE_REASON)
    def test_motor_control_numeric_cross_check(self):
        """Runs the real numeric cross-check + compile-verification script
        (Python ground truth vs. compiled C++ over the identical time
        sequence) and asserts it reports PASS."""
        env = os.environ.copy()
        env["MPLBACKEND"] = "Agg"
        result = subprocess.run(
            [sys.executable, str(EXAMPLES_CODEGEN / "verify_codegen.py")],
            cwd=str(EXAMPLES_CODEGEN),
            env=env,
            text=True,
            capture_output=True,
            timeout=120,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"verify_codegen.py failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("PASS", result.stdout)


# ---------------------------------------------------------------------------
# 5. IR coverage sanity check
# ---------------------------------------------------------------------------


class IRCoverageTests(unittest.TestCase):
    def test_no_raw_ir_hit_across_known_good_diagrams(self):
        """RawStmt/RawExpr hits mean the frontend fell through to unlowered
        raw Python source somewhere -- a real frontend-coverage gap. None
        of the known-good diagrams should ever hit it (a raw hit would
        already have failed at emit time before generation could succeed,
        but this makes the invariant explicit and self-checking)."""
        reset_ir_coverage()

        sim = bdsim.BDSim(animation=False)
        bd = sim.blockdiagram()
        demand = bd.STEP(T=1, name="demand")
        summ = bd.SUM("+-")
        gain = bd.GAIN(10)
        plant = bd.LTI_SISO(0.5, [2, 1], name="plant")
        scope = bd.SCOPE(styles=["k", "r--"], loc="lower right")
        bd.connect(demand, summ[0], scope[1])
        bd.connect(plant, summ[1])
        bd.connect(summ, gain)
        bd.connect(gain, plant)
        bd.connect(plant, scope[0])
        bd.compile()
        _generate(bd)

        _generate(_standalone_integrator_s_diagram())

        _report, raw_hit = ir_coverage_report()
        self.assertFalse(raw_hit)


if __name__ == "__main__":
    unittest.main()
