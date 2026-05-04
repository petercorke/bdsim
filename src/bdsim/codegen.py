import ast
import inspect
import textwrap
from dataclasses import dataclass, field
from typing import Any, Iterable
import numpy as np

import bdsim

sim = bdsim.BDSim()

UNKNOWN = object()


class VarType:
    """Holds type information about a variable or value."""

    dtype: str
    etype: str | None = None
    dims: int | tuple[int, int] | None = None

    def __init__(self, v):
        if isinstance(v, str):
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
        self.env: dict[str, Any] = {}
        # Stmts queued by the inliner to splice before the current statement.
        self._pending_stmts: list[IR.Stmt] = []

    def specialize_function(self, fn: IR.Function) -> IR.Function:
        self.env = {}
        body = [self.specialize_stmt(stmt) for stmt in fn.body]
        body = self._flatten(body)
        if self._is_sum_output(fn):
            body = self._specialize_sum_body(body)
        body = [self.specialize_stmt(stmt) for stmt in body]
        body = self._flatten(body)
        return IR.Function(name=fn.name, args=fn.args, body=body)

    def _is_sum_output(self, fn: IR.Function) -> bool:
        block_type = getattr(self.block_cfg.block, "type", "")
        return fn.name == "output" and block_type == "sum"

    def _specialize_sum_body(self, body: list[IR.Stmt]) -> list[IR.Stmt]:
        if not body:
            return body
        if not isinstance(body[0], IR.For):
            return body

        signs = self.self.get("signs")
        if not isinstance(signs, str) or len(signs) == 0:
            return body

        def in_at(i: int) -> IR.Expr:
            return IR.Subscript(IR.Name("inputs"), IR.Literal(i))

        expr: IR.Expr
        expr = in_at(0) if signs[0] == "+" else IR.UnaryOp("-", in_at(0))
        for i, sign in enumerate(signs[1:], start=1):
            if sign == "+":
                expr = IR.BinaryOp(expr, "+", in_at(i))
            else:
                expr = IR.BinaryOp(expr, "-", in_at(i))

        assign = IR.Assign(IR.Name("sum"), expr)
        return [assign] + body[1:]

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
            return IR.For(
                self.specialize_expr(stmt.target),
                self.specialize_expr(stmt.iterable),
                self._flatten([self.specialize_stmt(s) for s in stmt.body]),
                self._flatten([self.specialize_stmt(s) for s in stmt.orelse]),
            )
        if isinstance(stmt, IR.If):
            cond = self.specialize_expr(stmt.condition)
            val = self.eval_expr(cond)
            body = self._flatten([self.specialize_stmt(s) for s in stmt.body])
            orelse = self._flatten([self.specialize_stmt(s) for s in stmt.orelse])
            if val is True:
                return body
            if val is False:
                return orelse
            return IR.If(cond, body, orelse)
        return stmt

    def specialize_expr(self, expr: IR.Expr) -> IR.Expr:
        _ir_coverage["spec_expr"].add(type(expr).__name__)
        if isinstance(expr, IR.Attribute):
            value = self.specialize_expr(expr.value)
            return IR.Attribute(value, expr.attr)
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
            val = self.eval_expr(out)
            if val is not UNKNOWN and not isinstance(val, VarType):
                return _literal_from(val)
            # --- Intrinsic annotation (Strategy A) ---
            # Mark the call with an IntrinsicCall wrapper so the emitter
            # can render it without knowing about Python function objects.
            f_val = self.eval_expr(out.func)
            arg_vals = [self.eval_expr(a) for a in out.args]
            if callable(f_val) and not any(v is UNKNOWN for v in arg_vals):
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
                try:
                    inline_result = IRInliner.inline(f_val, out.args)
                    if inline_result is not None:
                        extra_stmts, result_expr = inline_result
                        # Specialize the inlined body
                        spec_extra = []
                        for s in extra_stmts:
                            r = self.specialize_stmt(s)
                            spec_extra.extend(r if isinstance(r, list) else [r])
                        self._pending_stmts.extend(spec_extra)
                        return self.specialize_expr(result_expr)
                except (RecursionError, OSError, TypeError, AttributeError):
                    pass
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
        if name == "np":
            return np
        if name == "isinstance":
            return isinstance
        if name == "len":
            return len
        if name == "enumerate":
            return enumerate
        if name == "zip":
            return zip
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
            base = self.eval_expr(expr.value)
            if base is UNKNOWN:
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
                    if l.dtype == "ndarray" or r.dtype == "ndarray":
                        nd = l if l.dtype == "ndarray" else r
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
    MAX_DEPTH = 3

    @classmethod
    def inline(
        cls, fn_obj, arg_exprs: list[IR.Expr], depth: int = 0
    ) -> tuple[list[IR.Stmt], IR.Expr] | None:
        """Return (stmts, result_expr) or None if not inlineable."""
        if depth >= cls.MAX_DEPTH:
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

            prefix = f"_il{depth}_"
            formal_names = [a.arg for a in func_def.args.args]
            # Build substitution map: formal → actual arg expr
            subst: dict[str, IR.Expr] = {}
            for formal, actual in zip(formal_names, arg_exprs):
                subst[formal] = actual

            frontend = MethodFrontend({})
            raw_body = frontend.lower_block(func_def.body)

            renamer = _IRAlphaRenamer(prefix, subst)
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


def _flatten_list(nodes):
    out = []
    for n in nodes:
        if isinstance(n, list):
            out.extend(_flatten_list(n))
        else:
            out.append(n)
    return out


class _IRAlphaRenamer:
    """α-rename locals in IR, substituting formals with actual arg exprs."""

    def __init__(self, prefix: str, subst: dict[str, IR.Expr]) -> None:
        self.prefix = prefix
        self.subst = subst  # formal_name -> IR.Expr replacement

    def _local(self, name: str) -> str:
        return self.prefix + name

    def rename_expr(self, e: IR.Expr) -> IR.Expr:
        if isinstance(e, IR.Name):
            if e.name in self.subst:
                return self.subst[e.name]
            return IR.Name(self._local(e.name))
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
        if isinstance(e, IR.Call):
            return IR.Call(
                self.rename_expr(e.func), [self.rename_expr(a) for a in e.args]
            )
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
        "int32": "int32_t",
        "int64": "int64_t",
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
    }

    def __init__(self, cfg, types: dict[str, str] | None = None) -> None:
        super().__init__(cfg, types)
        self._needed_helpers: set[str] = set()
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
        if vt.dtype in self._SCALAR_TYPES:
            return self._SCALAR_TYPES[vt.dtype]
        if vt.dtype == "ndarray":
            if not isinstance(vt.dims, tuple):
                self._fail("ndarray VarType must have tuple dims")
            scalar = self._etype_to_cpp(vt.etype)
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
        if isinstance(e, (IR.Call, IR.IntrinsicCall)):
            return None
        if isinstance(e, IR.Compare):
            return "bool"
        if isinstance(e, IR.BoolOp):
            return "bool"
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
            return repr(value)
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

    def expr_BinaryOp(self, e: IR.BinaryOp) -> str:
        if e.op == "@":
            # NumPy matmul → Eigen helper
            return f"matmul({self.expr(e.left)}, {self.expr(e.right)})"
        lt = self.infer_expr_type(e.left)
        rt = self.infer_expr_type(e.right)
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
        target = s.target.name
        rhs = self.expr(s.value)
        if target not in self.locals_types:
            inferred = self.infer_expr_type(s.value)
            if inferred is None:
                self._fail(
                    f"cannot infer C++ type for local '{target}'"
                    f" (rhs is {type(s.value).__name__})",
                    s,
                )
            self.locals_types[target] = inferred
        if target in self.declared_locals:
            self._emit(f"{target} = {rhs};")
        else:
            self._emit(f"{self.locals_types[target]} {target} = {rhs};")
            self.declared_locals.add(target)

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

        prefix = fixname(block_name)
        self_struct = f"{prefix}_self"
        in_struct = f"{prefix}_inports"
        out_struct = f"{prefix}_outports"

        # Emit function body
        for s in ir.body:
            self.stmt(s)
        body_lines = list(self._lines)

        # Build struct definitions
        self_initializers = {
            name: self.literal_to_str(value)
            for name, (value, _vt) in self.cfg.self.items()
            if name in self._self_field_types
        }
        struct_lines: list[str] = [
            # "// Generated C++ structs for block state and ports",
            *self._struct(
                self_struct,
                list(self._self_field_types.items()),
                initializers=self_initializers,
            ),
            "",
            *self._struct(
                in_struct, [(f"_{i}", t) for i, t in enumerate(self._inport_types)]
            ),
            "",
            *self._struct(
                out_struct, [(f"_{i}", t) for i, t in enumerate(self._outport_types)]
            ),
        ]

        # Prepend helper bodies for any intrinsics that were used
        helper_texts = [
            self.INTRINSIC_IMPLS[name][1]
            for name in sorted(self._needed_helpers)
            if self.INTRINSIC_IMPLS.get(name, (None, None))[1] is not None
        ]
        if helper_texts:
            struct_lines = helper_texts + [""] + struct_lines

        func_lines: list[str] = [
            # "// Generated C++ function from specialized IR",
            (
                f"void {prefix}_{function_name}(double t, "
                f"const Eigen::VectorXd& x, {self_struct}& self, "
                f"const {in_struct}& inports, {out_struct}& outports) {{"
            ),
            *body_lines,
            "}",
        ]

        return "\n".join(struct_lines), "\n".join(func_lines)


def emit_cpp(
    ir: IR.Function,
    block_name: str,
    function_name: str,
    cfg,
    types: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Backward-compatible wrapper around :class:`CppEmitter`."""
    return CppEmitter(cfg, types=types).emit(ir, block_name, function_name)


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


def codegen(bd):
    # build a dictionary of block metadata for code generation
    block_dict = {}

    def block_cfg(block):
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
            # print(f"  {name}: {value} ({type(value)})")
            _self[name] = (value, VarType(value))

        return SimpleNamespace(
            block=block,
            nin=block.nin,
            nout=block.nout,
            nstates=block.nstates,
            ndstates=block.ndstates,
            itypes=itypes,
            otypes=otypes,
            self=_self,
        )

    printer = IRPrettyPrinter()

    fp = open("codegen.cpp", "w")
    for block in bd.blocklist:

        cfg = block_cfg(block)

        if cfg.nout == 0:
            continue
        print(f"====================================================== {block.name}")
        print(cfg)

        method_ir = lower_block_method(cfg.block.output, cfg)
        print("--- raw IR")
        print(printer.format(method_ir))
        print("--- specialized IR")
        spec_ir = specialize_ir(method_ir, cfg)
        print(printer.format(spec_ir))
        print("--- emitted C++")
        s, f = emit_cpp(spec_ir, block.name, "output", cfg)
        fp.write(f"// C++ code for block {block.name}\n")
        fp.write(s + "\n\n" + f + "\n\n")

    # build the run-time schedule and wiring

    for sequence, group in enumerate(bd.plan):
        fp.write(f"\n\n/****** Schedule group {sequence} *******/\n")
        for b in group:
            print(f"Schedule {b.name} at sequence {sequence}")
            name = fixname(b.name)

            if b.nin > 0 and sequence > 0:
                fp.write("\n")
                for port, source in enumerate(b.inports):
                    value = source.block.outport_value(source.port)
                    typ = type(value).__name__
                    # if isinstance(value, np.ndarray):
                    #     typ += "{:s}.{:s}".format(str(value.shape), str(value.dtype))
                    src_name = source.block.name or ""
                    if source.block.nout > 1:
                        src_name += f"[{source.port}]"

                    fp.write(
                        f"{name}_inports._{port} = {src_name}_outports._{source.port};  // {name}[{port}] <-- {src_name}[{source.port}] (type: {typ})\n"
                    )

            # EMIT THE FUNCTION CALL
            # e.g. bdsim_step_blockname(t, x, self_blockname,
            fp.write(
                f"{name}_output(t, x, {name}_self, {name}_inports, {name}_outports);\n"
            )


# TODO:
# - handle next() blocks
# - redo scheduler for multi-clock systems
# - add time groups
# - pass appropriate bits of state vector to each function, not the whole x

# # --- IR coverage summary ---
# print("\n====================================================== IR coverage")
# col_w = 20
# phases = ["spec_stmt", "spec_expr", "emit_stmt", "emit_expr"]
# header = f"{'node type':<{col_w}}" + "".join(f"  {p:<{col_w}}" for p in phases)
# print(header)
# print("-" * len(header))
# for name in sorted(_ALL_IR_TYPES):
#     row = f"{name:<{col_w}}"
#     for phase in phases:
#         hit = "HIT" if name in _ir_coverage[phase] else "."
#         row += f"  {hit:<{col_w}}"
#     print(row)


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

    codegen(bd)
