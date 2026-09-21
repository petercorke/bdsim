r"""Generate standalone, embedded-target C++ from a compiled bdsim
:class:`~bdsim.blockdiagram.BlockDiagram`.

Pipeline: each block's ``output()``/``next()`` Python source is parsed
(:mod:`ast`), lowered to a small internal IR (:class:`IR`) by
:class:`MethodFrontend`, constant-folded/specialized by
:class:`IRSpecializer`, and rendered to C++ by :class:`CppEmitter`.
:class:`Codegen` orchestrates the whole diagram. See
``claude-notes/codegen-embedded-plan.md`` for the design history and
rationale; this docstring is the reference for *what's actually
supported* -- deliberately narrower than Python itself, and narrower
than what a fully general Python-to-C++ transpiler would need, because
the target is bdsim block bodies and simple toolbox helpers, not
arbitrary code.

Fails loudly (``NotImplementedError``) on anything outside this
subset, naming the construct or call that couldn't be handled, rather
than silently emitting C++ that won't compile or (worse) compiles but
does the wrong thing. If you hit one of these, that's the pipeline
correctly telling you it doesn't understand your code yet -- not a bug
report waiting to happen at the C++ compile stage.

**Supported statements**: assignment (``x = ...``), annotated
declaration (``x: float = ...``), ``if``/``else`` (only the branch a
constant-folded condition proves reachable is ever visited by later
passes -- a dead branch containing something otherwise-unsupported is
fine), ``return``, ``raise``, bare expression statements. ``for`` is
supported for exactly one shape -- ``for i, x in enumerate(inputs):
...`` -- unrolled into ``nin`` copies of the loop body (the bound is
always statically known), substituting ``i``/``x`` per copy and leaving
every other name (a cross-iteration accumulator, e.g. ``SUM``'s
``sum``/``PROD``'s ``prod``) genuinely shared, not renamed (see
:func:`IRSpecializer._unroll_enumerate_inputs_for`). This is the only
``for`` shape bdsim's own block library actually uses; any other shape,
and ``while``, ``try``/``except``, ``with``, class/nested-function
definitions, ``async``, walrus, and ``match``, are **not** supported at
all (tracked: bdsim issue #92).

**Supported expressions**: arithmetic/comparison/boolean operators,
subscripting, attribute access, literals, list/tuple construction, the
ternary (``a if cond else b``). Calls are supported three ways, tried in
order: (1) a registered intrinsic (``_INTRINSICS`` -- currently
``spatialmath.base`` functions like ``skew``/``vex``/``cross``, rendered
via a hand-written C++ implementation in each :class:`Emitter`
subclass's ``INTRINSIC_IMPLS``); (2) inlining, for a plain Python
function/lambda whose source :func:`inspect.getsource` can read, not
from a blocked package (``_NO_INLINE_PACKAGES`` -- currently
``numpy``/``scipy``: their internals sometimes *do* have real Python
source, but are too complex to reliably specialize, so codegen refuses
to even try and fails at the actual call site instead of somewhere deep
inside NumPy's own implementation), within ``max_inline_depth`` levels
of nesting; (3) a small set of specially-recognized builtins
(``len``/``isinstance``/``enumerate``/``zip``/``abs``, ``list(x)`` and
``np.array(x)`` as no-op coercions, ``x.item()`` on an ndarray-typed
value). Comprehensions (``ListComp``/``DictComp``) are defined as IR
node types but not meaningfully supported beyond limited folding.

**Type mapping**: a bare Python ``int`` maps to ``int32_t``, a bare
``float`` to C++ ``float`` (32-bit -- not ``double``, even though Python
floats are 64-bit) by default -- both configurable per :class:`Codegen`
instance (``default_int_type``/``default_float_type``). A genuinely
NumPy-typed value (``np.uint16(5)``, or an ``ndarray`` with an explicit
``dtype``) always keeps its own width regardless of that default --
``np.float64(x)`` reliably gets a C++ ``double``, for instance. An
``ndarray`` with 1 or 2 dimensions maps to a fixed-size
``Eigen::Matrix``; 0 dimensions (a genuine NumPy scalar) maps to a plain
C++ scalar, no Eigen wrapper.
"""

import ast
import builtins
import datetime
import inspect
import os
import sys
import json
import math
import textwrap
from dataclasses import dataclass, field
from dataclasses import fields as dataclass_fields
from dataclasses import replace as dataclass_replace
from typing import Any, Iterable
import numpy as np

import bdsim
from bdsim.components import IOBlockMixin

sim = bdsim.BDSim()

UNKNOWN = object()

# Top-level packages IRSpecializer never attempts to inline into, even when
# Python source happens to be available for a specific function (e.g.
# np.linalg.norm is a thin wrapper, not a compiled builtin) -- their
# internals are too complex to reliably specialize and produce useless
# errors buried deep inside auto-generated inlined code instead of at the
# actual call site. Register a specific function in _INTRINSICS instead.
# Deliberately narrow: ordinary third-party/toolbox modules (spatialmath,
# RTB, MVTB, a user's own code) are exactly what the inliner exists for.
_NO_INLINE_PACKAGES = frozenset({"numpy", "scipy"})


class VarType:
    """Holds type information about a variable or value."""

    dtype: str
    etype: str | None = None
    dims: int | tuple[int, int] | None = None

    def __init__(self, v):
        # Checked before str/bool/float/int: NumPy scalar types (np.uint16,
        # np.float32, ...) carry an explicit width/precision the plain
        # Python buckets below can't express -- and some of them (notably
        # np.float64) are themselves subclasses of the Python builtin, so
        # this must come first or explicit NumPy typing gets silently
        # discarded (e.g. np.float64(x) would otherwise match `float`
        # below and lose its width to the default float mapping).
        # dims=() (0-d) distinguishes a genuine scalar from an ndarray.
        if isinstance(v, np.generic):
            self.dtype = "ndarray"
            self.etype = str(v.dtype)
            self.dims = ()
        elif isinstance(v, str):
            self.dtype = "str"
        elif isinstance(v, bool):
            self.dtype = "bool"
        elif isinstance(v, float):
            self.dtype = "float"
        elif isinstance(v, int):
            self.dtype = "int"
        elif isinstance(v, tuple) or isinstance(v, list):
            self.dtype = "list"
            self.dims = len(v)
        elif isinstance(v, np.ndarray):
            self.dtype = "ndarray"
            self.etype = str(v.dtype)
            self.dims = v.shape
        elif isinstance(v, type(None)):
            self.dtype = "None"
        else:
            raise ValueError(f"unsupported VarType: {v}")

    @classmethod
    def _make(cls, dtype: str, etype: str | None = None, dims=None) -> "VarType":
        obj = object.__new__(cls)
        obj.dtype = dtype
        obj.etype = etype
        obj.dims = dims
        return obj

    def __repr__(self):
        s = f"VarType({self.dtype}"
        if self.dims is not None:
            s += f", dims={self.dims}"
        s += ")"
        return s


class IR:
    """A simple class acting as a namespace for IR node definitions."""

    @dataclass
    class Node:
        pass

    @dataclass
    class Expr(Node):
        pass

    @dataclass
    class Stmt(Node):
        pass

    @dataclass
    class Load(Node):
        pass

    @dataclass
    class Store(Node):
        pass

    @dataclass
    class Arg(Node):
        name: str
        annotation: str | None = None

    @dataclass
    class Arguments(Node):
        args: list["IR.Arg"]

    @dataclass
    class Assert(Stmt):
        test: "IR.Expr"
        msg: "IR.Expr | None" = None

    @dataclass
    class Assign(Stmt):
        target: "IR.Expr"
        value: "IR.Expr"

    @dataclass
    class Attribute(Expr):
        value: "IR.Expr"
        attr: str

    @dataclass
    class BinaryOp(Expr):
        left: "IR.Expr"
        op: str
        right: "IR.Expr"

    @dataclass
    class BoolOp(Expr):
        op: str
        values: list["IR.Expr"]

    @dataclass
    class Call(Expr):
        func: "IR.Expr"
        args: list["IR.Expr"]
        keywords: list["IR.Keyword"] = field(default_factory=list)

    @dataclass
    class Compare(Expr):
        left: "IR.Expr"
        op: str
        right: "IR.Expr"

    @dataclass
    class Comprehension(Node):
        target: "IR.Expr"
        iterable: "IR.Expr"
        ifs: list["IR.Expr"]

    @dataclass
    class Declare(Stmt):
        target: "IR.Expr"
        annotation: str | None
        value: "IR.Expr | None" = None

    @dataclass
    class DictComp(Expr):
        key: "IR.Expr"
        value: "IR.Expr"
        generators: list["IR.Comprehension"]

    @dataclass
    class ExceptHandler(Node):
        exc_type: "IR.Expr | None"
        name: str | None
        body: list["IR.Stmt"]

    @dataclass
    class ExprStmt(Stmt):
        value: "IR.Expr"

    @dataclass
    class For(Stmt):
        target: "IR.Expr"
        iterable: "IR.Expr"
        body: list["IR.Stmt"]
        orelse: list["IR.Stmt"] = field(default_factory=list)

    @dataclass
    class Function(Node):
        name: str
        args: list[str]
        body: list["IR.Stmt"]

    @dataclass
    class If(Stmt):
        condition: "IR.Expr"
        body: list["IR.Stmt"]
        orelse: list["IR.Stmt"] = field(default_factory=list)

    @dataclass
    class IfExpr(Expr):
        body: "IR.Expr"
        condition: "IR.Expr"
        orelse: "IR.Expr"

    @dataclass
    class Keyword(Expr):
        arg: str | None
        value: "IR.Expr"

    @dataclass
    class List(Expr):
        values: list["IR.Expr"]

    @dataclass
    class ListComp(Expr):
        elt: "IR.Expr"
        generators: list["IR.Comprehension"]

    @dataclass
    class Literal(Expr):
        value: Any

    @dataclass
    class Module(Node):
        body: list["IR.Node"]

    @dataclass
    class Name(Expr):
        name: str
        ctx: "IR.Node | None" = None

    @dataclass
    class Raise(Stmt):
        value: "IR.Expr"

    @dataclass
    class RawExpr(Expr):
        source: str

    @dataclass
    class RawStmt(Stmt):
        source: str

    @dataclass
    class Return(Stmt):
        value: "IR.Expr"

    @dataclass
    class IntrinsicCall(Expr):
        """A call resolved to a named, language-neutral intrinsic.

        ``name`` is a dot-separated identifier like ``"bdsim.skew3"`` that
        each :class:`Emitter` subclass looks up in its own
        ``INTRINSIC_IMPLS`` table to produce target-language code.
        """

        name: str
        args: "list[IR.Expr]"
        result_vt: "VarType | None" = None

    @dataclass
    class Starred(Expr):
        value: "IR.Expr"

    @dataclass
    class Subscript(Expr):
        value: "IR.Expr"
        index: "IR.Expr"
        ctx: "IR.Node | None" = None

    @dataclass
    class Try(Stmt):
        body: list["IR.Stmt"]
        handlers: list["IR.ExceptHandler"] = field(default_factory=list)
        orelse: list["IR.Stmt"] = field(default_factory=list)
        finalbody: list["IR.Stmt"] = field(default_factory=list)

    @dataclass
    class Tuple(Expr):
        values: list["IR.Expr"]

    @dataclass
    class UnaryOp(Expr):
        op: str
        operand: "IR.Expr"


# ---------------------------------------------------------------------------
# IR coverage tracking
# ---------------------------------------------------------------------------
_ALL_IR_TYPES: set[str] = {
    name
    for name, obj in vars(IR).items()
    if isinstance(obj, type) and issubclass(obj, IR.Node) and obj is not IR.Node
}

_ir_coverage: dict[str, set[str]] = {
    "spec_stmt": set(),
    "spec_expr": set(),
    "emit_stmt": set(),
    "emit_expr": set(),
}


class IRPrettyPrinter:
    def __init__(self) -> None:
        self.indent = 0

    def _prefix(self) -> str:
        return "    " * self.indent

    def format(self, node: IR.Node) -> str:
        return self.visit(node)

    def generic_visit(self, node: IR.Node) -> str:
        return repr(node)

    def visit(self, node: IR.Node) -> str:
        method = getattr(self, f"visit_{type(node).__name__}", self.generic_visit)
        return method(node)

    def visit_Assign(self, node: IR.Assign) -> str:
        return f"{self.visit(node.target)} = {self.visit(node.value)}"

    def visit_Attribute(self, node: IR.Attribute) -> str:
        return f"{self.visit(node.value)}.{node.attr}"

    def visit_BinaryOp(self, node: IR.BinaryOp) -> str:
        return f"({self.visit(node.left)} {node.op} {self.visit(node.right)})"

    def visit_BoolOp(self, node: IR.BoolOp) -> str:
        joiner = f" {node.op} "
        return f"({joiner.join(self.visit(value) for value in node.values)})"

    def visit_Call(self, node: IR.Call) -> str:
        return f"{self.visit(node.func)}({', '.join(self.visit(arg) for arg in node.args)})"

    def visit_Compare(self, node: IR.Compare) -> str:
        return f"({self.visit(node.left)} {node.op} {self.visit(node.right)})"

    def visit_Comprehension(self, node: IR.Comprehension) -> str:
        suffix = (
            ""
            if not node.ifs
            else " " + " ".join(f"if {self.visit(cond)}" for cond in node.ifs)
        )
        return f"for {self.visit(node.target)} in {self.visit(node.iterable)}{suffix}"

    def visit_Declare(self, node: IR.Declare) -> str:
        base = self.visit(node.target)
        if node.annotation is not None:
            base = f"declare {base}: {node.annotation}"
        if node.value is not None:
            base += f" = {self.visit(node.value)}"
        return base

    def visit_ExprStmt(self, node: IR.ExprStmt) -> str:
        return self.visit(node.value)

    def visit_For(self, node: IR.For) -> str:
        lines = [f"for {self.visit(node.target)} in {self.visit(node.iterable)}:"]
        self.indent += 1
        for stmt in node.body:
            lines.append(self._prefix() + self.visit(stmt))
        self.indent -= 1
        if node.orelse:
            lines.append(self._prefix() + "else:")
            self.indent += 1
            for stmt in node.orelse:
                lines.append(self._prefix() + self.visit(stmt))
            self.indent -= 1
        return "\n".join(lines)

    def visit_Function(self, node: IR.Function) -> str:
        lines = [f"function {node.name}({', '.join(node.args)})"]
        self.indent += 1
        for stmt in node.body:
            lines.append(self._prefix() + self.visit(stmt))
        self.indent -= 1
        return "\n".join(lines)

    def visit_If(self, node: IR.If) -> str:
        lines = [f"if {self.visit(node.condition)}:"]
        self.indent += 1
        for stmt in node.body:
            lines.append(self._prefix() + self.visit(stmt))
        self.indent -= 1
        if node.orelse:
            lines.append(self._prefix() + "else:")
            self.indent += 1
            for stmt in node.orelse:
                lines.append(self._prefix() + self.visit(stmt))
            self.indent -= 1
        return "\n".join(lines)

    def visit_List(self, node: IR.List) -> str:
        return f"[{', '.join(self.visit(v) for v in node.values)}]"

    def visit_ListComp(self, node: IR.ListComp) -> str:
        generators = " ".join(self.visit(generator) for generator in node.generators)
        return f"[{self.visit(node.elt)} {generators}]"

    def visit_Literal(self, node: IR.Literal) -> str:
        return repr(node.value)

    def visit_Name(self, node: IR.Name) -> str:
        return node.name

    def visit_RawExpr(self, node: IR.RawExpr) -> str:
        return f"raw_expr({node.source})"

    def visit_IntrinsicCall(self, node: IR.IntrinsicCall) -> str:
        args = ", ".join(self.visit(a) for a in node.args)
        return f"intrinsic:{node.name}({args})"

    def visit_RawStmt(self, node: IR.RawStmt) -> str:
        return f"raw_stmt({node.source})"

    def visit_Raise(self, node: IR.Raise) -> str:
        return f"raise {self.visit(node.value)}"

    def visit_Return(self, node: IR.Return) -> str:
        return f"return {self.visit(node.value)}"

    def visit_Subscript(self, node: IR.Subscript) -> str:
        return f"{self.visit(node.value)}[{self.visit(node.index)}]"

    def visit_Tuple(self, node: IR.Tuple) -> str:
        return f"({', '.join(self.visit(v) for v in node.values)})"

    def visit_UnaryOp(self, node: IR.UnaryOp) -> str:
        return f"({node.op}{self.visit(node.operand)})"


class MethodFrontend(ast.NodeVisitor):
    """Lower a Python method AST into a structured, inspectable IR."""

    def __init__(self, symbol_table: dict[str, str]) -> None:
        self.symbol_table = symbol_table

    @staticmethod
    def ast_source(node: ast.AST) -> str:
        return ast.unparse(node)

    def generic_visit(self, node: ast.AST):
        if isinstance(node, ast.expr):
            return IR.RawExpr(self.ast_source(node))
        if isinstance(node, ast.stmt):
            return IR.RawStmt(self.ast_source(node))
        return super().generic_visit(node)

    # def lower_block(self, body: Iterable[ast.stmt]) -> list[IR.Stmt]:
    #     return [self.visit(stmt) for stmt in body]

    # def lower_method(self, tree) -> IR.Function:

    #     function = tree.body[0]
    #     assert isinstance(function, ast.FunctionDef)
    #     return self.visit(function)

    def lower_method(self, method) -> IR.Function:
        source = textwrap.dedent(inspect.getsource(method))
        tree = ast.parse(source)
        function = tree.body[0]
        assert isinstance(function, ast.FunctionDef)
        return self.visit(function)

    def lower_block(self, body: Iterable[ast.stmt]) -> list[IR.Stmt]:
        return [self.visit(stmt) for stmt in body]

    def visit_AnnAssign(self, node: ast.AnnAssign) -> IR.Declare:
        value = self.visit(node.value) if node.value is not None else None
        return IR.Declare(
            target=self.visit(node.target),
            annotation=self.ast_source(node.annotation),
            value=value,
        )

    def visit_Assign(self, node: ast.Assign) -> IR.Assign:
        return IR.Assign(
            target=self.visit(node.targets[0]), value=self.visit(node.value)
        )

    def visit_Attribute(self, node: ast.Attribute) -> IR.Expr:
        if isinstance(node.value, ast.Name) and node.value.id == "self":
            return IR.Attribute(IR.Name("self"), node.attr)
        return IR.Attribute(self.visit(node.value), node.attr)

    def visit_BinOp(self, node: ast.BinOp) -> IR.Expr:
        op_map = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.MatMult: "@",
            ast.Mod: "%",
        }
        op = op_map.get(type(node.op), self.ast_source(node.op))
        return IR.BinaryOp(
            left=self.visit(node.left), op=op, right=self.visit(node.right)
        )

    def visit_BoolOp(self, node: ast.BoolOp) -> IR.Expr:
        op_map = {
            ast.And: "and",
            ast.Or: "or",
        }
        op = op_map.get(type(node.op), self.ast_source(node.op))
        return IR.BoolOp(op=op, values=[self.visit(value) for value in node.values])

    def visit_Call(self, node: ast.Call) -> IR.Call:
        return IR.Call(
            func=self.visit(node.func), args=[self.visit(arg) for arg in node.args]
        )

    def visit_IfExp(self, node: ast.IfExp) -> IR.IfExpr:
        return IR.IfExpr(
            body=self.visit(node.body),
            condition=self.visit(node.test),
            orelse=self.visit(node.orelse),
        )

    def visit_Compare(self, node: ast.Compare) -> IR.Expr:
        if len(node.ops) != 1 or len(node.comparators) != 1:
            return IR.RawExpr(self.ast_source(node))
        op_map = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Gt: ">",
            ast.GtE: ">=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.In: "in",
            ast.NotIn: "not in",
            ast.Is: "is",
            ast.IsNot: "is not",
        }
        op = op_map.get(type(node.ops[0]), self.ast_source(node.ops[0]))
        return IR.Compare(
            left=self.visit(node.left),
            op=op,
            right=self.visit(node.comparators[0]),
        )

    def visit_Constant(self, node: ast.Constant) -> IR.Literal:
        return IR.Literal(node.value)

    def visit_Expr(self, node: ast.Expr) -> IR.ExprStmt:
        return IR.ExprStmt(value=self.visit(node.value))

    def visit_For(self, node: ast.For) -> IR.For:
        return IR.For(
            target=self.visit(node.target),
            iterable=self.visit(node.iter),
            body=self.lower_block(node.body),
            orelse=self.lower_block(node.orelse),
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> IR.Function:
        args = [arg.arg for arg in node.args.args]
        return IR.Function(name=node.name, args=args, body=self.lower_block(node.body))

    def visit_If(self, node: ast.If) -> IR.If:
        return IR.If(
            condition=self.visit(node.test),
            body=self.lower_block(node.body),
            orelse=self.lower_block(node.orelse),
        )

    def visit_List(self, node: ast.List) -> IR.List:
        return IR.List(values=[self.visit(elt) for elt in node.elts])

    def visit_ListComp(self, node: ast.ListComp) -> IR.ListComp:
        return IR.ListComp(
            elt=self.visit(node.elt),
            generators=[self.visit(gen) for gen in node.generators],
        )

    def visit_Name(self, node: ast.Name) -> IR.Expr:
        # role = self.symbol_table.get(node.id)
        # if role == "field":
        #     return IR.Name(f"field:{node.id}")
        # if role == "input":
        #     return IR.Name(f"input:{node.id}")
        # if role == "output":
        #     return IR.Name(f"output:{node.id}")
        return IR.Name(node.id)

    def visit_Raise(self, node: ast.Raise) -> IR.Raise:
        value = self.visit(node.exc) if node.exc is not None else IR.Literal(None)
        return IR.Raise(value=value)

    def visit_Return(self, node: ast.Return) -> IR.Return:
        value = self.visit(node.value) if node.value is not None else IR.Literal(None)
        return IR.Return(value=value)

    def visit_Subscript(self, node: ast.Subscript) -> IR.Subscript:
        return IR.Subscript(value=self.visit(node.value), index=self.visit(node.slice))

    def visit_Tuple(self, node: ast.Tuple) -> IR.Tuple:
        return IR.Tuple(values=[self.visit(elt) for elt in node.elts])

    def visit_UnaryOp(self, node: ast.UnaryOp) -> IR.Expr:
        op_map = {
            ast.USub: "-",
            ast.UAdd: "+",
            ast.Not: "not ",
        }
        op = op_map.get(type(node.op), self.ast_source(node.op))
        return IR.UnaryOp(op=op, operand=self.visit(node.operand))

    def visit_comprehension(self, node: ast.comprehension) -> IR.Comprehension:
        return IR.Comprehension(
            target=self.visit(node.target),
            iterable=self.visit(node.iter),
            ifs=[self.visit(cond) for cond in node.ifs],
        )

    def visit_keyword(self, node: ast.keyword) -> IR.Expr:
        return IR.RawExpr(self.ast_source(node))


def build_symbol_table(block_cfg) -> dict[str, str]:
    """Create a lightweight symbol table for frontend labeling only."""
    table: dict[str, str] = {"self": "self", "t": "time", "x": "state"}
    if block_cfg.nin > 0:
        table["inputs"] = "input"
        table["u"] = "input"
    if block_cfg.nout > 0:
        table["outputs"] = "output"
        table["y"] = "output"
    for name in block_cfg.self.keys():
        table[name] = "field"
    return table


def lower_block_method(method, block_cfg) -> IR.Function:
    frontend = MethodFrontend(build_symbol_table(block_cfg))
    return frontend.lower_method(method)


class IRSpecializer:
    """Specialize IR using known block locals and simple constant folding."""

    def __init__(self, block_cfg) -> None:
        self.block_cfg = block_cfg
        self.self = {k: v for k, (v, _vt) in block_cfg.self.items()}
        self.self_types = {k: vt for k, (_v, vt) in block_cfg.self.items()}
        self.input_types = list(block_cfg.itypes)
        # Type (not value) of a sampled block's synthesized self.state field,
        # if it has one -- lets isinstance()/.ndim/.size fold on state even
        # though its concrete value must stay symbolic (it changes every
        # tick, unlike a real self.X field, which is why it's deliberately
        # kept out of self.self above).
        self.state_type: VarType | None = getattr(block_cfg, "state_vt", None)
        # Max nesting depth for IRInliner.inline() (a genuinely deep but
        # non-cyclic helper-calls-helper chain, not the already-separately
        # guarded case of true recursion -- see IRInliner._stack).
        self.max_inline_depth: int = getattr(block_cfg, "max_inline_depth", 20)
        # Monotonic counter, one value per actual inline call site --
        # drives IRInliner's alpha-rename prefix instead of nesting depth
        # (two sibling inlined calls at the same depth still need distinct
        # prefixes; see IRInliner.inline's unique_id docs). Starts at 1:
        # 0 is reserved for lower_function_block()'s own top-level inline
        # of a FUNCTION block's callable, which doesn't go through here.
        self._inline_counter = 0
        # Fallback namespace for free-variable name resolution -- e.g. a
        # FUNCTION block's callable referencing a *sibling* helper defined
        # in the same module (not a nested/self attribute), the normal
        # shape for a toolbox module where one helper calls another. Only
        # the top-level callable's own __globals__, not per-nesting-level,
        # so a helper calling another helper defined in a *different*
        # module still won't resolve -- a known, narrower-than-ideal limit.
        self.extra_globals: dict[str, Any] = getattr(block_cfg, "extra_globals", None) or {}
        self._inline_depth = 0
        self.env: dict[str, Any] = {}
        # Populated properly by specialize_function(); empty default here
        # only for callers (e.g. direct specialize_expr()/eval_expr() unit
        # tests) that never go through it.
        self.local_names: set[str] = set()
        # Stmts queued by the inliner to splice before the current statement.
        self._pending_stmts: list[IR.Stmt] = []

    def specialize_function(self, fn: IR.Function) -> IR.Function:
        self.env = {}
        # Every genuine local (formal params + every Assign/Declare/For
        # target in the body) -- checked by _name_value before it ever
        # falls through to np/math/extra_globals/builtins, so a local that
        # happens to share a name with one of those (e.g. this block's own
        # `input = inputs[0]`, colliding with the builtin input()) is
        # never misresolved to it. See collect_bound_names's docstring --
        # same underlying concept IRInliner's alpha-renamer uses.
        self.local_names: set[str] = set(fn.args)
        collect_bound_names(fn.body, self.local_names)
        body = [self.specialize_stmt(stmt) for stmt in fn.body]
        body = self._flatten(body)
        return IR.Function(name=fn.name, args=fn.args, body=body)

    def _unroll_enumerate_inputs_for(self, stmt: IR.For) -> list[IR.Stmt] | None:
        """Unroll ``for i, x in enumerate(inputs): BODY`` into ``nin``
        copies of ``BODY``, substituting ``i`` -> the literal iteration
        index and ``x`` -> ``inputs[index]`` in each copy -- sound because
        the loop bound (``len(inputs) == nin``) is always known at
        generation time. Every *other* name in ``BODY`` (an accumulator
        like SUM's ``sum``/PROD's ``prod``) is deliberately left
        completely alone, not renamed per copy -- reusing
        ``_IRAlphaRenamer`` with an empty ``bound_names`` set gives
        exactly that for free (nothing to rename, only the two
        substitutions), so a genuine cross-iteration accumulator stays
        one shared variable across the unrolled copies, threaded through
        correctly, while ``i``/``x`` disappear into concrete per-copy
        values.

        This is the *only* for-loop shape bdsim's own block library
        actually uses (SUM, PROD, ...) -- returns None for anything else,
        which falls back to the generic (currently: fails at emit time
        unless somehow otherwise supported) path.

        Returns the unrolled, NOT-YET-(re)specialized statements -- the
        caller is responsible for feeding them back through
        specialize_stmt(), same as for any other statement list.
        """
        it = stmt.iterable
        if not (
            isinstance(it, IR.Call)
            and isinstance(it.func, IR.Name)
            and it.func.name == "enumerate"
            and len(it.args) == 1
            and isinstance(it.args[0], IR.Name)
            and it.args[0].name == "inputs"
        ):
            return None
        target = stmt.target
        if not (
            isinstance(target, IR.Tuple)
            and len(target.values) == 2
            and isinstance(target.values[0], IR.Name)
            and isinstance(target.values[1], IR.Name)
        ):
            return None
        idx_name = target.values[0].name
        elt_name = target.values[1].name

        unrolled: list[IR.Stmt] = []
        for k in range(len(self.input_types)):
            subst = {
                idx_name: IR.Literal(k),
                elt_name: IR.Subscript(IR.Name("inputs"), IR.Literal(k)),
            }
            renamer = _IRAlphaRenamer("", subst, set())
            unrolled.extend(
                _flatten_list([renamer.rename_stmt(s) for s in stmt.body])
            )
        return unrolled

    def _flatten(self, nodes: list[Any]) -> list[Any]:
        out: list[Any] = []
        for n in nodes:
            if isinstance(n, list):
                out.extend(self._flatten(n))
            else:
                out.append(n)
        return out

    def specialize_stmt(self, stmt: IR.Stmt) -> IR.Stmt | list[IR.Stmt]:
        _ir_coverage["spec_stmt"].add(type(stmt).__name__)
        pending_before = self._pending_stmts
        self._pending_stmts = []
        result = self._specialize_stmt_inner(stmt)
        pre = pending_before + self._pending_stmts
        self._pending_stmts = []
        if pre:
            return pre + (result if isinstance(result, list) else [result])
        return result

    def _specialize_stmt_inner(self, stmt: IR.Stmt) -> IR.Stmt | list[IR.Stmt]:
        if isinstance(stmt, IR.Assign):
            out = IR.Assign(
                self.specialize_expr(stmt.target), self.specialize_expr(stmt.value)
            )
            if isinstance(out.target, IR.Name):
                val = self.eval_expr(out.value)
                if val is UNKNOWN:
                    self.env.pop(out.target.name, None)
                else:
                    self.env[out.target.name] = val
            return out
        if isinstance(stmt, IR.Declare):
            value = None if stmt.value is None else self.specialize_expr(stmt.value)
            return IR.Declare(self.specialize_expr(stmt.target), stmt.annotation, value)
        if isinstance(stmt, IR.ExprStmt):
            return IR.ExprStmt(self.specialize_expr(stmt.value))
        if isinstance(stmt, IR.Return):
            return IR.Return(self.specialize_expr(stmt.value))
        if isinstance(stmt, IR.Raise):
            return IR.Raise(self.specialize_expr(stmt.value))
        if isinstance(stmt, IR.For):
            unrolled = self._unroll_enumerate_inputs_for(stmt)
            if unrolled is not None:
                return self._flatten([self.specialize_stmt(s) for s in unrolled])
            return IR.For(
                self.specialize_expr(stmt.target),
                self.specialize_expr(stmt.iterable),
                self._flatten([self.specialize_stmt(s) for s in stmt.body]),
                self._flatten([self.specialize_stmt(s) for s in stmt.orelse]),
            )
        if isinstance(stmt, IR.If):
            # Lazy: fold the condition first, and only specialize whichever
            # branch actually survives. Previously specialized both branches
            # unconditionally before deciding which to keep -- harmless while
            # the pipeline silently passed through anything it couldn't
            # translate, but wrong once unresolvable constructs fail loudly
            # (a dead branch, e.g. Integrator_S.next()'s disabled-`enable`
            # path calling np.zeros(), would fail even though it can never
            # actually be reached once the guarding condition is known).
            cond = self.specialize_expr(stmt.condition)
            val = self.eval_expr(cond)
            if val is True:
                return self._flatten([self.specialize_stmt(s) for s in stmt.body])
            if val is False:
                return self._flatten([self.specialize_stmt(s) for s in stmt.orelse])
            body = self._flatten([self.specialize_stmt(s) for s in stmt.body])
            orelse = self._flatten([self.specialize_stmt(s) for s in stmt.orelse])
            return IR.If(cond, body, orelse)
        return stmt

    def specialize_expr(self, expr: IR.Expr) -> IR.Expr:
        _ir_coverage["spec_expr"].add(type(expr).__name__)
        if isinstance(expr, IR.Attribute):
            value = self.specialize_expr(expr.value)
            out = IR.Attribute(value, expr.attr)
            if isinstance(value, IR.Name) and value.name == "self":
                # self.<field> (including the synthesized self.state) must
                # stay a real struct-field reference in the emitted code,
                # even when its current value happens to be known --
                # folding it away would defeat keep_fields
                # (telemetry/live tuning) and the whole point of a
                # mutable self struct. Unlike every sibling case below,
                # this branch deliberately never calls eval_expr() to fold.
                return out
            val = self.eval_expr(out)
            if val is not UNKNOWN and not isinstance(val, VarType) and not callable(val):
                # callable(val) excluded: a module-attribute reference
                # to a *function* (np.array, np.zeros, ...) must stay an
                # IR.Attribute, not get wrapped in an IR.Literal -- the
                # IR.Call handling below pattern-matches specific
                # `isinstance(out.func, IR.Attribute)` shapes (e.g. the
                # np.array(x) no-op coercion, x.item()) that only fire
                # when the callee is still a plain attribute reference.
                return _literal_from(val)
            return out
        if isinstance(expr, IR.Subscript):
            out = IR.Subscript(
                self.specialize_expr(expr.value), self.specialize_expr(expr.index)
            )
            val = self.eval_expr(out)
            if isinstance(val, VarType):
                # Keep analysis-only type tokens out of printed IR..
                return out
            if val is not UNKNOWN and not isinstance(val, VarType):
                return _literal_from(val)
            return out
        if isinstance(expr, IR.UnaryOp):
            out = IR.UnaryOp(expr.op, self.specialize_expr(expr.operand))
            val = self.eval_expr(out)
            if val is not UNKNOWN and not isinstance(val, VarType):
                return _literal_from(val)
            return out
        if isinstance(expr, IR.BinaryOp):
            out = IR.BinaryOp(
                self.specialize_expr(expr.left),
                expr.op,
                self.specialize_expr(expr.right),
            )
            val = self.eval_expr(out)
            if val is not UNKNOWN and not isinstance(val, VarType):
                return _literal_from(val)
            return out
        if isinstance(expr, IR.Compare):
            out = IR.Compare(
                self.specialize_expr(expr.left),
                expr.op,
                self.specialize_expr(expr.right),
            )
            val = self.eval_expr(out)
            if val is not UNKNOWN and not isinstance(val, VarType):
                return _literal_from(val)
            return out
        if isinstance(expr, IR.BoolOp):
            out = IR.BoolOp(expr.op, [self.specialize_expr(v) for v in expr.values])
            val = self.eval_expr(out)
            if val is not UNKNOWN and not isinstance(val, VarType):
                return _literal_from(val)
            return out
        if isinstance(expr, IR.IfExpr):
            cond = self.specialize_expr(expr.condition)
            cond_val = self.eval_expr(cond)
            if cond_val is True:
                return self.specialize_expr(expr.body)
            if cond_val is False:
                return self.specialize_expr(expr.orelse)
            return IR.IfExpr(
                self.specialize_expr(expr.body), cond, self.specialize_expr(expr.orelse)
            )
        if isinstance(expr, IR.Call):
            out = IR.Call(
                self.specialize_expr(expr.func),
                [self.specialize_expr(a) for a in expr.args],
            )
            # Fold list(tuple_or_list) -> IR.List([...])
            if (
                isinstance(out.func, IR.Name)
                and out.func.name == "list"
                and len(out.args) == 1
                and isinstance(out.args[0], (IR.Tuple, IR.List))
            ):
                return IR.List(out.args[0].values)
            # np.array(x) is a no-op coercion for codegen purposes -- the
            # Eigen/C++ representation is already array-like -- so drop the
            # wrapper entirely rather than emitting an unrenderable call.
            if (
                isinstance(out.func, IR.Attribute)
                and isinstance(out.func.value, IR.Name)
                and out.func.value.name == "np"
                and out.func.attr == "array"
                and len(out.args) == 1
            ):
                return out.args[0]
            # x.item() unwraps a size-1 ndarray to a plain scalar -- a
            # common idiom (ZOH/Integrator_S) for letting state be a
            # scalar or a vector. The receiver's *value* can't fold (state
            # is symbolic), but its *type* can (self.state_type / the
            # input-type table), which is enough to recognize the pattern
            # and hand it to the emitter as a language-neutral intrinsic.
            if (
                isinstance(out.func, IR.Attribute)
                and out.func.attr == "item"
                and len(out.args) == 0
            ):
                recv_vt = self.eval_expr(out.func.value)
                if isinstance(recv_vt, VarType) and recv_vt.dtype == "ndarray":
                    return IR.IntrinsicCall(
                        "numpy.item", [out.func.value], VarType._make("float")
                    )
            val = self.eval_expr(out)
            if val is not UNKNOWN and not isinstance(val, VarType):
                return _literal_from(val)
            # --- Intrinsic annotation (Strategy A) ---
            # Mark the call with an IntrinsicCall wrapper so the emitter
            # can render it without knowing about Python function objects.
            f_val = self.eval_expr(out.func)
            arg_vals = [self.eval_expr(a) for a in out.args]
            # No longer gated on "every arg value/type is known" -- a
            # wildcard-registered intrinsic (sig=(), e.g. min/max) applies
            # regardless of arg values by definition, and an exact-sig
            # intrinsic (skew/vex/...) already can't spuriously match
            # without its real VarType present (_vtsig only includes
            # actual VarType args; UNKNOWN is filtered out exactly like
            # any other non-VarType value already was). This also matters
            # for a nested intrinsic call as an argument (e.g. min(a,
            # max(b, c))): IR.IntrinsicCall always evaluates to UNKNOWN
            # (deliberately -- see eval_expr's own IntrinsicCall case), so
            # the outer call would otherwise never even attempt a lookup.
            if callable(f_val):
                hit = _lookup_intrinsic(f_val, arg_vals)
                if hit is not None:
                    result_vt_fn, intrinsic_name = hit
                    result_vt = result_vt_fn(arg_vals) if result_vt_fn else None
                    return IR.IntrinsicCall(intrinsic_name, out.args, result_vt)
            # --- IR inliner (Strategy B) ---
            if callable(f_val) and f_val not in (
                len,
                isinstance,
                enumerate,
                zip,
                list,
                range,
                print,
            ):
                fn_desc = getattr(f_val, "__qualname__", None) or repr(f_val)
                fn_module = getattr(f_val, "__module__", None) or ""
                if fn_module:
                    fn_desc = f"{fn_module}.{fn_desc}"
                top_package = fn_module.split(".")[0]

                if top_package in _NO_INLINE_PACKAGES:
                    # A numeric library's *internals* often do have real
                    # Python source (e.g. np.linalg.norm is a thin wrapper),
                    # so the inliner would happily recurse into it -- and
                    # hit genuinely complex, shape/dtype-branching code
                    # (np.linalg.norm calls _multi_svd_norm, branches on
                    # ord/axis/keepdims, ...) that was never going to
                    # specialize cleanly. Failing deep inside that produces
                    # a useless error naming some auto-generated inlined
                    # local, not the call that actually caused it. Refusing
                    # to even attempt inlining here keeps the failure at
                    # the actual call site, with a clear message, instead.
                    # Doesn't apply to ordinary third-party/toolbox helpers
                    # (spatialmath, RTB, MVTB, a user's own module) --
                    # those are exactly what the inliner exists for.
                    raise NotImplementedError(
                        f"codegen: cannot transpile call to {fn_desc}() -- "
                        f"it's from {top_package}, whose internals are too "
                        f"complex to reliably inline even when Python source "
                        f"happens to be available. Register it in "
                        f"_INTRINSICS with a hand-written C++ implementation "
                        f"instead."
                    )

                try:
                    self._inline_counter += 1
                    inline_result = IRInliner.inline(
                        f_val,
                        out.args,
                        depth=self._inline_depth,
                        max_depth=self.max_inline_depth,
                        unique_id=self._inline_counter,
                    )
                    if inline_result is not None:
                        extra_stmts, result_expr = inline_result
                        # These are new locals (alpha-renamed, so already
                        # collision-free against the outer function's own
                        # names -- see IRInliner.inline) spliced into an
                        # already-in-progress specialize_function() run;
                        # self.local_names was only seeded from the outer
                        # function's own body at the start, so without this
                        # they'd be invisible to the same shadowing guard
                        # in _name_value (e.g. an inlined helper with its
                        # own `input = ...` local).
                        collect_bound_names(extra_stmts, self.local_names)
                        self._inline_depth += 1
                        try:
                            # Specialize the inlined body
                            spec_extra = []
                            for s in extra_stmts:
                                r = self.specialize_stmt(s)
                                spec_extra.extend(r if isinstance(r, list) else [r])
                            self._pending_stmts.extend(spec_extra)
                            result = self.specialize_expr(result_expr)
                        finally:
                            self._inline_depth -= 1
                        return result
                except (RecursionError, OSError, TypeError, AttributeError):
                    pass
                # Not a registered intrinsic (checked above) and not
                # inlineable -- no Python source available (e.g. a
                # compiled/C-extension function), or the nesting limit was
                # hit. Fail loudly now, naming the call, rather than
                # silently emitting a reference to a C++ symbol that was
                # never defined and deferring the failure to the C++
                # compiler with a far less specific error.
                raise NotImplementedError(
                    f"codegen: cannot transpile call to {fn_desc}() -- not a "
                    f"registered intrinsic (add one to _INTRINSICS with a "
                    f"hand-written C++ implementation) and its source isn't "
                    f"available for inlining (e.g. a compiled/C-extension "
                    f"function), or it nests deeper than max_inline_depth "
                    f"({self.max_inline_depth})"
                )
            return out
        if isinstance(expr, IR.List):
            return IR.List([self.specialize_expr(v) for v in expr.values])
        if isinstance(expr, IR.Tuple):
            return IR.Tuple([self.specialize_expr(v) for v in expr.values])
        if isinstance(expr, IR.ListComp):
            return IR.ListComp(
                self.specialize_expr(expr.elt),
                [
                    IR.Comprehension(
                        self.specialize_expr(gen.target),
                        self.specialize_expr(gen.iterable),
                        [self.specialize_expr(c) for c in gen.ifs],
                    )
                    for gen in expr.generators
                ],
            )
        return expr

    def _name_value(self, name: str):
        if name in self.env:
            return self.env[name]
        if name in self.local_names:
            # A genuine local (formal param or assigned within this
            # function) whose current value isn't concretely foldable --
            # must not fall through to np/math/extra_globals/builtins
            # below even if it happens to share a name with one of those
            # (e.g. a block's own `input = inputs[0]` shadows the builtin
            # input()); real Python scoping would shadow it too.
            return UNKNOWN
        if name == "np":
            return np
        if name == "math":
            return math
        if name == "isinstance":
            return isinstance
        if name == "len":
            return len
        if name == "enumerate":
            return enumerate
        if name == "zip":
            return zip
        if name in self.extra_globals:
            return self.extra_globals[name]
        # Last-resort fallback: any other Python builtin (min, max, abs,
        # round, sum, ...) referenced by bare name. Without this, a name
        # like `min` silently resolves to UNKNOWN (callable(UNKNOWN) is
        # False), so a call to it skips both the intrinsic and inline
        # strategies without ever raising -- the IR.Call node just passes
        # through unresolved, deferring the failure to CppEmitter, which
        # reports a much less specific "cannot infer C++ type" error with
        # no mention of `min` at all. Resolving the name here lets that
        # call reach the same loud, specific failure (or a registered
        # intrinsic, e.g. min/max -- see _INTRINSICS) as math.sqrt() does.
        builtin = getattr(builtins, name, UNKNOWN)
        if builtin is not UNKNOWN:
            return builtin
        return UNKNOWN

    def eval_expr(self, expr: IR.Expr):
        if isinstance(expr, IR.Literal):
            return expr.value
        if isinstance(expr, IR.Name):
            return self._name_value(expr.name)
        if isinstance(expr, IR.Attribute):
            # Return actual self values so 'is None' / 'is not None' folds correctly.
            # VarType is only needed for inputs (where we have no runtime value).
            if isinstance(expr.value, IR.Name) and expr.value.name == "self":
                if expr.attr in self.self:
                    return self.self[expr.attr]
                if expr.attr == "state" and self.state_type is not None:
                    return self.state_type
            base = self.eval_expr(expr.value)
            if base is UNKNOWN:
                return UNKNOWN
            if isinstance(base, VarType):
                # Type-level (not value-level) folding for ndarray shape
                # introspection -- e.g. the common `if x.ndim == 1 and
                # x.size == 1: x = x.item()` scalar-unwrapping idiom, used
                # by several sampled blocks on their state.
                if base.dtype == "ndarray" and isinstance(base.dims, tuple):
                    if expr.attr == "ndim":
                        return len(base.dims)
                    if expr.attr == "size":
                        size = 1
                        for d in base.dims:
                            size *= d
                        return size
                return UNKNOWN
            try:
                return getattr(base, expr.attr)
            except Exception:
                return UNKNOWN
        if isinstance(expr, IR.Subscript):
            # Handle inputs[i] to get type information
            if (
                isinstance(expr.value, IR.Name)
                and expr.value.name in ("inputs", "input:inputs")
                and isinstance(expr.index, IR.Literal)
                and isinstance(expr.index.value, int)
                and 0 <= expr.index.value < len(self.input_types)
            ):
                return self.input_types[expr.index.value]
            base = self.eval_expr(expr.value)
            idx = self.eval_expr(expr.index)
            if base is UNKNOWN or idx is UNKNOWN:
                return UNKNOWN
            try:
                return base[idx]
            except Exception:
                return UNKNOWN
        if isinstance(expr, IR.UnaryOp):
            v = self.eval_expr(expr.operand)
            if v is UNKNOWN:
                return UNKNOWN
            try:
                if expr.op == "-":
                    return -v
                if expr.op == "+":
                    return +v
                if expr.op.strip() == "not":
                    return not v
            except Exception:
                return UNKNOWN
            return UNKNOWN
        if isinstance(expr, IR.BinaryOp):
            l = self.eval_expr(expr.left)
            r = self.eval_expr(expr.right)
            if l is UNKNOWN or r is UNKNOWN:
                return UNKNOWN
            # Type propagation when operands are VarType (static analysis only)
            if isinstance(l, VarType) or isinstance(r, VarType):
                _scalar_rank = {"bool": 0, "int": 1, "float": 2}
                if isinstance(l, VarType) and isinstance(r, VarType):
                    if l.dtype in _scalar_rank and r.dtype in _scalar_rank:
                        if expr.op in ("+", "-", "*", "/", "%"):
                            rank = max(_scalar_rank[l.dtype], _scalar_rank[r.dtype])
                            return VarType._make(["bool", "int", "float"][rank])
                # Elementwise-shape-preserving ops (+, -, *, /, %) between
                # an ndarray-typed operand and *anything else* (a concrete
                # scalar like a block's own self.gain, or another VarType)
                # keep the ndarray operand's exact shape/etype -- real
                # NumPy broadcasting semantics for scalar-op-array, not
                # just a heuristic. Previously only handled when *both*
                # operands were VarType, so a block's common
                # `self.gain * (u[0] - x) / self.T` idiom (Deriv_S; unlike
                # Integrator_S's bare `result = x`) lost all type
                # information the moment a concrete self.field entered the
                # expression -- the very next isinstance(result,
                # np.ndarray)/.ndim/.size/.item() scalar-unwrap check (the
                # same idiom Integrator_S already folds correctly) then
                # couldn't fold either, and reached the emitter as raw,
                # uncompilable Python-isinstance/NumPy-attribute text.
                if expr.op in ("+", "-", "*", "/", "%"):
                    l_nd = l if isinstance(l, VarType) and l.dtype == "ndarray" else None
                    r_nd = r if isinstance(r, VarType) and r.dtype == "ndarray" else None
                    nd = l_nd or r_nd
                    if nd is not None:
                        return VarType._make("ndarray", nd.etype, nd.dims)
                return UNKNOWN
            try:
                if expr.op == "+":
                    return l + r
                if expr.op == "-":
                    return l - r
                if expr.op == "*":
                    return l * r
                if expr.op == "/":
                    return l / r
                if expr.op == "%":
                    return l % r
                if expr.op == "@":
                    return l @ r
            except Exception:
                return UNKNOWN
            return UNKNOWN
        if isinstance(expr, IR.Compare):
            l = self.eval_expr(expr.left)
            r = self.eval_expr(expr.right)
            if l is UNKNOWN or r is UNKNOWN:
                return UNKNOWN
            try:
                if expr.op == "==":
                    return l == r
                if expr.op == "!=":
                    return l != r
                if expr.op == ">":
                    return l > r
                if expr.op == ">=":
                    return l >= r
                if expr.op == "<":
                    return l < r
                if expr.op == "<=":
                    return l <= r
                if expr.op == "is":
                    return l is r
                if expr.op == "is not":
                    return l is not r
                if expr.op == "in":
                    return l in r
                if expr.op == "not in":
                    return l not in r
            except Exception:
                return UNKNOWN
            return UNKNOWN
        if isinstance(expr, IR.BoolOp):
            vals = [self.eval_expr(v) for v in expr.values]
            if expr.op == "and":
                if any(v is False for v in vals):
                    return False
                if all(v is True for v in vals):
                    return True
                return UNKNOWN
            if expr.op == "or":
                if any(v is True for v in vals):
                    return True
                if all(v is False for v in vals):
                    return False
                return UNKNOWN
            return UNKNOWN
        if isinstance(expr, IR.IfExpr):
            cond_val = self.eval_expr(expr.condition)
            if cond_val is True:
                return self.eval_expr(expr.body)
            if cond_val is False:
                return self.eval_expr(expr.orelse)
            return UNKNOWN
        if isinstance(expr, IR.IntrinsicCall):
            return UNKNOWN  # Intrinsic calls have known C++ forms but unknown Python values
        if isinstance(expr, IR.Call):
            f = self.eval_expr(expr.func)
            args = [self.eval_expr(a) for a in expr.args]
            if f is UNKNOWN or any(a is UNKNOWN for a in args):
                return UNKNOWN
            # --- Intrinsic table lookup (Strategy A) ---
            vt_args = [a for a in args if isinstance(a, VarType)]
            if callable(f) and len(vt_args) == len(args):
                hit = _lookup_intrinsic(f, args)
                if hit is not None:
                    result_vt_fn, _iname = hit
                    return result_vt_fn(args)
            try:
                if f is len and len(args) == 1:
                    return len(args[0])
                if f is isinstance and len(args) == 2:
                    if isinstance(args[0], VarType) and isinstance(args[1], type):
                        type_map = {
                            np.ndarray: "ndarray",
                            int: "int",
                            float: "float",
                            bool: "bool",
                            str: "str",
                            list: "list",
                            tuple: "list",
                            type(None): "None",
                        }
                        want = type_map.get(args[1], None)
                        if want is not None:
                            return args[0].dtype == want
                        return UNKNOWN
                    return isinstance(args[0], args[1])
            except Exception:
                return UNKNOWN
            return UNKNOWN
        return UNKNOWN


def _literal_from(value: Any) -> IR.Literal:
    return IR.Literal(value)


# ---------------------------------------------------------------------------
# Intrinsic table  (Strategy A)
# ---------------------------------------------------------------------------
# Maps a Python callable (identified by __module__ + __qualname__ + arg-type
# signature) to a language-neutral intrinsic name string such as "bdsim.skew3".
#
# The name string is embedded in IR.IntrinsicCall.name.  Each Emitter subclass
# owns a INTRINSIC_IMPLS dict that maps the same name to its target-language
# rendering function and any required helper/preamble code.
#
# Key:   (module: str, qualname: str, arg_sigs: tuple[str, ...])
#        where each arg_sig is _vtsig(vt) — e.g. "ndarray:float64:1"
# Value: (result_vt_fn(arg_vts)->VarType|None, intrinsic_name: str)
# ---------------------------------------------------------------------------


def _vtsig(vt: VarType) -> str:
    """Canonical string key for a VarType, used in intrinsic lookup."""
    if vt.dtype == "ndarray":
        ndim = (
            len(vt.dims)
            if isinstance(vt.dims, tuple)
            else (1 if vt.dims is not None else 0)
        )
        return f"ndarray:{vt.etype}:{ndim}"
    return vt.dtype


_INTRINSICS: dict[tuple, tuple] = {}


def _reg(
    module: str, qualname: str, sig: tuple[str, ...], result_vt, intrinsic_name: str
):
    """Register a Python callable → intrinsic name mapping."""
    _INTRINSICS[(module, qualname, sig)] = (result_vt, intrinsic_name)


# spatialmath.base intrinsics
_reg(
    "spatialmath.base",
    "skew",
    ("ndarray:float64:1",),
    lambda vts: VarType._make("ndarray", "float64", (3, 3)),
    "bdsim.skew3",
)
_reg(
    "spatialmath.base",
    "skewa",
    ("ndarray:float64:1",),
    lambda vts: VarType._make("ndarray", "float64", (4, 4)),
    "bdsim.skewa",
)
_reg(
    "spatialmath.base",
    "vex",
    ("ndarray:float64:2",),
    lambda vts: VarType._make("ndarray", "float64", (3,)),
    "bdsim.vex3",
)
_reg(
    "spatialmath.base",
    "r2t",
    ("ndarray:float64:2",),
    lambda vts: VarType._make("ndarray", "float64", (4, 4)),
    "bdsim.r2t",
)
_reg(
    "spatialmath.base",
    "t2r",
    ("ndarray:float64:2",),
    lambda vts: VarType._make("ndarray", "float64", (3, 3)),
    "bdsim.t2r",
)
_reg(
    "spatialmath.base",
    "norm",
    ("ndarray:float64:1",),
    lambda vts: VarType._make("float"),
    "bdsim.norm",
)
_reg(
    "spatialmath.base",
    "norm",
    ("ndarray:float64:2",),
    lambda vts: VarType._make("float"),
    "bdsim.norm",
)
_reg(
    "spatialmath.base",
    "unit",
    ("ndarray:float64:1",),
    lambda vts: VarType._make("ndarray", "float64", (3,)),
    "bdsim.unit",
)
_reg(
    "spatialmath.base",
    "cross",
    ("ndarray:float64:1", "ndarray:float64:1"),
    lambda vts: VarType._make("ndarray", "float64", (3,)),
    "bdsim.cross",
)


def _scalar_minmax_result_vt(arg_vals: list) -> VarType:
    """Result type for the builtin min()/max() intrinsics below -- promotes
    to the widest scalar dtype among the (up to 2) arguments actually
    passed, whether each arrives as a concrete value or a VarType (a
    symbolic arg, e.g. a block input, carries only a VarType; a concrete
    self.field value carries its own Python type directly -- see
    _lookup_intrinsic's signature filtering, which is why this can't just
    read the registration key's sig tuple)."""

    def dtype_of(v: Any) -> str:
        if isinstance(v, VarType):
            return v.dtype
        if isinstance(v, bool):
            return "bool"
        if isinstance(v, float):
            return "float"
        if isinstance(v, int):
            return "int"
        return "float"

    dtypes = [dtype_of(v) for v in arg_vals]
    if "float" in dtypes:
        return VarType._make("float")
    if "int" in dtypes:
        return VarType._make("int")
    return VarType._make("bool")


def _abs_result_vt(arg_vals: list) -> VarType:
    """Result type for the builtin abs() intrinsic -- abs() preserves its
    argument's dtype (unlike min/max, which promote across two args)."""
    v = arg_vals[0] if arg_vals else None
    if isinstance(v, VarType):
        return v
    if isinstance(v, bool):
        return VarType._make("bool")
    if isinstance(v, float):
        return VarType._make("float")
    if isinstance(v, int):
        return VarType._make("int")
    return VarType._make("float")


# sig=() is a wildcard match (see _lookup_intrinsic's key_any fallback) --
# min()/max() take scalars of any arithmetic type, and the render below
# (static_cast<double> on both operands) works regardless of the mix.
_reg("builtins", "min", (), _scalar_minmax_result_vt, "python.min")
_reg("builtins", "max", (), _scalar_minmax_result_vt, "python.max")
# abs() was previously an accidental "unresolved call passes through
# verbatim, and C++ happens to have a same-named global too" pass-through
# (see CppEmitter.expr_BinaryOp's "unqualified-call style (e.g. abs(),
# matmul())" comment) -- fragile by construction (matmul() is the same
# pattern and is *not* a real function; see bdsim#93). Now a real,
# registered intrinsic like everything else.
_reg("builtins", "abs", (), _abs_result_vt, "python.abs")

# math.* functions -- wildcard-registered (sig=()) like min/max/abs above,
# since these are always plain scalar-in-scalar-out. math.pi/math.e (bare
# attribute access, not a call) already fold via specialize_expr's
# IR.Attribute constant-folding; these are for the *calls* -- math.sqrt(x)
# and friends, which previously had no coverage at all and hit the loud
# "not a registered intrinsic" failure unconditionally.
def _math_float_result(arg_vals: list) -> VarType:
    return VarType._make("float")


def _math_int_result(arg_vals: list) -> VarType:
    # math.floor()/math.ceil() return int in Python (unlike std::floor/
    # ceil, which return a floating type) -- cast in the render, not here.
    return VarType._make("int")


for _math_fn in ("sqrt", "sin", "cos", "tan", "exp", "log", "atan2", "pow"):
    _reg("math", _math_fn, (), _math_float_result, f"python.math.{_math_fn}")
for _math_fn in ("floor", "ceil"):
    _reg("math", _math_fn, (), _math_int_result, f"python.math.{_math_fn}")
del _math_fn

# NumPy scalar-type constructors (np.uint16(x), np.float32(x), ...) called
# directly -- e.g. inside an ordinary FUNCTION block's Python source doing
# an explicit cast. The CAST block (bdsim.blocks.functions.Cast) below
# doesn't go through this table at all -- its dtype only exists as a
# per-instance string, which can't be resolved through a call expression
# the normal way (see lower_cast_block's docstring) -- but reuses these
# same "python.cast.<etype>" intrinsic names directly, so there's one
# rendering implementation either way.
def _numpy_cast_result_vt(etype: str):
    def result_vt(arg_vals: list) -> VarType:
        if etype == "bool":
            return VarType._make("bool")
        return VarType._make("ndarray", etype, ())

    return result_vt


for _cast_etype in (
    "int8", "int16", "int32", "int64",
    "uint8", "uint16", "uint32", "uint64",
    "float32", "float64", "bool",
):
    _reg("numpy", _cast_etype, (), _numpy_cast_result_vt(_cast_etype), f"python.cast.{_cast_etype}")
del _cast_etype


def _lookup_intrinsic(fn_obj, arg_vts: list) -> tuple | None:
    """Return ``(result_vt_fn, intrinsic_name)`` or None."""
    try:
        module = fn_obj.__module__
        name = fn_obj.__qualname__
    except AttributeError:
        return None
    sig = tuple(_vtsig(a) for a in arg_vts if isinstance(a, VarType))
    key = (module, name, sig)
    if key in _INTRINSICS:
        return _INTRINSICS[key]
    key_any = (module, name, ())
    if key_any in _INTRINSICS:
        return _INTRINSICS[key_any]
    return None


# ---------------------------------------------------------------------------
# IR inliner  (Strategy B)
# ---------------------------------------------------------------------------


class IRInliner:
    """Inline a Python callable into IR at a call site.

    Lowers the callee source, α-renames its locals (prefix ``_il{depth}_``),
    substitutes actual args for formal params, and returns a tuple:
      (extra_stmts: list[IR.Stmt], result_expr: IR.Expr)

    The caller should prepend ``extra_stmts`` before the call site and
    replace the call with ``result_expr``.
    """

    _stack: set[int] = set()  # function object ids currently being inlined
    MAX_DEPTH = 20  # default when a caller doesn't pass max_depth explicitly

    @classmethod
    def inline(
        cls,
        fn_obj,
        arg_exprs: list[IR.Expr],
        depth: int = 0,
        max_depth: int | None = None,
        unique_id: int | None = None,
    ) -> tuple[list[IR.Stmt], IR.Expr] | None:
        """Return (stmts, result_expr) or None if not inlineable.

        ``depth`` is the current nesting level (the caller is responsible
        for incrementing it across recursive inlining -- this method does
        not call itself). Not a cycle guard -- true recursion is caught
        separately by ``_stack`` below, regardless of depth -- ``depth``
        is purely a bound on how far a genuinely non-cyclic chain of
        nested helper calls gets unrolled, for sane generated-code size.

        ``unique_id``, not ``depth``, drives the ``_il{unique_id}_``
        alpha-rename prefix (falls back to ``depth`` if not given, for
        callers that only ever make one top-level inline call). Two
        *sibling* inlined calls at the same nesting depth -- e.g. a
        function returning ``[helper_a(u), helper_b(u)]`` -- are not
        cyclic and don't collide with each other's names via ``_stack``,
        but they *do* both sit at ``depth`` 0 if keyed on depth alone;
        if both happen to use a same-named local (e.g. both use ``tmp``),
        depth-keyed prefixes collide and silently corrupt the generated
        code (second inlined ``tmp`` overwrites the first, both outputs
        get the second helper's value). The caller is responsible for
        passing a value that's unique per actual inline call site, not
        per nesting level.
        """
        if depth >= (max_depth if max_depth is not None else cls.MAX_DEPTH):
            return None
        fn_id = id(fn_obj)
        if fn_id in cls._stack:
            raise RecursionError(f"IRInliner: recursion detected inlining {fn_obj!r}")
        try:
            import inspect, textwrap

            src = textwrap.dedent(inspect.getsource(fn_obj))
        except (OSError, TypeError):
            return None

        cls._stack.add(fn_id)
        try:
            tree = ast.parse(src)
            func_def = tree.body[0]
            if not isinstance(func_def, ast.FunctionDef):
                return None

            prefix = f"_il{unique_id if unique_id is not None else depth}_"
            formal_names = [a.arg for a in func_def.args.args]
            # Build substitution map: formal → actual arg expr
            subst: dict[str, IR.Expr] = {}
            for formal, actual in zip(formal_names, arg_exprs):
                subst[formal] = actual

            frontend = MethodFrontend({})
            raw_body = frontend.lower_block(func_def.body)

            bound_names: set[str] = set(formal_names)
            collect_bound_names(raw_body, bound_names)

            renamer = _IRAlphaRenamer(prefix, subst, bound_names)
            renamed_body = [renamer.rename_stmt(s) for s in raw_body]
            renamed_body = _flatten_list(renamed_body)

            # Extract return value; everything before it becomes extra_stmts
            result_expr: IR.Expr = IR.Literal(None)
            extra_stmts: list[IR.Stmt] = []
            for s in renamed_body:
                if isinstance(s, IR.Return):
                    result_expr = s.value
                else:
                    extra_stmts.append(s)

            return extra_stmts, result_expr
        finally:
            cls._stack.discard(fn_id)


def lower_function_block(block) -> IR.Function:
    """Synthesize ``output()`` IR for a ``FUNCTION`` block by inlining its
    user-supplied callable directly.

    ``Function.output()``'s own Python source can never lower through the
    normal AST pipeline -- it wraps the call in a ``try/except`` (no
    ``visit_Try`` in ``MethodFrontend``, and there's no sensible embedded-C++
    translation for exception handling anyway) and dispatches dynamically
    via ``*args``/``**kwargs``. The user's callable itself, on the other
    hand, is exactly what ``IRInliner`` already exists to inline -- so
    bypass ``output()`` entirely and inline ``block.func`` against
    ``inputs[i]`` references instead.

    Only the common case is supported: a single callable, no ``fargs``/
    ``fkwargs``, not ``persistent``. The other FUNCTION variants (a list of
    per-output callables, extra static args, persistent state) would need
    real design work, not a quick extension of this -- fails loudly rather
    than silently mishandling them.
    """
    func = block.func
    if isinstance(func, (list, tuple)):
        raise NotImplementedError(
            f"codegen: FUNCTION block '{block.name}' uses a list of "
            "callables (one per output) -- not yet supported"
        )
    if getattr(block, "args", None) or getattr(block, "kwargs", None):
        raise NotImplementedError(
            f"codegen: FUNCTION block '{block.name}' uses fargs/fkwargs -- "
            "not yet supported"
        )
    if getattr(block, "userdata", None) is not None:
        raise NotImplementedError(
            f"codegen: FUNCTION block '{block.name}' uses persistent=True "
            "-- not yet supported"
        )

    arg_exprs: list[IR.Expr] = [
        IR.Subscript(IR.Name("inputs"), IR.Literal(i)) for i in range(block.nin)
    ]
    inline_result = IRInliner.inline(func, arg_exprs)
    if inline_result is None:
        raise NotImplementedError(
            f"codegen: could not inline FUNCTION block '{block.name}'s "
            f"callable ({func!r}) -- source not available (e.g. a "
            "builtin), or not a plain function/lambda"
        )
    extra_stmts, result_expr = inline_result
    if not isinstance(result_expr, IR.List):
        result_expr = IR.List([result_expr])

    return IR.Function(
        name="output",
        args=["self", "t", "inputs", "x"],
        body=extra_stmts + [IR.Return(result_expr)],
    )


def lower_cast_block(block) -> IR.Function:
    """Synthesize ``output()`` IR for a ``CAST`` block directly from its
    ``dtype`` -- entirely metadata-driven, nothing to transpile from
    Python source at all.

    ``Cast.output()``'s real Python body does a dict-keyed lookup
    (``self._NP_TYPE[self.dtype](inputs[0])``) to pick the right NumPy
    scalar constructor -- fine for bdsim's own simulator, since dict
    lookups are ordinary Python at runtime, but not something codegen's
    self-attribute resolution can ever follow: the constructor itself
    (a bare NumPy type, e.g. ``np.uint16``) isn't representable as a
    ``VarType`` (see ``_block_cfg``'s try/except around ``VarType(value)``
    for exactly this kind of non-data attribute), so it can never survive
    onto ``self`` as something specialize_expr could read back out --
    regardless of how indirectly it's stored or looked up. ``self.dtype``
    (the *string*) is representable, but branching a C++ ``static_cast``
    on a runtime string isn't meaningful either. Since the whole point of
    a CAST block is that its behavior is fully fixed at construction time
    -- the dtype never changes after ``__init__`` -- bypassing
    ``output()``'s source and synthesizing the call directly is the
    actual right answer, not a workaround: there's no Python source that
    *should* need transpiling here at all, matching the same reasoning
    that makes IOBlockMixin blocks declaration-only. Reuses the
    ``python.cast.<etype>`` intrinsic names/renders registered for a
    direct ``np.uint16(x)``-style call (see ``_reg("numpy", "uint16",
    ...)`` above) -- one rendering implementation either way.
    """
    etype = block.dtype
    result_vt = VarType._make("bool") if etype == "bool" else VarType._make("ndarray", etype, ())
    call = IR.IntrinsicCall(
        f"python.cast.{etype}",
        [IR.Subscript(IR.Name("inputs"), IR.Literal(0))],
        result_vt,
    )
    return IR.Function(
        name="output",
        args=["self", "t", "inputs", "x"],
        body=[IR.Return(IR.List([call]))],
    )


def _flatten_list(nodes):
    out = []
    for n in nodes:
        if isinstance(n, list):
            out.extend(_flatten_list(n))
        else:
            out.append(n)
    return out


class _IRAlphaRenamer:
    """α-rename locals in IR, substituting formals with actual arg exprs.

    Only renames names in ``bound_names`` (formals plus anything actually
    assigned within the inlined function's own body -- see
    :func:`collect_bound_names`). Any other ``IR.Name`` is a free
    reference (a module like ``math``, a sibling helper function used as
    a value, a builtin, ...) and must be left alone: renaming it would
    point it at a local that's never declared. Previously every
    non-substituted ``IR.Name`` was renamed unconditionally, which
    silently corrupted free references reached other than as a direct
    call target -- e.g. ``math.pi`` (an ``IR.Attribute`` whose ``.value``
    is ``IR.Name("math")``) became the invalid ``_il0_math.pi``. The
    direct-call-target case (``math.sin(x)``, another top-level ``def``)
    had its own narrower carve-out for the same underlying reason; with
    ``IR.Name`` itself now discriminating correctly, the call case no
    longer needs a special case of its own.
    """

    def __init__(
        self, prefix: str, subst: dict[str, IR.Expr], bound_names: set[str]
    ) -> None:
        self.prefix = prefix
        self.subst = subst  # formal_name -> IR.Expr replacement
        self.bound_names = bound_names  # true locals: formals + assigned names

    def _local(self, name: str) -> str:
        return self.prefix + name

    def rename_expr(self, e: IR.Expr) -> IR.Expr:
        if isinstance(e, IR.Name):
            if e.name in self.subst:
                return self.subst[e.name]
            if e.name in self.bound_names:
                return IR.Name(self._local(e.name))
            return e  # free reference (module, global, sibling def, builtin)
        if isinstance(e, IR.Attribute):
            return IR.Attribute(self.rename_expr(e.value), e.attr)
        if isinstance(e, IR.Subscript):
            return IR.Subscript(self.rename_expr(e.value), self.rename_expr(e.index))
        if isinstance(e, IR.BinaryOp):
            return IR.BinaryOp(
                self.rename_expr(e.left), e.op, self.rename_expr(e.right)
            )
        if isinstance(e, IR.UnaryOp):
            return IR.UnaryOp(e.op, self.rename_expr(e.operand))
        if isinstance(e, IR.Compare):
            return IR.Compare(self.rename_expr(e.left), e.op, self.rename_expr(e.right))
        if isinstance(e, IR.BoolOp):
            return IR.BoolOp(e.op, [self.rename_expr(v) for v in e.values])
        if isinstance(e, IR.IfExpr):
            return IR.IfExpr(
                self.rename_expr(e.body),
                self.rename_expr(e.condition),
                self.rename_expr(e.orelse),
            )
        if isinstance(e, IR.Call):
            # e.func goes through the same IR.Name handling as any other
            # expression -- substituted if it's a formal, renamed if it's
            # a genuine local (e.g. a locally-assigned callable:
            # `g = helper; return g(x)`), left alone if it's a free
            # reference (`abs(u)`, `math.sin(x)`, a sibling top-level def).
            return IR.Call(self.rename_expr(e.func), [self.rename_expr(a) for a in e.args])
        if isinstance(e, IR.IntrinsicCall):
            return IR.IntrinsicCall(
                e.name, [self.rename_expr(a) for a in e.args], e.result_vt
            )
        if isinstance(e, IR.List):
            return IR.List([self.rename_expr(v) for v in e.values])
        if isinstance(e, IR.Tuple):
            return IR.Tuple([self.rename_expr(v) for v in e.values])
        return e  # Literal, RawExpr, etc.

    def rename_stmt(self, s: IR.Stmt) -> IR.Stmt | list:
        if isinstance(s, IR.Assign):
            tgt = s.target
            if isinstance(tgt, IR.Name):
                tgt = IR.Name(self._local(tgt.name))
            return IR.Assign(tgt, self.rename_expr(s.value))
        if isinstance(s, IR.Declare):
            tgt = s.target
            if isinstance(tgt, IR.Name):
                tgt = IR.Name(self._local(tgt.name))
            val = self.rename_expr(s.value) if s.value is not None else None
            return IR.Declare(tgt, s.annotation, val)
        if isinstance(s, IR.Return):
            return IR.Return(self.rename_expr(s.value))
        if isinstance(s, IR.If):
            body = _flatten_list([self.rename_stmt(c) for c in s.body])
            orelse = _flatten_list([self.rename_stmt(c) for c in s.orelse])
            return IR.If(self.rename_expr(s.condition), body, orelse)
        if isinstance(s, IR.For):
            tgt = self.rename_expr(s.target)
            body = _flatten_list([self.rename_stmt(c) for c in s.body])
            return IR.For(tgt, self.rename_expr(s.iterable), body)
        if isinstance(s, IR.ExprStmt):
            return IR.ExprStmt(self.rename_expr(s.value))
        if isinstance(s, IR.Raise):
            return IR.Raise(self.rename_expr(s.value))
        return s


def specialize_ir(fn: IR.Function, block_cfg) -> IR.Function:
    return IRSpecializer(block_cfg).specialize_function(fn)


def collect_self_fields(node: Any, out: set[str]) -> None:
    """Recursively collect names accessed as ``self.<name>`` anywhere in an IR tree.

    Used to prune a block's ``self`` struct down to the fields its
    (specialized) ``output``/``next`` IR actually reads, instead of emitting
    every non-underscore instance attribute the Python block object happens
    to carry (e.g. ``nin``/``nout``, which no block body ever reads via
    ``self.``).
    """
    if isinstance(node, IR.Attribute) and isinstance(node.value, IR.Name):
        if node.value.name == "self":
            out.add(node.attr)
            return
    if isinstance(node, IR.Node):
        for f in dataclass_fields(node):
            collect_self_fields(getattr(node, f.name), out)
    elif isinstance(node, list):
        for item in node:
            collect_self_fields(item, out)


def rename_ir_name(node: Any, old: str, replacement: "IR.Expr") -> Any:
    """Return a copy of an IR tree with every ``IR.Name(old)`` replaced by *replacement*."""
    if isinstance(node, IR.Name) and node.name == old:
        return replacement
    if isinstance(node, IR.Node):
        changes = {
            f.name: rename_ir_name(getattr(node, f.name), old, replacement)
            for f in dataclass_fields(node)
        }
        return dataclass_replace(node, **changes)
    if isinstance(node, list):
        return [rename_ir_name(item, old, replacement) for item in node]
    return node


def collect_names(node: Any, out: set[str]) -> None:
    """Recursively collect every ``IR.Name.name`` appearing anywhere in an IR tree.

    Not scope-aware (doesn't distinguish a name shadowed in a nested
    comprehension from the same name used in the enclosing scope) -- used
    only as a cheap pre-check that a rename target isn't already in use by
    something else in the same function, not as a general symbol table.
    """
    if isinstance(node, IR.Name):
        out.add(node.name)
        return
    if isinstance(node, IR.Node):
        for f in dataclass_fields(node):
            collect_names(getattr(node, f.name), out)
    elif isinstance(node, list):
        for item in node:
            collect_names(item, out)


def collect_bound_names(node: Any, out: set[str]) -> None:
    """Recursively collect every name *assigned* within an IR tree --
    ``Assign``/``Declare``/``For``/comprehension targets -- i.e. genuine
    Python-scope locals, as opposed to free references to
    globals/builtins/sibling functions.

    Unlike :func:`collect_names` (which collects every ``IR.Name``
    occurrence indiscriminately, for use as a cheap "is this name already
    taken" pre-check), this distinguishes what :class:`_IRAlphaRenamer`
    must rename -- real locals, to avoid colliding with the caller's own
    names -- from what it must leave alone: free variables such as a
    module name (``math``), a sibling helper function referenced by bare
    name, or a builtin.
    """
    if isinstance(node, IR.Assign) and isinstance(node.target, IR.Name):
        out.add(node.target.name)
    elif isinstance(node, IR.Declare) and isinstance(node.target, IR.Name):
        out.add(node.target.name)
    elif isinstance(node, IR.For) and isinstance(node.target, IR.Name):
        out.add(node.target.name)
    elif isinstance(node, IR.Comprehension) and isinstance(node.target, IR.Name):
        out.add(node.target.name)
    if isinstance(node, IR.Node):
        for f in dataclass_fields(node):
            collect_bound_names(getattr(node, f.name), out)
    elif isinstance(node, list):
        for item in node:
            collect_bound_names(item, out)


def normalize_input_param(fn: IR.Function) -> IR.Function:
    """Rewrite a lowered ``output``/``next``/``deriv`` IR.Function so its
    input-list parameter is always named ``inputs``, regardless of what the
    Python source called it.

    Every such method has the fixed shape ``(self, t, <input-list>, x)`` --
    that positional contract is enforced by the base ``Block`` class -- but
    the local spelling of the third parameter varies across the block
    library (``inputs`` in most files, ``u`` in ``sampled.py``/``spatial.py``/
    continuous ``deriv()`` overrides, and blocks defined outside this repo
    in RTB/MVTB may vary further in ways not auditable from here).
    Normalizing it here lets the rest of the pipeline keep matching the
    literal name ``"inputs"`` unchanged.

    Fails loudly rather than silently corrupting the IR if some unrelated
    local in the function body already happens to be named ``inputs`` --
    that would make this rename ambiguous (see ``collect_names``'s caveat).
    """
    param_name = fn.args[2]
    if param_name == "inputs":
        return fn
    existing_names: set[str] = set()
    collect_names(fn.body, existing_names)
    if "inputs" in existing_names:
        raise NotImplementedError(
            f"codegen: {fn.name}() already uses the name 'inputs' for "
            f"something other than its input-list parameter (named "
            f"'{param_name}' here) -- cannot normalize without ambiguity"
        )
    new_args = list(fn.args)
    new_args[2] = "inputs"
    new_body = rename_ir_name(fn.body, param_name, IR.Name("inputs"))
    return IR.Function(name=fn.name, args=new_args, body=new_body)


def substitute_state_param(fn: IR.Function) -> IR.Function:
    """Rewrite a sampled block's IR so its state parameter (position 3,
    conventionally ``x``) reads/writes ``self.state`` -- a field codegen
    synthesizes on the ``self`` struct -- instead of being passed in as an
    external parameter.

    Only ever applied when ``cfg.ndstates > 0``; continuous blocks keep
    receiving state as an external parameter, unchanged, since they're out
    of scope for this codegen effort (see the embedded codegen plan).

    Fails loudly if the function body already reads/writes a genuine
    ``self.state`` attribute of its own -- that would collide with the
    synthesized field and there's no way to tell them apart safely.
    """
    existing_self_fields: set[str] = set()
    collect_self_fields(fn.body, existing_self_fields)
    if "state" in existing_self_fields:
        raise NotImplementedError(
            f"codegen: {fn.name}() already reads/writes a 'state' field "
            f"of its own on self -- collides with the state codegen "
            f"synthesizes for sampled blocks, cannot substitute safely"
        )
    param_name = fn.args[3]
    new_body = rename_ir_name(
        fn.body, param_name, IR.Attribute(IR.Name("self"), "state")
    )
    return IR.Function(name=fn.name, args=fn.args, body=new_body)


def _eigen_matrix_literal(m: np.ndarray) -> str:
    rows, cols = m.shape
    vals = [repr(float(m[r, c])) for r in range(rows) for c in range(cols)]
    return (
        f"(Eigen::Matrix<double,{rows},{cols}>() << " + ", ".join(vals) + ").finished()"
    )


# ---------------------------------------------------------------------------
# Code emitters
# ---------------------------------------------------------------------------


class Emitter:
    """Language-neutral base class for IR-to-code emitters.

    Provides dispatcher infrastructure, shared expression/statement visitors,
    and the indent/line machinery.  Subclasses implement language-specific
    type mapping, literal rendering, and any constructs that vary by target
    language (e.g. Eigen broadcasting for C++, nalgebra for Rust).

    Each subclass populates ``INTRINSIC_IMPLS``:
        intrinsic_name -> (render_fn, helper_body_or_None)
    where ``render_fn(rendered_args: list[str]) -> str`` produces the
    target-language call expression.
    """

    INTRINSIC_IMPLS: dict[str, tuple] = {}

    def __init__(self, cfg, types: dict[str, str] | None = None) -> None:
        self.cfg = cfg
        self.extra_types = types or {}
        self._lines: list[str] = []
        self._indent = 0
        self.locals_types: dict[str, str] = {}
        self.declared_locals: set[str] = set()
        self._function_kind: str = "output"

    # ------------------------------------------------------------------
    # Line / indent machinery
    # ------------------------------------------------------------------

    def _emit(self, line: str) -> None:
        self._lines.append("    " * self._indent + line)

    def _fail(self, msg: str, node: Any = None) -> None:
        details = f" [{type(node).__name__}]" if node is not None else ""
        raise NotImplementedError(f"{type(self).__name__}: {msg}{details}")

    # ------------------------------------------------------------------
    # Dispatchers
    # ------------------------------------------------------------------

    def expr(self, e: IR.Expr) -> str:
        _ir_coverage["emit_expr"].add(type(e).__name__)
        method = getattr(self, f"expr_{type(e).__name__}", None)
        if method:
            return method(e)
        self._fail("unsupported expression", e)

    def stmt(self, s: IR.Stmt) -> None:
        _ir_coverage["emit_stmt"].add(type(s).__name__)
        method = getattr(self, f"stmt_{type(s).__name__}", None)
        if method:
            method(s)
        else:
            self._fail("unsupported statement", s)

    # ------------------------------------------------------------------
    # Shared expression visitors (language-neutral)
    # ------------------------------------------------------------------

    def expr_Name(self, e: IR.Name) -> str:
        return e.name

    def expr_Attribute(self, e: IR.Attribute) -> str:
        return f"{self.expr(e.value)}.{e.attr}"

    def expr_UnaryOp(self, e: IR.UnaryOp) -> str:
        return f"({e.op}{self.expr(e.operand)})"

    def expr_Compare(self, e: IR.Compare) -> str:
        return f"({self.expr(e.left)} {e.op} {self.expr(e.right)})"

    def expr_BoolOp(self, e: IR.BoolOp) -> str:
        joiner = " && " if e.op == "and" else " || " if e.op == "or" else None
        if joiner is None:
            self._fail(f"unsupported boolean op '{e.op}'", e)
        return "(" + joiner.join(self.expr(v) for v in e.values) + ")"

    def expr_Call(self, e: IR.Call) -> str:
        return f"{self.expr(e.func)}({', '.join(self.expr(a) for a in e.args)})"

    def expr_IntrinsicCall(self, e: IR.IntrinsicCall) -> str:
        hit = self.INTRINSIC_IMPLS.get(e.name)
        if hit is None:
            self._fail(f"no implementation for intrinsic '{e.name}'", e)
        render_fn = hit[0]
        rendered = render_fn([self.expr(a) for a in e.args])
        self._on_intrinsic_used(e.name)
        return rendered

    def _on_intrinsic_used(self, name: str) -> None:
        """Hook called when an intrinsic is rendered; subclasses track helpers."""

    def expr_RawExpr(self, e: IR.RawExpr) -> str:
        self._fail("raw expression reached emitter", e)

    # ------------------------------------------------------------------
    # Shared statement visitors (language-neutral)
    # ------------------------------------------------------------------

    def stmt_If(self, s: IR.If) -> None:
        self._emit(f"if {self.expr(s.condition)} {{")
        self._indent += 1
        for child in s.body:
            self.stmt(child)
        self._indent -= 1
        if s.orelse:
            self._emit("} else {")
            self._indent += 1
            for child in s.orelse:
                self.stmt(child)
            self._indent -= 1
        self._emit("}")

    def stmt_ExprStmt(self, s: IR.ExprStmt) -> None:
        self._emit(f"{self.expr(s.value)};")

    def stmt_RawStmt(self, s: IR.RawStmt) -> None:
        self._fail("raw statement reached emitter", s)

    # ------------------------------------------------------------------
    # Abstract interface (implement in subclass)
    # ------------------------------------------------------------------

    def vartype_to_str(self, vt: VarType) -> str:
        raise NotImplementedError

    def literal_to_str(self, value: Any) -> str:
        raise NotImplementedError

    def emit(
        self, ir: IR.Function, block_name: str, function_name: str
    ) -> tuple[str, str]:
        """Emit code for *ir*.  Returns ``(preamble, function_body)``."""
        raise NotImplementedError


def _cpp_render_minmax(op: str):
    """Render for the ``python.min``/``python.max`` intrinsics (registered
    with a wildcard signature -- see ``_reg("builtins", "min", (), ...)``
    above -- so arity isn't checked at registration time). ``std::min``/
    ``std::max`` require matching operand types, which int/float-mixed
    Python args (e.g. an int ``self.max`` clip limit against a float
    signal) won't satisfy without a cast, so both operands are promoted to
    ``double`` unconditionally rather than trying to track/match the
    narrower type."""

    def render(args: list[str]) -> str:
        if len(args) != 2:
            raise NotImplementedError(
                f"codegen: {op}() with {len(args)} arguments is not "
                f"supported (only the 2-argument scalar form is)"
            )
        a, b = args
        return f"std::{op}<double>(static_cast<double>({a}), static_cast<double>({b}))"

    return render


def _cpp_render_cast(cpp_type: str):
    """Render for a ``python.cast.<etype>`` intrinsic -- a plain
    ``static_cast<T>``. One render per C++ scalar type (from
    CppEmitter._ETYPE_MAP), shared by both a direct ``np.uint16(x)`` call
    in ordinary code and the dedicated CAST block (see
    lower_cast_block)."""

    def render(args: list[str]) -> str:
        return f"static_cast<{cpp_type}>({args[0]})"

    return render


class CppEmitter(Emitter):
    """Emit C++ code (using Eigen for matrix types) from specialized IR."""

    # VarType.dtype -> C++ type
    _SCALAR_TYPES: dict[str, str] = {
        "bool": "bool",
        "int": "int32_t",
        "float": "float",
        "str": "std::string",
        "None": "std::nullptr_t",
    }
    # ndarray VarType.etype -> C++ scalar type
    _ETYPE_MAP: dict[str, str] = {
        "float32": "float",
        "float64": "double",
        "int8": "int8_t",
        "int16": "int16_t",
        "int32": "int32_t",
        "int64": "int64_t",
        "uint8": "uint8_t",
        "uint16": "uint16_t",
        "uint32": "uint32_t",
        "uint64": "uint64_t",
        "bool": "bool",
    }
    # Python annotation string (from IR.Declare) -> C++ type
    _ANNOTATION_MAP: dict[str, str] = {
        "float": "float",
        "double": "double",
        "int": "int32_t",
        "bool": "bool",
        "str": "std::string",
    }
    # Arithmetic promotion rank for mixed-type binary ops
    _CPP_RANK: dict[str, int] = {
        "bool": 0,
        "int32_t": 1,
        "int64_t": 2,
        "float": 3,
        "double": 4,
    }

    # Intrinsic render functions and their C++ helper bodies.
    # Each entry: intrinsic_name -> (render_fn(args)->str, helper_body: str | None)
    INTRINSIC_IMPLS: dict[str, tuple] = {
        "bdsim.skew3": (
            lambda args: f"bdsim_skew3({args[0]})",
            "inline Eigen::Matrix<double,3,3> bdsim_skew3(const Eigen::Matrix<double,3,1>& v) {\n"
            "    Eigen::Matrix<double,3,3> S;\n"
            "    S <<  0,    -v(2),  v(1),\n"
            "          v(2),  0,    -v(0),\n"
            "         -v(1),  v(0),  0;\n"
            "    return S;\n"
            "}",
        ),
        "bdsim.vex3": (
            lambda args: f"bdsim_vex3({args[0]})",
            "inline Eigen::Matrix<double,3,1> bdsim_vex3(const Eigen::Matrix<double,3,3>& S) {\n"
            "    return Eigen::Matrix<double,3,1>(S(2,1), S(0,2), S(1,0));\n"
            "}",
        ),
        "bdsim.r2t": (
            lambda args: f"bdsim_r2t({args[0]})",
            "inline Eigen::Matrix<double,4,4> bdsim_r2t(const Eigen::Matrix<double,3,3>& R) {\n"
            "    Eigen::Matrix<double,4,4> T = Eigen::Matrix<double,4,4>::Identity();\n"
            "    T.block<3,3>(0,0) = R;\n"
            "    return T;\n"
            "}",
        ),
        "bdsim.t2r": (
            lambda args: f"bdsim_t2r({args[0]})",
            "inline Eigen::Matrix<double,3,3> bdsim_t2r(const Eigen::Matrix<double,4,4>& T) {\n"
            "    return T.block<3,3>(0,0);\n"
            "}",
        ),
        "bdsim.norm": (
            lambda args: f"bdsim_norm({args[0]})",
            "template<typename Derived>\n"
            "inline double bdsim_norm(const Eigen::MatrixBase<Derived>& v) { return v.norm(); }",
        ),
        "bdsim.unit": (
            lambda args: f"bdsim_unit({args[0]})",
            "template<typename Derived>\n"
            "inline auto bdsim_unit(const Eigen::MatrixBase<Derived>& v) { return v.normalized(); }",
        ),
        "bdsim.cross": (
            lambda args: f"bdsim_cross({args[0]}, {args[1]})",
            "inline Eigen::Matrix<double,3,1> bdsim_cross(\n"
            "    const Eigen::Matrix<double,3,1>& a, const Eigen::Matrix<double,3,1>& b) {\n"
            "    return a.cross(b);\n"
            "}",
        ),
        # x.item() on a size-1 Eigen vector/matrix -- linear coefficient
        # access, no helper function needed.
        "numpy.item": (lambda args: f"{args[0]}(0)", None),
        # std::min/std::max from <algorithm> -- no helper body needed.
        "python.min": (_cpp_render_minmax("min"), None),
        "python.max": (_cpp_render_minmax("max"), None),
        # std::abs from <cmath>/<cstdlib> -- overloaded for int/float/
        # double already, no cast needed (unlike min/max, only one operand
        # so there's no cross-type mismatch to resolve).
        "python.abs": (lambda args: f"std::abs({args[0]})", None),
        # math.* -- all <cmath>, already included.
        "python.math.sqrt": (lambda args: f"std::sqrt({args[0]})", None),
        "python.math.sin": (lambda args: f"std::sin({args[0]})", None),
        "python.math.cos": (lambda args: f"std::cos({args[0]})", None),
        "python.math.tan": (lambda args: f"std::tan({args[0]})", None),
        "python.math.exp": (lambda args: f"std::exp({args[0]})", None),
        "python.math.log": (lambda args: f"std::log({args[0]})", None),
        "python.math.atan2": (
            lambda args: f"std::atan2({args[0]}, {args[1]})",
            None,
        ),
        "python.math.pow": (lambda args: f"std::pow({args[0]}, {args[1]})", None),
        # math.floor()/ceil() return Python int -- cast the double result.
        "python.math.floor": (
            lambda args: f"static_cast<int32_t>(std::floor({args[0]}))",
            None,
        ),
        "python.math.ceil": (
            lambda args: f"static_cast<int32_t>(std::ceil({args[0]}))",
            None,
        ),
        # One "python.cast.<etype>" render per entry in _ETYPE_MAP above --
        # shared by a direct np.uint16(x)-style call and the CAST block.
        **{
            f"python.cast.{etype}": (_cpp_render_cast(cpp_type), None)
            for etype, cpp_type in _ETYPE_MAP.items()
        },
    }

    def __init__(
        self,
        cfg,
        types: dict[str, str] | None = None,
        default_int_type: str = "int32_t",
        default_float_type: str = "float",
    ) -> None:
        super().__init__(cfg, types)
        self._needed_helpers: set[str] = set()
        # Python-name -> current C++ identifier, for locals whose type
        # changes on reassignment (e.g. `x = x.item()`); see stmt_Assign.
        self.name_remap: dict[str, str] = {}
        self._rebind_counter: int = 0
        # Instance copy of _SCALAR_TYPES so a plain Python int/float's
        # default C++ type is configurable per emitter instance instead of
        # fixed for the whole class. Everything else (bool/str/None, and
        # ndarray element types via _ETYPE_MAP) is unaffected -- those
        # already carry explicit type information (see VarType), it's
        # only bare int/float that have no signal of their own and need
        # *some* default.
        self.scalar_types: dict[str, str] = dict(self._SCALAR_TYPES)
        self.scalar_types["int"] = default_int_type
        self.scalar_types["float"] = default_float_type
        # Pre-derive type strings from cfg so vartype_to_str is only called once.
        self._self_field_types: dict[str, str] = {
            name: self.vartype_to_str(vt) for name, (_v, vt) in cfg.self.items()
        }
        self._self_field_types.update(self.extra_types)
        self._inport_types: list[str] = [self.vartype_to_str(vt) for vt in cfg.itypes]
        self._outport_types: list[str] = [self.vartype_to_str(vt) for vt in cfg.otypes]

    # ------------------------------------------------------------------
    # Type system
    # ------------------------------------------------------------------

    def vartype_to_str(self, vt: VarType) -> str:
        if vt.dtype in self.scalar_types:
            return self.scalar_types[vt.dtype]
        if vt.dtype == "ndarray":
            if not isinstance(vt.dims, tuple):
                self._fail("ndarray VarType must have tuple dims")
            scalar = self._etype_to_cpp(vt.etype)
            if len(vt.dims) == 0:
                # A genuine NumPy scalar (np.uint16(5), ...), not an
                # array -- plain C++ scalar, no Eigen wrapper.
                return scalar
            if len(vt.dims) == 1:
                return f"Eigen::Matrix<{scalar}, {vt.dims[0]}, 1>"
            if len(vt.dims) == 2:
                return f"Eigen::Matrix<{scalar}, {vt.dims[0]}, {vt.dims[1]}>"
            self._fail("only 1D and 2D ndarray types are supported")
        self._fail(f"unsupported VarType dtype '{vt.dtype}'")

    def _etype_to_cpp(self, etype: str | None) -> str:
        if etype is None:
            self._fail("missing ndarray element type (VarType.etype)")
        cpp = self._ETYPE_MAP.get(etype)
        if cpp is None:
            self._fail(f"unsupported ndarray element type '{etype}'")
        return cpp

    def infer_expr_type(self, e: IR.Expr) -> str | None:
        """Best-effort C++ type string for *e*. Returns None if unknown."""
        if isinstance(e, IR.Name):
            if e.name == "t":
                # matches the `double t` parameter in every emitted signature
                return "double"
            return self.locals_types.get(e.name)
        if isinstance(e, IR.Attribute):
            if isinstance(e.value, IR.Name) and e.value.name == "self":
                return self._self_field_types.get(e.attr)
            return None
        if isinstance(e, IR.Subscript):
            if (
                isinstance(e.value, IR.Name)
                and e.value.name == "inputs"
                and isinstance(e.index, IR.Literal)
                and isinstance(e.index.value, int)
                and 0 <= e.index.value < len(self._inport_types)
            ):
                return self._inport_types[e.index.value]
            return None
        if isinstance(e, IR.Literal):
            if isinstance(e.value, bool):
                return "bool"
            if isinstance(e.value, int):
                return "int32_t"
            if isinstance(e.value, float):
                return "float"
            return None
        if isinstance(e, IR.UnaryOp):
            return self.infer_expr_type(e.operand)
        if isinstance(e, IR.BinaryOp):
            lt = self.infer_expr_type(e.left)
            rt = self.infer_expr_type(e.right)
            if e.op == "@":
                return lt
            if lt == rt:
                return lt
            if lt in self._CPP_RANK and rt in self._CPP_RANK:
                return lt if self._CPP_RANK[lt] >= self._CPP_RANK[rt] else rt
            _mp = "Eigen::"
            if lt is not None and lt.startswith(_mp):
                return lt
            if rt is not None and rt.startswith(_mp):
                return rt
            return None
        if isinstance(e, IR.IntrinsicCall):
            return self.vartype_to_str(e.result_vt) if e.result_vt is not None else None
        if isinstance(e, IR.Call):
            return None
        if isinstance(e, IR.Compare):
            return "bool"
        if isinstance(e, IR.BoolOp):
            return "bool"
        if isinstance(e, IR.IfExpr):
            bt = self.infer_expr_type(e.body)
            ot = self.infer_expr_type(e.orelse)
            if bt == ot:
                return bt
            if bt in self._CPP_RANK and ot in self._CPP_RANK:
                return bt if self._CPP_RANK[bt] >= self._CPP_RANK[ot] else ot
            return None
        return None

    # ------------------------------------------------------------------
    # Literal rendering
    # ------------------------------------------------------------------

    def literal_to_str(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None:
            return "nullptr"
        if isinstance(value, str):
            return json.dumps(value)
        if isinstance(value, np.generic):
            # A NumPy scalar (np.uint16(5), np.float32(1.0), ...) -- render
            # its native-Python equivalent. Checked before (int, float)
            # since e.g. np.float64 is itself a float subclass and would
            # otherwise be caught there; np.bool_ is not a bool subclass
            # (needs true/false, not Python's True/False repr).
            item = value.item()
            if isinstance(item, bool):
                return "true" if item else "false"
            return repr(item)
        if isinstance(value, (int, float)):
            return repr(value)
        if isinstance(value, np.ndarray):
            if value.ndim == 1:
                n = value.shape[0]
                vals = ", ".join(repr(float(v)) for v in value)
                return f"(Eigen::Matrix<double,{n},1>() << {vals}).finished()"
            if value.ndim == 2:
                rows, cols = value.shape
                vals = ", ".join(
                    repr(float(value[r, c])) for r in range(rows) for c in range(cols)
                )
                return f"(Eigen::Matrix<double,{rows},{cols}>() << {vals}).finished()"
            self._fail("ndarray literal must be 1D or 2D")
        self._fail("unsupported literal value")

    # ------------------------------------------------------------------
    # Expression visitors (C++ / Eigen specific)
    # ------------------------------------------------------------------

    def expr_Literal(self, e: IR.Literal) -> str:
        return self.literal_to_str(e.value)

    def expr_Name(self, e: IR.Name) -> str:
        return self.name_remap.get(e.name, e.name)

    def expr_Subscript(self, e: IR.Subscript) -> str:
        # inputs[i] → inports._i  (domain-level port convention)
        if (
            isinstance(e.value, IR.Name)
            and e.value.name == "inputs"
            and isinstance(e.index, IR.Literal)
            and isinstance(e.index.value, int)
        ):
            return f"inports._{e.index.value}"
        return f"{self.expr(e.value)}[{self.expr(e.index)}]"

    # C++'s `%` only accepts integer operands, unlike Python's -- floating
    # modulo needs fmod(). <cmath> (pulled in transitively by Eigen)
    # injects an unqualified overload into the global namespace, matching
    # this file's existing unqualified-call style (e.g. abs(), matmul()).
    _INTEGER_CPP_TYPES = {"bool", "int32_t", "int64_t"}

    def expr_BinaryOp(self, e: IR.BinaryOp) -> str:
        if e.op == "@":
            # No real matmul() helper exists -- this used to silently
            # emit a call to one anyway, producing C++ that looked fine
            # right up until compile time (an undefined `matmul`
            # symbol), discovered via PROD's own matrix branch (`prod @
            # input`, correctly isinstance-folded and reached at
            # generation time for real matrix inputs) rather than only
            # the already-tracked continuous-block case (bdsim#93). Fail
            # loudly and specifically here instead -- Eigen's own
            # Matrix::operator* already does real matrix multiplication
            # (not elementwise) for two Matrix-typed operands, so this
            # is likely cheap to actually implement later; just not
            # attempted here (out of scope -- this session's ask was the
            # scalar SUM/PROD case specifically).
            self._fail("matrix multiply (@) has no C++ implementation yet", e)
        lt = self.infer_expr_type(e.left)
        rt = self.infer_expr_type(e.right)
        if e.op == "%" and (
            lt not in self._INTEGER_CPP_TYPES or rt not in self._INTEGER_CPP_TYPES
        ):
            return f"fmod({self.expr(e.left)}, {self.expr(e.right)})"
        _mp = "Eigen::"
        lmat = lt is not None and lt.startswith(_mp)
        rmat = rt is not None and rt.startswith(_mp)
        if e.op in ("+", "-") and (lmat or rmat) and not (lmat and rmat):
            # Eigen doesn't support matrix ± scalar directly; use .array() view.
            lhs = f"{self.expr(e.left)}.array()" if lmat else self.expr(e.left)
            rhs = f"{self.expr(e.right)}.array()" if rmat else self.expr(e.right)
            return f"({lhs} {e.op} {rhs}).matrix()"
        if e.op == "*" and lmat and rmat:
            # NumPy * is element-wise; Eigen * is matmul — use .array() views.
            return (
                f"({self.expr(e.left)}.array() * {self.expr(e.right)}.array()).matrix()"
            )
        return f"({self.expr(e.left)} {e.op} {self.expr(e.right)})"

    def expr_IfExpr(self, e: IR.IfExpr) -> str:
        return f"({self.expr(e.condition)} ? {self.expr(e.body)} : {self.expr(e.orelse)})"

    def expr_Tuple(self, e: IR.Tuple) -> str:
        return "{" + ", ".join(self.expr(v) for v in e.values) + "}"

    def expr_List(self, e: IR.List) -> str:
        return "{" + ", ".join(self.expr(v) for v in e.values) + "}"

    # ------------------------------------------------------------------
    # Intrinsic helper tracking
    # ------------------------------------------------------------------

    def _on_intrinsic_used(self, name: str) -> None:
        self._needed_helpers.add(name)

    # ------------------------------------------------------------------
    # Statement visitors (C++ specific)
    # ------------------------------------------------------------------

    def stmt_Assign(self, s: IR.Assign) -> None:
        if not isinstance(s.target, IR.Name):
            self._fail("assignment target must be a simple name", s)
        py_name = s.target.name
        rhs = self.expr(s.value)  # resolves py_name under its *old* mapping

        if py_name not in self.locals_types:
            inferred = self.infer_expr_type(s.value)
            if inferred is None:
                self._fail(
                    f"cannot infer C++ type for local '{py_name}'"
                    f" (rhs is {type(s.value).__name__})",
                    s,
                )
            self.locals_types[py_name] = inferred
            self.name_remap[py_name] = py_name
            self._emit(f"{inferred} {py_name} = {rhs};")
            self.declared_locals.add(py_name)
            return

        # Already declared -- Python allows a name to change type on
        # reassignment (e.g. the `if x.size == 1: x = x.item()` idiom,
        # narrowing an ndarray to a scalar), C++ doesn't. When the new
        # type genuinely can't be assigned into the old one -- crossing
        # the Eigen-matrix/scalar boundary, or between two different
        # Eigen shapes -- declare a fresh, disambiguated C++ local
        # instead, and remap this Python name to it for the rest of the
        # function. An ordinary scalar-to-scalar difference (int32_t vs
        # float, say) is left alone: plain C++ assignment already
        # implicitly converts those, so reuse the existing declaration.
        # Also the fallback when inference can't tell at all -- treating
        # "unknown" as "unchanged" matches the previous, simpler behavior.
        inferred = self.infer_expr_type(s.value)
        cpp_name = self.name_remap.get(py_name, py_name)
        current = self.locals_types[py_name]
        needs_rebind = (
            inferred is not None
            and inferred != current
            and (inferred.startswith("Eigen::") or current.startswith("Eigen::"))
        )
        if needs_rebind:
            self._rebind_counter += 1
            cpp_name = f"{py_name}_{self._rebind_counter}"
            self.locals_types[py_name] = inferred
            self.name_remap[py_name] = cpp_name
            self._emit(f"{inferred} {cpp_name} = {rhs};")
        else:
            self._emit(f"{cpp_name} = {rhs};")

    def stmt_Declare(self, s: IR.Declare) -> None:
        if not isinstance(s.target, IR.Name):
            self._fail("declare target must be a simple name", s)
        target = s.target.name
        if s.annotation is not None:
            cpp_type = self._ANNOTATION_MAP.get(s.annotation)
            if cpp_type is None:
                self._fail(f"unsupported declare annotation '{s.annotation}'", s)
        elif s.value is not None:
            cpp_type = self.infer_expr_type(s.value)
            if cpp_type is None:
                self._fail(f"cannot infer type for declare '{target}'", s)
        else:
            self._fail(f"declare '{target}' has no annotation or value", s)
        self.locals_types[target] = cpp_type
        self.declared_locals.add(target)
        if s.value is not None:
            self._emit(f"{cpp_type} {target} = {self.expr(s.value)};")
        else:
            self._emit(f"{cpp_type} {target};")

    def stmt_Return(self, s: IR.Return) -> None:
        # next() has no output ports -- its return value is the block's
        # state for the following tick, written to self.state directly.
        if self._function_kind == "next":
            rhs = self.expr(s.value)
            state_vt = self.cfg.self.get("state", (None, None))[1]
            # A state whose real shape (from getstate0(), not a guess) is
            # exactly one element, but whose next() body returns a bare
            # scalar expression (e.g. Deriv_S.next()'s `return
            # np.array(u[0])` -- np.array()'s no-op-coercion strips down
            # to plain `u[0]`, with nothing Eigen-typed left anywhere in
            # the expression to make a direct `self.state = ...`
            # assignment type-check). Eigen has no implicit scalar ->
            # Matrix conversion, so broadcast-construct instead. Not
            # applied for a genuinely multi-element state -- that would be
            # masking a real bug, not a legitimate scalar/1-vector mixup.
            rhs_type = self.infer_expr_type(s.value)
            if (
                isinstance(state_vt, VarType)
                and state_vt.dtype == "ndarray"
                and isinstance(state_vt.dims, tuple)
                and math.prod(state_vt.dims) == 1
                and rhs_type is not None
                and not rhs_type.startswith("Eigen::")
            ):
                state_type = self._self_field_types.get("state", "")
                self._emit(f"self.state = {state_type}::Constant({rhs});")
            else:
                self._emit(f"self.state = {rhs};")
            self._emit("return;")
            return
        # Case 1: return [a, b, ...] — each element maps to one output port.
        if isinstance(s.value, IR.List):
            for i, value in enumerate(s.value.values):
                self._emit(f"outports._{i} = {self.expr(value)};")
            self._emit("return;")
            return
        # Case 2: return list(expr) — unpack a vector into N output ports.
        if (
            isinstance(s.value, IR.Call)
            and isinstance(s.value.func, IR.Name)
            and s.value.func.name == "list"
            and len(s.value.args) == 1
        ):
            cpp_expr = self.expr(s.value.args[0])
            if len(self._outport_types) == 1:
                self._emit(f"outports._0 = {cpp_expr}(0);")
            else:
                self._emit(f"auto _ret = {cpp_expr};")
                for i in range(len(self._outport_types)):
                    self._emit(f"outports._{i} = _ret({i});")
            self._emit("return;")
            return
        # Case 3: return inputs — the bare parameter itself, unmodified.
        # Only the subsystem-flattening INPORT/OUTPORT pass-through
        # blocks do this (nin == nout by construction); each port maps
        # straight across, not through an Eigen-vector index like case 2.
        if isinstance(s.value, IR.Name) and s.value.name == "inputs":
            for i in range(len(self._outport_types)):
                self._emit(f"outports._{i} = inports._{i};")
            self._emit("return;")
            return
        self._fail("return value must be a list literal or list(expr)", s)

    # ------------------------------------------------------------------
    # Struct helper
    # ------------------------------------------------------------------

    def _struct(
        self,
        name: str,
        fields: list[tuple[str, str]],
        initializers: dict[str, str] | None = None,
    ) -> list[str]:
        lines = [f"struct {name} {{"]
        for field_name, cpp_type in fields:
            init = (
                f" = {initializers[field_name]}"
                if initializers and field_name in initializers
                else ""
            )
            lines.append(f"    {cpp_type} {field_name}{init};")
        lines.append("};")
        return lines

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def emit(
        self, ir: IR.Function, block_name: str, function_name: str
    ) -> tuple[str, str]:
        """Emit C++ code for *ir*.  Returns ``(preamble, function_body)``."""
        # Reset per-emit mutable state
        self._lines = []
        self._indent = 1
        self.locals_types = {}
        self.declared_locals = set()
        self._needed_helpers = set()
        self._function_kind = function_name
        self.name_remap = {}
        self._rebind_counter = 0

        prefix = fixname(block_name)

        # Emit function body
        for s in ir.body:
            self.stmt(s)
        body_lines = list(self._lines)

        struct_lines = self._struct_defs(prefix)

        # Prepend helper bodies for any intrinsics that were used
        helper_texts = [
            self.INTRINSIC_IMPLS[name][1]
            for name in sorted(self._needed_helpers)
            if self.INTRINSIC_IMPLS.get(name, (None, None))[1] is not None
        ]
        if helper_texts:
            struct_lines = helper_texts + [""] + struct_lines

        sig_lines = self._signature_lines(prefix, function_name)
        sig_lines[-1] += " {"
        func_lines: list[str] = [*sig_lines, *body_lines, "}"]

        return "\n".join(struct_lines), "\n".join(func_lines)

    def _signature_lines(self, prefix: str, function_name: str) -> list[str]:
        """Build a stacked (one-argument-per-line) function signature,
        ending in a bare ``)`` -- shared by :meth:`emit` (which appends
        `` {``) and :meth:`emit_declaration` (which appends ``;``). The
        unstacked single-line form routinely ran past 150 columns."""
        return [
            f"void {prefix}_{function_name}(",
            "    double t,",
            "    const Eigen::VectorXd& x,",
            f"    {prefix}_self& self,",
            f"    const {prefix}_inports& inports,",
            f"    {prefix}_outports& outports",
            ")",
        ]

    def _struct_defs(self, prefix: str) -> list[str]:
        """Build the self/inports/outports struct definitions for a block
        named *prefix* -- shared by :meth:`emit` and
        :meth:`emit_declaration`, since both need identical structs
        regardless of whether a real function body follows."""
        self_initializers = {
            name: self.literal_to_str(value)
            for name, (value, _vt) in self.cfg.self.items()
            if name in self._self_field_types
        }
        return [
            *self._struct(
                f"{prefix}_self",
                list(self._self_field_types.items()),
                initializers=self_initializers,
            ),
            "",
            *self._struct(
                f"{prefix}_inports",
                [(f"_{i}", t) for i, t in enumerate(self._inport_types)],
            ),
            "",
            *self._struct(
                f"{prefix}_outports",
                [(f"_{i}", t) for i, t in enumerate(self._outport_types)],
            ),
        ]

    def emit_declaration(self, block_name: str, function_name: str) -> tuple[str, str]:
        """Emit struct definitions plus a declaration-only function
        prototype (no body) for a block whose function is never
        transpiled from Python -- used for :class:`IOBlockMixin` blocks,
        whose real implementation is hand-written C++ supplied elsewhere
        (see :class:`Codegen`'s I/O handling). Mirrors :meth:`emit`'s
        signature convention exactly, so the rest of the pipeline
        (scheduling, wiring) can call it identically either way."""
        prefix = fixname(block_name)
        struct_lines = self._struct_defs(prefix)
        sig_lines = self._signature_lines(prefix, function_name)
        sig_lines[-1] += ";"
        return "\n".join(struct_lines), "\n".join(sig_lines)


def emit_cpp(
    ir: IR.Function,
    block_name: str,
    function_name: str,
    cfg,
    types: dict[str, str] | None = None,
    default_int_type: str = "int32_t",
    default_float_type: str = "float",
) -> tuple[str, str]:
    """Backward-compatible wrapper around :class:`CppEmitter`."""
    return CppEmitter(
        cfg,
        types=types,
        default_int_type=default_int_type,
        default_float_type=default_float_type,
    ).emit(ir, block_name, function_name)


# ---------------------------------------------------------------------------
# RustEmitter  (nalgebra for fixed-size matrices)
#
# Matrix type strategy: nalgebra with statically-sized types.
#   VarType(ndarray, float64, (3,))   -> nalgebra::SVector<f64, 3>
#   VarType(ndarray, float64, (3, 3)) -> nalgebra::SMatrix<f64, 3, 3>
#   VarType(ndarray, float64, None)   -> nalgebra::DMatrix<f64>  (fallback)
#
# Key operation differences vs C++/Eigen:
#   matmul  @   -> *        (nalgebra overloads Mul for matrix product)
#   elem *      -> .component_mul(&rhs)
#   broadcast + -> .add_scalar(x)
#   broadcast * -> x * mat  (scalar on left, std::ops::Mul trait)
#   cross       -> .cross(&v)  (nalgebra method, 3-vectors only)
#   norm        -> .norm()
#   normalize   -> .normalize()
#
# Cargo.toml dependency:  nalgebra = "0.33"
# ---------------------------------------------------------------------------
class RustEmitter(Emitter):
    """Emit Rust code (using nalgebra for matrix/vector types) from specialized IR.

    STATUS: stub — ``vartype_to_str``, ``literal_to_str``, type tables all done.
    Still needed: ``expr_BinaryOp``, ``stmt_Assign``, ``stmt_Declare``,
    ``stmt_Return``, and ``emit()``.  Follow :class:`CppEmitter` as the template.

    Key operation differences to encode in ``expr_BinaryOp``:
      Python @  (matmul)      ->  a * b            (nalgebra Mul trait)
      Python *  (elem-wise)   ->  a.component_mul(&b)
      matrix ± scalar         ->  a.add_scalar(s) / a.add_scalar(-s)
      scalar * matrix         ->  s * a            (scalar on left)
      matrix norm             ->  a.norm()         (-> bdsim.norm intrinsic)
      matrix normalize        ->  a.normalize()    (-> bdsim.unit intrinsic)
      cross product           ->  a.cross(&b)      (-> bdsim.cross intrinsic)

    ``stmt_Assign`` notes:
      - Use ``let mut name: Type = rhs;`` for first use, bare ``name = rhs;`` after.
      - Track declared locals in ``self.declared_locals`` (same as CppEmitter).
      - nalgebra types are ``Copy`` for small fixed-size matrices, so plain
        assignment is fine (no memcpy needed unlike C).

    ``stmt_Return`` notes:
      - Rust uses structs for outports, same approach as C++.
      - Return statement: ``outports._0 = expr; return;``

    ``emit()`` must: reset state, iterate ``ir.body`` calling ``self.stmt()``,
    collect helper bodies from ``INTRINSIC_IMPLS``, then build and return
    ``(preamble_str, function_str)``.
    Struct definition syntax:  ``struct Name { field: Type, }``
    Function signature:  ``fn prefix_output(t: f64, self_: &mut PrefixSelf,
                              inports: &PrefixInports, outports: &mut PrefixOutports)``
    """

    # VarType.dtype -> Rust scalar type
    _SCALAR_TYPES: dict[str, str] = {
        "bool": "bool",
        "int": "i32",
        "float": "f64",
        "str": "String",
        "None": "()",
    }
    # ndarray VarType.etype -> Rust scalar type
    _ETYPE_MAP: dict[str, str] = {
        "float32": "f32",
        "float64": "f64",
        "int32": "i32",
        "int64": "i64",
        "bool": "bool",
    }
    # Arithmetic promotion rank (mirrors _CPP_RANK)
    _RUST_RANK: dict[str, int] = {
        "bool": 0,
        "i32": 1,
        "i64": 2,
        "f32": 3,
        "f64": 4,
    }

    # TODO: populate with nalgebra equivalents of each C++ intrinsic helper.
    # Each entry: intrinsic_name -> (render_fn(args)->str, helper_body: str | None)
    # nalgebra already provides many operations as methods so helper bodies
    # may not be needed (pass None).  Example:
    #   "bdsim.skew3": (lambda args: f"bdsim_skew3(&{args[0]})", "fn bdsim_skew3(...) {{ ... }}")
    INTRINSIC_IMPLS: dict[str, tuple] = {}

    def vartype_to_str(self, vt: VarType) -> str:
        """Convert a :class:`VarType` to a Rust type string."""
        if vt.dtype == "ndarray":
            et = self._ETYPE_MAP.get(vt.etype or "float64", "f64")
            dims = vt.dims
            if dims is None:
                return f"nalgebra::DMatrix<{et}>"
            if isinstance(dims, int):
                return f"nalgebra::SVector<{et}, {dims}>"
            if isinstance(dims, tuple):
                if len(dims) == 1:
                    return f"nalgebra::SVector<{et}, {dims[0]}>"
                if len(dims) == 2:
                    return f"nalgebra::SMatrix<{et}, {dims[0]}, {dims[1]}>"
            self._fail(f"unsupported ndarray dims={dims!r}")
        return self._SCALAR_TYPES.get(vt.dtype, vt.dtype)

    def literal_to_str(self, lit: "IR.Literal", target_type: str | None = None) -> str:
        """Render a literal value as a Rust expression."""
        val = lit.value
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, int):
            return f"{val}_i32"
        if isinstance(val, float):
            # Rust requires explicit float syntax
            s = repr(val)
            return s if "." in s or "e" in s else s + ".0"
        if isinstance(val, np.ndarray):
            # TODO: emit nalgebra matrix/vector literal
            # e.g. SVector::<f64,3>::new(1.0, 2.0, 3.0)
            #   or SMatrix::<f64,2,2>::from_row_slice(&[1.0, 0.0, 0.0, 1.0])
            raise NotImplementedError(
                "RustEmitter: ndarray literal not yet implemented"
            )
        if val is None:
            return "()"
        return repr(val)

    def emit(
        self, ir: "IR.Function", block_name: str, function_name: str
    ) -> tuple[str, str]:
        """Emit Rust code for *ir*.  Returns ``(preamble, function_body)``.

        Implementation skeleton (mirrors CppEmitter.emit exactly):

            self._lines = []; self._indent = 1
            self.locals_types = {}; self.declared_locals = set()
            self._needed_helpers = set()          # add this in __init__ too

            prefix = fixname(block_name)
            for s in ir.body: self.stmt(s)
            body_lines = list(self._lines)

            # Build Rust struct strings
            # struct {prefix}_Self  {{ field: Type, ... }}
            # struct {prefix}_Inports  {{ _0: Type, ... }}
            # struct {prefix}_Outports {{ _0: Type, ... }}

            # Prepend helper fn bodies for used intrinsics
            helper_texts = [self.INTRINSIC_IMPLS[n][1]
                            for n in sorted(self._needed_helpers)
                            if self.INTRINSIC_IMPLS.get(n,(None,None))[1]]

            func_lines = [
                f"fn {prefix}_{function_name}(t: f64, x: &[f64], "
                f"self_: &mut {prefix}Self, "
                f"inports: &{prefix}Inports, outports: &mut {prefix}Outports) {{",
                *body_lines, "}",
            ]
            return preamble_str, "\\n".join(func_lines)
        """
        raise NotImplementedError(
            "RustEmitter.emit() is not yet implemented. "
            "See docstring above for the step-by-step implementation plan."
        )


# ---------------------------------------------------------------------------
# CEmitter  (custom flat-array structs, zero external dependencies)
#
# Matrix type strategy: generated typedef + helper functions per (R,C) size.
#   VarType(ndarray, float64, (3,))   -> bdsim_vec3_t   (typedef double[3])
#   VarType(ndarray, float64, (3, 3)) -> bdsim_mat3x3_t (typedef double[9], row-major)
#   VarType(ndarray, float64, None)   -> double *        (fallback, caller manages size)
#
# Design rationale:
#   - Zero external dependencies (no GSL, no BLAS required)
#   - Sizes known at specialization time, so we generate one-shot inline helpers
#   - Row-major layout matches numpy / C conventions
#   - For large (>4x4) matrices or dynamic sizes, add optional CBLAS fallback
#
# Each matrix operation (add, mul, scale, etc.) becomes an emitted inline
# helper function keyed on the concrete size, e.g.:
#   static inline void bdsim_madd_3x3(const double* a, const double* b, double* out);
#   static inline void bdsim_mmul_3x3_3x1(const double* m, const double* v, double* out);
#
# Required headers:  <stdint.h>  <stdbool.h>  <string.h>  (optionally <math.h>)
# ---------------------------------------------------------------------------
class CEmitter(Emitter):
    """Emit C99 code (flat-array matrix structs, no external dependencies) from specialized IR.

    STATUS: stub — ``vartype_to_str``, ``literal_to_str``, ``_mat_typedef``,
    type tables all done.  Still needed: ``expr_BinaryOp``, ``stmt_Assign``,
    ``stmt_Declare``, ``stmt_Return``, and ``emit()``.

    Key differences from CppEmitter to encode:

    ``expr_BinaryOp``:
      C has NO operator overloading.  Every matrix op becomes a helper call.
      Accumulate needed helpers in ``self._needed_helpers`` (set of str tags
      like ``"madd_3x3"``).  Each tag maps to a generated ``static inline``
      function body stored in a second dict ``_MATRIX_OP_HELPERS``, keyed by
      the same tag.  Suggested helpers to generate on demand:
        bdsim_madd_{R}x{C}   add two RxC matrices
        bdsim_msub_{R}x{C}   subtract
        bdsim_mscale_{R}x{C} scale by scalar
        bdsim_mmul_{R}x{C}_{C}x{K}  matmul
        bdsim_mcopy_{R}x{C}  memcpy wrapper

    ``stmt_Assign``:
      - First use:  emit ``bdsim_vec3_t name;`` then ``bdsim_mcopy_3x1(rhs, name);``
      - Re-use:     just ``bdsim_mcopy_3x1(rhs, name);``
      - Scalar:     ``double name = rhs;`` / ``name = rhs;`` (normal C)

    ``stmt_Declare``:
      - Always emits the typedef + optionally memcpy-initializes.

    ``stmt_Return``:
      - For each output: ``bdsim_mcopy_{dims}(expr, outports._0);``

    ``emit()``:
      - Same reset/iterate/collect pattern as CppEmitter.
      - Typedef definitions (``typedef double bdsim_vec3_t[3];``) go at top
        of preamble, generated from seen VarTypes.
      - Inline helper bodies follow typedefs.
      - Struct definitions use C99 syntax::
          typedef struct { bdsim_vec3_t _0; } prefix_Inports;
      - Function signature::
          void prefix_output(double t, const double* x,
              prefix_Self* self, const prefix_Inports* inports,
              prefix_Outports* outports)
    """

    # VarType.dtype -> C99 type
    _SCALAR_TYPES: dict[str, str] = {
        "bool": "bool",  # <stdbool.h>
        "int": "int32_t",  # <stdint.h>
        "float": "double",
        "str": "const char*",
        "None": "void*",
    }
    # ndarray VarType.etype -> C scalar type
    _ETYPE_MAP: dict[str, str] = {
        "float32": "float",
        "float64": "double",
        "int32": "int32_t",
        "int64": "int64_t",
        "bool": "bool",
    }

    # TODO: populate with C helper-function call renderers.
    # intrinsic_name -> (render_fn(args)->str, helper_body: str | None)
    # Example:
    #   "bdsim.skew3": (
    #       lambda args: f"bdsim_skew3({args[0]}, _tmp_skew)",
    #       "static inline void bdsim_skew3(const double* v, double* out) { ... }")
    INTRINSIC_IMPLS: dict[str, tuple] = {}

    def _mat_typedef(self, dims: int | tuple) -> str:
        """Return the C typedef name for a matrix/vector with the given dims."""
        if isinstance(dims, int) or (isinstance(dims, tuple) and len(dims) == 1):
            n = dims if isinstance(dims, int) else dims[0]
            return f"bdsim_vec{n}_t"
        if isinstance(dims, tuple) and len(dims) == 2:
            return f"bdsim_mat{dims[0]}x{dims[1]}_t"
        return "double*"

    def vartype_to_str(self, vt: VarType) -> str:
        """Convert a :class:`VarType` to a C99 type string."""
        if vt.dtype == "ndarray":
            if vt.dims is None:
                et = self._ETYPE_MAP.get(vt.etype or "float64", "double")
                return f"{et}*"
            return self._mat_typedef(vt.dims)
        return self._SCALAR_TYPES.get(vt.dtype, vt.dtype)

    def literal_to_str(self, lit: "IR.Literal", target_type: str | None = None) -> str:
        """Render a literal value as a C99 expression."""
        val = lit.value
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, int):
            return f"{val}"
        if isinstance(val, float):
            s = repr(val)
            # C float literals need explicit suffix or decimal point
            return s if "." in s or "e" in s else s + ".0"
        if isinstance(val, np.ndarray):
            # TODO: emit a compound literal or a static initializer
            # e.g. (bdsim_mat3x3_t){{1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0}}
            raise NotImplementedError("CEmitter: ndarray literal not yet implemented")
        if val is None:
            return "NULL"
        return repr(val)

    def emit(
        self, ir: "IR.Function", block_name: str, function_name: str
    ) -> tuple[str, str]:
        """Emit C99 code for *ir*.  Returns ``(preamble, function_body)``.

        Implementation skeleton:

            self._lines = []; self._indent = 1
            self.locals_types = {}; self.declared_locals = set()
            self._needed_helpers: set[str] = set()   # op tags, e.g. "madd_3x3"
            self._seen_typedefs: set[str] = set()    # typedef names already emitted

            prefix = fixname(block_name)
            for s in ir.body: self.stmt(s)
            body_lines = list(self._lines)

            # 1. Emit typedefs for all seen matrix dims
            # 2. Emit static inline helper bodies (_MATRIX_OP_HELPERS[tag])
            # 3. Emit intrinsic helper bodies from INTRINSIC_IMPLS
            # 4. Emit typedef struct blocks for self/inports/outports
            # 5. Emit function
        """
        raise NotImplementedError(
            "CEmitter.emit() is not yet implemented. "
            "See docstring above for the step-by-step implementation plan."
        )


from typing import NamedTuple
from types import SimpleNamespace


def fixname(name: str) -> str:
    # replace all non-alphanumeric characters with underscores
    return "".join(c if c.isalnum() else "_" for c in name)


class Codegen:
    """Orchestrates C++ code generation for a compiled :class:`BlockDiagram`.

    Kept as its own class, separate from ``BlockDiagram`` itself: codegen
    is a heavyweight, still-experimental feature with its own dependencies
    (``ast``, ``inspect``) that most bdsim users don't need pulled into
    the core simulator's API surface. An instance holds generation
    options; construct one per configuration and call :meth:`generate`
    once per diagram.

    ``generate()`` itself is language-independent: it walks the diagram,
    lowers each block's Python source to IR, and specializes it -- none
    of that varies by target language. Only the *scaffolding* text around
    the per-block struct/function definitions (which already go through
    :class:`Emitter`) is C++-specific: includes, instance declarations,
    the wiring-assignment statement, the ``bdsim_tick()``/``bdsim_init()``
    function syntax. Each such piece is its own small ``_*`` method below
    rather than inline ``fp.write(...)`` calls, so a future
    ``CodegenRust(Codegen)`` for a second target only needs to override
    those methods, not re-read and rewrite ``generate()``.

    Precedent for this split: ``sympy.utilities.codegen`` -- ``CodeGen``
    holds the shared, language-independent ``routine()``/``write()``
    logic; ``CCodeGen``/``FCodeGen`` subclasses override hook methods for
    exactly this kind of scaffolding (``_preprocessor_statements``,
    ``_declare_arguments``, ``get_prototype``, ``dump_c``/``dump_h``),
    while a separately-delegated ``CodePrinter`` (``CCodePrinter``, ...)
    handles per-expression rendering -- the same role :class:`Emitter`
    already plays here. Not yet split into an abstract ``Codegen`` base
    plus a concrete ``CodegenCpp``: with only one real target there's
    nothing to distinguish it from yet, and inventing that split before a
    second implementation exists to validate it against would be
    guessing at the boundary rather than knowing it.

    :param keep_fields: block name -> field names to always keep in that
        block's ``self`` struct, even if unused by ``output()``/``next()``
        (e.g. fields exposed for telemetry or live parameter tuning).
    :param default_int_type: C++ type a plain Python ``int`` maps to when
        it carries no more specific type information of its own. A
        NumPy-typed value (e.g. ``np.uint16(5)``, or an ``ndarray`` with
        an explicit ``dtype``) is unaffected -- it always keeps its own
        explicit width regardless of this default.
    :param default_float_type: as above, for a plain Python ``float``.
    :param max_inline_depth: how many levels deep a chain of nested
        (non-recursive) helper-function calls gets inlined before codegen
        gives up and fails loudly, rather than silently emitting a call
        to an undefined C++ symbol. True recursion is caught separately
        and unconditionally (see ``IRInliner._stack``); this is purely a
        bound on legitimate but very deep non-cyclic call chains.
    :param output_path: where to write the generated C++.
    :param verbose: print each block's config, raw/specialized IR, and
        schedule as ``generate()`` runs -- useful when debugging a
        lowering/specialization problem, off by default since it dumps a
        lot of text (including, for a block whose callable's module
        carries the ordinary Python ``__builtins__`` reference in its
        ``__globals__``, the interactive-shell ``copyright``/``credits``/
        ``license`` objects' multi-paragraph ``__repr__`` text -- harmless
        but genuinely hard to read through).
    """

    def __init__(
        self,
        keep_fields: dict[str, set[str]] | None = None,
        default_int_type: str = "int32_t",
        default_float_type: str = "float",
        max_inline_depth: int = 20,
        output_path: str = "codegen.cpp",
        verbose: bool = False,
    ) -> None:
        self.keep_fields = keep_fields or {}
        self.default_int_type = default_int_type
        self.default_float_type = default_float_type
        self.max_inline_depth = max_inline_depth
        self.output_path = output_path
        self.verbose = verbose

    def _log(self, *args: Any) -> None:
        if self.verbose:
            print(*args)

    def _block_cfg(self, block):
        itypes = []
        try:
            for i in range(block.nin):
                itypes.append(VarType(block.inport_value(i)))
        except AttributeError:
            pass

        otypes = []
        try:
            for i in range(block.nout):
                otypes.append(VarType(block.outport_value(i)))
        except AttributeError:
            pass

        _self = {}
        for name, value in block.__dict__.items():
            if name.startswith("_"):
                continue
            try:
                vt = VarType(value)
            except ValueError:
                # Not representable as struct-field data -- e.g. FUNCTION
                # blocks' self.func (a callable) or self.kwargs (a dict).
                # Call-mechanics bookkeeping, not real block state; a call
                # to it is a lowering/inlining concern (IRInliner), not
                # something to store a value for. If the specialized IR
                # ends up genuinely needing it, collect_self_fields'
                # pruning step will never pick it back up (it's not in
                # _self at all) and specialization will surface that as
                # its own clear failure, rather than crashing here on
                # every block that merely happens to carry one.
                continue
            # print(f"  {name}: {value} ({type(value)})")
            _self[name] = (value, vt)

        # type (not value) of the synthesized self.state field, for sampled
        # blocks -- lets the specializer fold isinstance()/.ndim/.size on
        # state without ever seeing its (runtime-only) concrete value
        state_vt = VarType(block.getstate0()) if block.ndstates > 0 else None

        # Fallback name-resolution namespace: the module a FUNCTION block's
        # callable (or, for an ordinary block, its output() method) was
        # itself defined in -- lets a sibling helper function referenced
        # by bare name resolve for inlining. See IRSpecializer.extra_globals.
        # getattr(..., None), not direct attribute access -- called for
        # every block, including sink blocks (e.g. SCOPE) that have no
        # output() at all; this runs before generate()'s nout==0 skip.
        top_level_callable = getattr(block, "func", None) or getattr(
            block, "output", None
        )
        extra_globals = getattr(top_level_callable, "__globals__", None) or {}

        return SimpleNamespace(
            block=block,
            nin=block.nin,
            nout=block.nout,
            nstates=block.nstates,
            ndstates=block.ndstates,
            itypes=itypes,
            otypes=otypes,
            self=_self,
            state_vt=state_vt,
            max_inline_depth=self.max_inline_depth,
            extra_globals=extra_globals,
        )

    # ------------------------------------------------------------------
    # Target-language scaffolding hooks (C++ here). Override every one of
    # these for a different target. Each returns text for generate() to
    # write, rather than writing to a file itself -- matches how
    # CppEmitter's own methods work elsewhere in this file, and keeps
    # each hook independently testable without a real file.
    # ------------------------------------------------------------------

    def _file_header_comment(self) -> str:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # sys.argv[0] is the script Python was invoked with -- absolute-
        # pathed so the source is unambiguous regardless of what cwd this
        # ran from. Falls back gracefully for -c/REPL/notebook use, where
        # it's empty or not a real script path; still worth trying, since
        # the common case (`python some_diagram.py`) is exactly what this
        # is for -- without it, regenerating from a *different* script
        # into the same output path (a real mix-up this session) leaves
        # no trace of which diagram actually produced this file.
        source = os.path.abspath(sys.argv[0]) if sys.argv[0] else None
        source_line = (
            f"// Source: {source}\n" if source else "// Source: (interactive session -- no script path)\n"
        )
        return (
            "//============================================================\n"
            f"// Generated by bdsim.codegen on {timestamp}\n"
            f"{source_line}"
            "// Do not hand-edit -- regenerated from the Python diagram\n"
            "// description; changes here will be overwritten.\n"
            "//============================================================\n\n"
        )

    def _preamble(self) -> str:
        return (
            "#include <algorithm>\n#include <cstdint>\n#include <cmath>\n"
            "#include <string>\n#include <Eigen/Dense>\n\n"
        )

    _SEPARATOR_WIDTH = 60

    def _block_header_comment(self, block_name: str, block_type: str) -> str:
        bar = "=" * self._SEPARATOR_WIDTH
        return f"//{bar}\n//  {block_type.upper()} ({block_name})\n//{bar}\n"

    def _shared_state_decl(self) -> str:
        # A single shared (always-empty) state vector, purely to satisfy
        # the existing `const Eigen::VectorXd& x` parameter every
        # function still carries -- unused by any sampled block now that
        # state lives on self.state; kept only for signature
        # compatibility with the (currently out-of-scope) continuous-
        # block path.
        return "static Eigen::VectorXd g_x;\n"

    def _instance_decls(self, name: str) -> str:
        return (
            f"static {name}_self {name}_self_inst;\n"
            f"static {name}_inports {name}_inports_inst;\n"
            f"static {name}_outports {name}_outports_inst;\n"
        )

    def _init_function(self) -> str:
        return "\nvoid bdsim_init() {\n}\n"

    def _tick_function_open(self) -> str:
        # Wraps the schedule/wiring/state-update sequence as a single
        # function that runs one tick of the (single-clock, v1) polling
        # loop -- see the "Runtime loop shape" section of the embedded
        # codegen plan.
        return "\nvoid bdsim_tick(double t) {\n"

    def _tick_function_close(self) -> str:
        return "}\n"

    def _schedule_group_comment(self, sequence: int) -> str:
        return f"\n    /****** Schedule group {sequence} *******/\n"

    def _output_call(self, name: str) -> str:
        return (
            f"    {name}_output(t, g_x, {name}_self_inst, "
            f"{name}_inports_inst, {name}_outports_inst);\n"
        )

    def _wire_assignment(
        self,
        dest_name: str,
        dest_port: int,
        src_name: str,
        src_port: int,
        dest_label: str,
        src_label: str,
    ) -> str:
        # Push-based: called right after src_name's output() call, for
        # every one of its connected destinations -- mirrors how the real
        # bdsim runtime propagates values (Block._publish_output_values),
        # and is the only ordering that's correct in general: a non-
        # feedthrough stateful block (e.g. an integrator) is scheduled
        # independent of its input's readiness (its output only reads
        # self.state), so it can land in an earlier sequence group than
        # the block that produces its input -- but its inport still
        # needs this tick's value before the state-update pass runs.
        # Reading from the destination's own sequence slot instead (the
        # original approach) got this wrong: it either never wired
        # sequence-0 blocks' inputs at all, or would have read a stale,
        # one-tick-old value had it tried.
        return (
            f"    {dest_name}_inports_inst._{dest_port} = "
            f"{src_name}_outports_inst._{src_port};"
            f"  // {dest_label}[{dest_port}] <-- {src_label}[{src_port}]\n"
        )

    def _state_update_header(self) -> str:
        # advance state for every clocked block, from this tick's now-
        # current (already wired) inputs. Must run after every output()
        # above -- next() writes self.state directly and in place, and
        # it's safe to do so unconditionally here since no block ever
        # reads another block's state, only its own.
        #
        # Skipped on the very first tick -- matches bdsim's own real
        # clock semantics, confirmed by cross-checking generated output
        # numerically against bdsim's Python simulator (see the embedded
        # codegen plan): Clock.tick starts at 1, so the clock's first
        # scheduled event fires at t=T, not t=0 -- there's an implicit
        # free "tick 0" (the initial-condition sample) that never
        # triggers a state update. At t=T, output() still reads the
        # untouched initial state; only from t=2T does a block's output
        # reflect its first next() call. Translated to this polling
        # model (one bdsim_tick() call = one clock period, called
        # starting at t=0): the first call is that free IC sample, so
        # its next() pass doesn't run either.
        return (
            "\n    /****** State update (next) *******/\n"
            "    static bool first_tick = true;\n"
            "    if (!first_tick) {\n"
        )

    def _next_call(self, name: str) -> str:
        return (
            f"        {name}_next(t, g_x, {name}_self_inst, "
            f"{name}_inports_inst, {name}_outports_inst);\n"
        )

    def _state_update_footer(self) -> str:
        return "    }\n    first_tick = false;\n"

    def generate(self, bd) -> None:
        """Generate C++ code for compiled block diagram *bd*."""
        printer = IRPrettyPrinter()

        fp = open(self.output_path, "w")
        fp.write(self._file_header_comment())
        fp.write(self._preamble())
        emitted_blocks: list[str] = []
        for block in bd.blocklist:

            cfg = self._block_cfg(block)
            # Captured once, before the isinstance() check below narrows
            # the static type of `block` for the rest of this iteration
            # (IOBlockMixin, a bare mixin unrelated to Block in the type
            # system, would otherwise make `block.name`/`.type` look
            # unknown to the type checker after the narrowing).
            block_name = block.name
            block_type = block.type
            is_io = isinstance(block, IOBlockMixin)

            if cfg.nout == 0 and not is_io:
                # sink block (e.g. SCOPE) -- no C++ meaning, nothing to
                # generate. An I/O sink (DigitalOut/PWMOut/DeviceOut/...)
                # still needs a struct + declaration, handled below.
                continue
            self._log(f"====================================================== {block_name}")
            self._log(cfg)

            if is_io:
                # I/O blocks' Python output()/step() is a Python-simulator-
                # only stand-in (a settable sim value), never transpiled --
                # the real implementation is hand-written C++ supplied
                # elsewhere (see the I/O handling section of the embedded
                # codegen plan). Keep only fields the block class itself
                # registered via add_param() (block._parameters) -- the
                # existing bdsim convention for "this is genuine, user-
                # facing configuration" (e.g. channel/device/freq), used
                # elsewhere for live parameter tuning too. Everything else
                # on self -- generic Block bookkeeping like nin/nout, and
                # simulator-only sim_value(s) -- was never meant for a
                # hand-written C++ body and would otherwise show up as
                # dead struct fields with no meaning there.
                keep = set(block._parameters.keys())  # noqa: SLF001
                cfg.self = {k: v for k, v in cfg.self.items() if k in keep}
                s, f = CppEmitter(
                    cfg,
                    default_int_type=self.default_int_type,
                    default_float_type=self.default_float_type,
                ).emit_declaration(block_name, "output")
                fp.write(self._block_header_comment(block_name, block_type))
                fp.write(s + "\n\n" + f + "\n\n")
                emitted_blocks.append(fixname(block_name))
                continue

            # block_type was already captured earlier in this iteration
            # (for the block-separator comment) -- same value, reused
            # here rather than recomputed.
            if block_type == "function":
                method_ir = lower_function_block(cfg.block)
            elif block_type == "cast":
                method_ir = lower_cast_block(cfg.block)
            else:
                method_ir = lower_block_method(cfg.block.output, cfg)
            method_ir = normalize_input_param(method_ir)
            if cfg.ndstates > 0:
                method_ir = substitute_state_param(method_ir)
            self._log("--- raw IR")
            self._log(printer.format(method_ir))
            self._log("--- specialized IR")
            spec_ir = specialize_ir(method_ir, cfg)
            self._log(printer.format(spec_ir))

            # sampled (clocked) blocks also get a next() function, computing
            # their state for the following tick from this tick's inputs
            next_spec_ir = None
            if cfg.ndstates > 0:
                next_ir = lower_block_method(cfg.block.next, cfg)
                next_ir = normalize_input_param(next_ir)
                next_ir = substitute_state_param(next_ir)
                self._log("--- next specialized IR")
                next_spec_ir = specialize_ir(next_ir, cfg)
                self._log(printer.format(next_spec_ir))

            # prune the self struct to fields the specialized IR (output and,
            # if present, next) actually reads, plus any explicitly requested
            # via keep_fields (e.g. for telemetry/live tuning, which by
            # definition aren't read here)
            used_self_fields: set[str] = set()
            collect_self_fields(spec_ir, used_self_fields)
            if next_spec_ir is not None:
                collect_self_fields(next_spec_ir, used_self_fields)
            used_self_fields |= self.keep_fields.get(block_name, set())

            # state is synthesized, not a real block.__dict__ attribute -- add
            # it to cfg.self (typed/initialized from getstate0()) only now,
            # after specialization, so it never gets constant-folded away
            if cfg.ndstates > 0 and "state" in used_self_fields:
                state0 = cfg.block.getstate0()
                cfg.self["state"] = (state0, VarType(state0))

            cfg.self = {k: v for k, v in cfg.self.items() if k in used_self_fields}

            self._log("--- emitted C++")
            s, f = emit_cpp(
                spec_ir,
                block_name,
                "output",
                cfg,
                default_int_type=self.default_int_type,
                default_float_type=self.default_float_type,
            )
            fp.write(self._block_header_comment(block_name, block_type))
            fp.write(s + "\n\n" + f + "\n\n")

            if next_spec_ir is not None:
                # struct definitions already written above; only the function body
                _, next_f = emit_cpp(
                    next_spec_ir,
                    block_name,
                    "next",
                    cfg,
                    default_int_type=self.default_int_type,
                    default_float_type=self.default_float_type,
                )
                fp.write(next_f + "\n\n")

            emitted_blocks.append(fixname(block_name))

        fp.write("\n\n/****** Block instances *******/\n")
        fp.write(self._shared_state_decl())
        for name in emitted_blocks:
            fp.write(self._instance_decls(name))

        fp.write(self._init_function())
        fp.write(self._tick_function_open())

        emitted_block_set = set(emitted_blocks)
        called_blocks: set[str] = set()
        for sequence, group in enumerate(bd.plan):
            fp.write(self._schedule_group_comment(sequence))
            for b in group:
                self._log(f"Schedule {b.name} at sequence {sequence}")
                name = fixname(b.name)

                fp.write(self._output_call(name))
                called_blocks.add(name)

                for port in range(b.nout):
                    for wire in b._output_wires[port]:  # noqa: SLF001 -- no public accessor
                        dest_block = wire.end.block
                        dest_name = fixname(dest_block.name or "")
                        if dest_name not in emitted_block_set:
                            # sink block (e.g. SCOPE) -- no struct/instance
                            # generated for it yet, see the I/O handling
                            # section of the embedded codegen plan
                            continue
                        fp.write(
                            self._wire_assignment(
                                dest_name,
                                wire.end.port,
                                name,
                                port,
                                dest_block.name,
                                b.name,
                            )
                        )

        # bd.plan deliberately excludes every sink/graphics-classed block
        # (BlockDiagram.schedule_generate() assigns them a _sequence for
        # ordering purposes, then removes them from the group that
        # actually gets appended to plan) -- bdsim's own Python engine
        # calls them separately, via BlockDiagram.step() ("called at the
        # end of every integration interval"), not through plan/evaluate()
        # at all. An I/O sink (DigitalOut/PWMOut/DeviceOut/...) needs the
        # same treatment here: its struct+declaration were emitted above
        # and its inputs get wired above (as a wiring *destination*, via
        # the loop just above), but nothing yet calls its own
        # {name}_output() -- without this, a real, correctly-wired
        # hand-written implementation would still just never run.
        io_sink_blocks = [
            b
            for b in bd.blocklist
            if isinstance(b, IOBlockMixin)
            and b.nout == 0
            and fixname(b.name) not in called_blocks
        ]
        if io_sink_blocks:
            fp.write("\n    /****** I/O sink outputs (not in bd.plan) *******/\n")
            for b in io_sink_blocks:
                fp.write(self._output_call(fixname(b.name)))

        stateful_blocks = [b for b in bd.blocklist if b.ndstates > 0]
        if stateful_blocks:
            fp.write(self._state_update_header())
            for b in stateful_blocks:
                fp.write(self._next_call(fixname(b.name)))
            fp.write(self._state_update_footer())

        fp.write(self._tick_function_close())
        fp.close()
        # Always printed, regardless of `verbose` -- confirms generate()
        # actually ran and points at the file, without dumping the
        # per-block trace. Easy to miss otherwise: the file just changes
        # on disk with no signal in the terminal that anything happened,
        # or where to look (e.g. wiring lines buried at the end of a
        # long bdsim_tick(), not obviously findable by scrolling).
        print(f"Generated C++ code -> {os.path.abspath(self.output_path)}")




# TODO:
# - redo scheduler for multi-clock systems
# - add time groups
# - pass appropriate bits of state vector to each function, not the whole x
#   (moot for sampled blocks now that state lives on self; still applies to
#   continuous blocks, out of scope for this codegen effort)

def ir_coverage_report() -> tuple[str, bool]:
    """Return (report, raw_hit) summarizing which IR node types have been
    exercised, across every ``specialize_ir()``/``emit_cpp()`` call made
    in this process so far -- coverage accumulates in the module-level
    ``_ir_coverage`` dict across multiple diagrams/calls; use
    :func:`reset_ir_coverage` first to scope a report to just one.

    ``raw_hit`` is ``True`` if ``RawStmt``/``RawExpr`` was hit in any
    phase -- the one row that's a genuine warning, not just informational:
    it means some Python construct fell through ``MethodFrontend``'s
    per-node handling into the untyped fallback, i.e. real frontend
    coverage is missing for whatever produced it.
    """
    col_w = 20
    phases = ["spec_stmt", "spec_expr", "emit_stmt", "emit_expr"]
    header = f"{'node type':<{col_w}}" + "".join(f"  {p:<{col_w}}" for p in phases)
    lines = [header, "-" * len(header)]
    raw_hit = False
    for name in sorted(_ALL_IR_TYPES):
        row = f"{name:<{col_w}}"
        for phase in phases:
            hit = name in _ir_coverage[phase]
            row += f"  {'HIT' if hit else '.':<{col_w}}"
            if hit and name in ("RawStmt", "RawExpr"):
                raw_hit = True
        lines.append(row)
    if raw_hit:
        lines += [
            "",
            "WARNING: RawStmt/RawExpr was hit -- some Python construct fell "
            "through to the untyped fallback; MethodFrontend is missing real "
            "support for whatever produced it.",
        ]
    return "\n".join(lines), raw_hit


def reset_ir_coverage() -> None:
    """Clear accumulated IR coverage, e.g. to scope a report to one call."""
    for s in _ir_coverage.values():
        s.clear()


if __name__ == "__main__":
    import bdsim
    import numpy as np

    sim = bdsim.BDSim(animation=True)  # create simulator
    bd = sim.blockdiagram()  # create an empty block diagram

    # define the blocks
    demand = bd.STEP(T=1, name="demand")
    sum = bd.SUM("+-")
    gain = bd.GAIN(10)
    plant = bd.LTI_SISO(0.5, [2, 1], name="plant")
    scope = bd.SCOPE(styles=["k", "r--"], loc="lower right")  # , movie='eg1.mp4')

    # x = bd.CONSTANT(np.array([1.1, 2.2]), name="2-vector")
    # gain2 = bd.GAIN(np.array([[1, 2], [3, 4]]), name="2x2 gain")
    # bd.connect(x, gain2)

    # connect the blocks
    bd.connect(demand, sum[0], scope[1])
    bd.connect(plant, sum[1])
    bd.connect(sum, gain)
    bd.connect(gain, plant)
    bd.connect(plant, scope[0])

    bd.compile()  # check the diagram

    bd.report_schedule()

    Codegen(verbose=True).generate(bd)

    print("\n====================================================== IR coverage")
    report, _raw_hit = ir_coverage_report()
    print(report)
