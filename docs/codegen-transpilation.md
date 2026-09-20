# bdsim.codegen: capabilities and limitations of the C++ transpiler

**Status: draft, working document.** Tracks the transpiler as it exists
on the `feat/codegen` branch, which is still under active development
and unreleased. Nothing here is a stable API guarantee yet. This may
move to the bdsim wiki once the design settles, and/or be converted to
reST for the Sphinx docs — for now it's the single source of truth for
"what does `bdsim.codegen` actually support."

I/O blocks (reading/writing real pins, encoders, PWM outputs, ...) are
deliberately **not** covered here yet — that part of the design hasn't
converged. This document covers pure-computation transpilation only.

## What this is

`bdsim.codegen` takes a compiled `BlockDiagram` and generates a single
standalone C++ file implementing the same behaviour, intended to run on
a microcontroller with no Python, no host machine, and no `bdsim`
runtime attached. The target is small diagrams (roughly a dozen blocks)
running on a single hardware timer tick — think a PID loop on an
Arduino-class board, not a general-purpose simulation replay.

It is **not** a general Python-to-C++ compiler. It transpiles exactly
the subset of Python that bdsim's own block library and simple
user-supplied helper functions actually use, and it is deliberately
narrow about that. Anything outside the supported subset fails loudly,
at generation time, naming the specific construct or call that couldn't
be handled — never a silent guess, and never C++ that compiles but does
the wrong thing.

## Scope (v1)

- **Sampled/clocked blocks only.** A block runs off a discrete clock
  tick; there is no continuous-time integration. `PID_S`,
  `Integrator_S`, `WAVEFORM`, `FUNCTION`, `GAIN`, `SUM`, `CLIP` and
  friends are all fair game.
- **Continuous-time blocks are out of scope, and using one produces
  C++ that does not compile.** The specializer will happily lower and
  fold a block like `LTI_SISO`, but the emitter has no real
  implementation for matrix multiply (`@` emits a call to a `matmul()`
  that doesn't exist) or NumPy `.size`/`.item()` against an Eigen type.
  Tracked as [bdsim#93](https://github.com/petercorke/bdsim/issues/93);
  the fix, when this becomes in-scope, is either to make codegen refuse
  continuous blocks loudly (cheap) or to actually implement continuous
  support (a real scope expansion).
- **Single clock.** The generated program is one polling loop
  (`bdsim_tick()`), called once per tick. Multiple independent clock
  rates aren't generalized yet.
- **A dozen blocks, not a hundred.** No attempt at scaling; the
  generated code is meant to be read and hand-verified.

## The pipeline

Each block's `output()` (and, for a stateful block, `next()`) Python
source is parsed with `ast`, lowered to a small internal IR, constant-
folded/specialized against what's actually known about the block's
inputs and `self` fields, and rendered to C++. A `FUNCTION` block's
user-supplied callable is inlined directly into its `output()`, since
`Function.output()`'s own Python source (with its `*args`/`**kwargs`
and `try`/`except`) isn't itself transpilable.

## Supported Python subset

**Statements:** assignment (`x = ...`), annotated declaration
(`x: float = ...`), `if`/`else` (lazily — only the branch a folded
condition proves reachable is ever visited by later passes, so a dead
branch containing something otherwise-unsupported is fine), `return`,
`raise`, bare expression statements.

**Loops:** `for` is lowered but only meaningfully consumed by one
block-specific special case (`SUM`'s own
`for i, input in enumerate(inputs): ...` shape) — there is no general
for-loop support. `while` is not supported at all. Both tracked as
[bdsim#92](https://github.com/petercorke/bdsim/issues/92).

**Not supported at all:** `try`/`except`, `with`, class/nested-function
definitions, `async`, the walrus operator, `match`.

**Expressions:** arithmetic/comparison/boolean operators, subscripting,
attribute access, literals, list/tuple construction, the ternary
(`a if cond else b`). List/dict comprehensions exist as IR node types
but aren't meaningfully supported beyond limited folding.

### Calls

A call is resolved three ways, tried in order:

1. **A registered intrinsic** — a known Python callable with a
   hand-written C++ implementation. See the table below.
2. **Inlining** — for a plain Python function/lambda whose source
   `inspect.getsource()` can read, and which isn't from a blocked
   package (see "numpy/scipy internals" below), up to
   `max_inline_depth` levels of nested (non-recursive) calls. This is
   how a `FUNCTION` block's own callable, and any ordinary helper
   function it calls, get transpiled — no special-casing needed beyond
   "can we read the source."
3. **A few structurally-recognized shapes** — `len`/`isinstance`/
   `enumerate`/`zip`, `list(x)`/`np.array(x)` as no-op coercions
   (Eigen's own representation is already array-like), and `x.item()`
   on an ndarray-typed value (unwraps a size-1 Eigen type to a scalar).

Anything that resolves to a real Python callable but matches none of
the above fails loudly, naming the call
(`module.qualname`) and explaining why: not registered, source
unavailable (e.g. a compiled/C-extension function), or nesting too deep.

### Registered intrinsics (as of this writing)

| Python | C++ |
|---|---|
| `min(a, b)`, `max(a, b)` | `std::min<double>`/`std::max<double>` (both operands cast to `double` — avoids template-deduction failure on an int/float mix, e.g. an integer clip limit against a float signal) |
| `abs(x)` | `std::abs(x)` |
| `math.sqrt/sin/cos/tan/exp/log` | `std::sqrt` etc. |
| `math.atan2(y, x)`, `math.pow(x, y)` | `std::atan2`, `std::pow` |
| `math.floor(x)`, `math.ceil(x)` | `static_cast<int32_t>(std::floor(x))` / `std::ceil` — Python's `math.floor`/`ceil` return `int`, C++'s return a float type |
| `math.pi`, `math.e`, ... (bare attribute access, not a call) | folds directly to a numeric literal |
| `spatialmath.base.skew/skewa/vex/r2t/t2r/norm/unit/cross` | hand-written Eigen helpers |
| `x.item()` on an ndarray-typed value | direct coefficient access |

This list grows as real diagrams hit gaps — `min`/`max`/`abs`/`math.*`
were all added because a real block (`CLIP`) or a real toolbox helper
needed them, not speculatively. If you hit an unregistered call, that's
the pipeline telling you where to add one, not a dead end.

**Not covered, no current plan:** `round`, `sum`, `sorted`, `divmod`,
and most of the rest of `math`/`builtins` beyond what's in the table.
Add on demand.

### `numpy`/`scipy` internals — deliberately refused, not inlined

`np.linalg.norm` and similar functions often *do* have real Python
source the inliner could technically read — but that source is usually
deep, shape/dtype-branching implementation code that was never going to
specialize cleanly. Rather than let the inliner recurse into it and fail
with a confusing error naming some auto-generated internal, codegen
refuses to even attempt inlining anything from `numpy`/`scipy`, and
fails at the actual call site instead. If a NumPy/SciPy function is
genuinely needed, it belongs in the intrinsic table with a hand-written
C++ implementation, not inlined.

## Type mapping

| Python value | C++ type |
|---|---|
| bare `int` | `int32_t` (configurable: `Codegen(default_int_type=...)`) |
| bare `float` | `float` — 32-bit, **not** `double`, even though Python floats are 64-bit (configurable: `default_float_type`) |
| `np.float64(x)`, or an `ndarray` with an explicit `dtype` | its own real width always — `np.float64` reliably becomes a C++ `double`, `np.uint16` a `uint16_t`, etc., regardless of the defaults above |
| `ndarray`, 1 or 2 dimensions | fixed-size `Eigen::Matrix<...>` |
| `ndarray`, 0 dimensions (a genuine NumPy scalar) | a plain C++ scalar, no Eigen wrapper |
| `bool` | `bool` |
| `str` | `std::string` |
| `None` | `std::nullptr_t` |

A `self.<field>` reference (a block's own stored attribute, e.g. a
`PID_S`'s gain) is **never** folded into a literal in the emitted code,
even when its value is known at generation time — it stays a real,
mutable struct field. This is what lets `keep_fields` expose a field for
live tuning later; folding it away would silently defeat that.

## Error philosophy

Every unsupported construct raises `NotImplementedError` at generation
time, naming what it hit — never a silent pass-through that produces
C++ which either fails to compile with a confusing error, or (worse)
compiles and runs with the wrong behaviour. If you hit one of these,
read it as "the pipeline correctly doesn't understand this yet," not as
a bug report waiting to happen at the C++ compile stage.

Two structural gaps this closes, both real regressions caught in
practice, worth knowing about if you're debugging a new one:

- A local variable is always resolved before considering it a possible
  reference to a builtin/module function — real Python scoping rules,
  respected on purpose. A block's own `input = inputs[0]` (a genuine,
  common idiom) must not be misresolved to the builtin `input()` just
  because the names collide.
- A nested intrinsic call used as another intrinsic's own argument (e.g.
  `min(a, max(b, c))`) is handled — an `IntrinsicCall` node deliberately
  evaluates to "unknown value, known C++ form" for further folding
  purposes, so the outer call's own intrinsic match doesn't get starved
  by that.

## Known limitations (current, not exhaustive)

- No general `for`/`while` loop support ([bdsim#92](https://github.com/petercorke/bdsim/issues/92)).
- Continuous-time blocks don't produce compilable C++ ([bdsim#93](https://github.com/petercorke/bdsim/issues/93)).
- Single clock only — no multi-clock scheduling yet.
- No recursion (guarded and rejected, not silently broken).
- `max_inline_depth` (default 20) bounds how deep a legitimate, non-
  recursive chain of helper calls can nest before codegen gives up.
- No `try`/`except`, `with`, classes, `async`, `match`, walrus.
- Comprehensions aren't meaningfully folded.
- `builtins`/`math` coverage is deliberately reactive (added when a
  real diagram needs it), not exhaustive — see the intrinsic table.

## How to extend

Adding a new intrinsic is the normal way to close a coverage gap:
register `(module, qualname, sig)` → `(result_vt_fn, intrinsic_name)` in
`_INTRINSICS` (`sig=()` is a wildcard, matching regardless of argument
types — appropriate for something like `min`/`max` that doesn't need
type-dependent dispatch), then add the C++ rendering to
`CppEmitter.INTRINSIC_IMPLS[intrinsic_name]`. See `codegen.py`'s
existing registrations (`spatialmath.base`, `builtins`, `math`) for the
pattern.

## See also

- `src/bdsim/codegen.py`'s own module docstring — the terser,
  code-adjacent version of the "supported subset" section above; keep
  the two in sync if one changes.
- `claude-notes/codegen-embedded-plan.md` — the full design history,
  decisions, and bug write-ups behind this transpiler (not tracked in
  git; local working notes).
