import argparse
import sys
import warnings
from typing import Any

from bdsim import BDSim
from bdsim.blockdiagram import bdload


def _bdrun_arg_parser() -> argparse.ArgumentParser:
    """Build parser for bdrun-specific CLI options."""
    return argparse.ArgumentParser(
        prog="bdrun",
        description="load and run a block-diagram file (.bd)",
        epilog=(
            "examples:\n"
            "  bdrun model.bd\n"
            "  bdrun model.bd --no-graphics --simtime 5\n\n"
            "The options below are provided by the BDSim runtime:"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )


def _add_bdrun_cli_args(parser: argparse.ArgumentParser) -> None:
    """Attach bdrun-specific CLI options to a parser."""
    parser.add_argument("-h", "--help", action="store_true", dest="help")
    parser.add_argument("--safe-eval", action="store_true", dest="safe_eval")
    parser.add_argument("--force-eval", action="store_true", dest="force_eval")
    parser.add_argument("--trace-eval", action="store_true", dest="trace_eval")
    parser.add_argument("filename", nargs="?")
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        dest="list_diagram",
        help="show diagram block and wire list, then exit",
    )


def _parse_bdrun_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    """Parse bdrun-specific flags and keep the remaining args for BDSim."""
    parser = _bdrun_arg_parser()
    _add_bdrun_cli_args(parser)

    args, remaining = parser.parse_known_args(argv)
    if args.safe_eval and args.force_eval:
        raise ValueError("cannot use --safe-eval and --force-eval together")
    return args, remaining


def _print_full_help(passthrough_argv: list[str], **kwargs: Any) -> None:
    """Print bdrun help and delegated BDSim help in one place."""
    parser = _bdrun_arg_parser()
    _add_bdrun_cli_args(parser)
    parser.print_help()

    original_argv = sys.argv
    # Ensure BDSim enters its own help path regardless of bdrun parsing.
    sys.argv = [sys.argv[0], "-h", *passthrough_argv]
    try:
        BDSim(**kwargs)  # prints BDSim help and exits via SystemExit
    except SystemExit:
        pass
    finally:
        sys.argv = original_argv


def bdrun(
    filename: str | None = None,
    globalvars: dict[str, Any] | None = None,
    *,
    globals: dict[str, Any] | None = None,
    allow_eval: bool | None = None,
    trace_eval: bool = False,
    **kwargs: Any,
) -> None:
    """Load a ``.bd`` model file and run it via ``BDSim``.

    :param filename: Path to ``.bd`` JSON model file. If ``None``, uses
        ``sys.argv[1]``.
    :type filename: str, optional
    :param globalvars: Extra names available when evaluating ``"=..."`` parameter
        expressions in the model. These names are merged with this module's
        global namespace before calling ``eval``.
    :type globalvars: dict[str, Any], optional
    :param globals: Deprecated alias for ``globalvars``.
    :type globals: dict[str, Any], optional
    :param allow_eval: controls expression evaluation behavior. ``True`` enables
        ``eval`` without warning, ``False`` refuses required ``=...`` expressions,
        ``None`` (default) allows evaluation with a one-time warning.
    :type allow_eval: bool, optional
    :param trace_eval: print each expression before it is evaluated.
    :type trace_eval: bool, optional
    :param kwargs: Additional keyword args forwarded to ``BDSim`` and ``bdload``.
    :type kwargs: dict[str, Any]

    ``globalvars`` is intended for trusted, local workflows where model expressions
    should be able to resolve symbols from caller code (for example, constants,
    lambdas, or helper functions).

    Changed in 1.1: ``globals`` is deprecated in favor of ``globalvars``.
    Loading model expressions uses ``eval`` and should only be done for trusted
    model files.
    """
    if globals is not None:
        if globalvars is not None:
            raise ValueError("provide only one of globalvars or globals")
        warnings.warn(
            "bdrun(..., globals=...) is deprecated; use globalvars=... instead",
            DeprecationWarning,
            stacklevel=2,
        )
        globalvars = globals

    if globalvars is None:
        globalvars = {}

    argv = sys.argv[1:]
    cli_filename: str | None = None
    passthrough_argv = argv
    if filename is None:
        parsed, passthrough_argv = _parse_bdrun_args(argv)
        cli_filename = parsed.filename
        trace_eval = trace_eval or parsed.trace_eval
        if parsed.safe_eval:
            allow_eval = False
        elif parsed.force_eval:
            allow_eval = True

    # Print full help for both explicit -h and no-argument invocation.
    if filename is None and (len(argv) == 0 or "-h" in argv or "--help" in argv):
        _print_full_help(passthrough_argv, **kwargs)
        return

    if filename is None:
        if cli_filename is not None:
            filename = cli_filename
        else:
            _print_full_help(passthrough_argv, **kwargs)
            return

    original_argv = sys.argv
    sys.argv = [sys.argv[0], *passthrough_argv]
    try:
        sim = BDSim(**kwargs)  # create simulator
    finally:
        sys.argv = original_argv
    bd = sim.blockdiagram()  # create diagram

    bd = bdload(
        bd,
        filename=filename,
        globalvars=globalvars,
        allow_eval=allow_eval,
        trace_eval=trace_eval,
        verbose=True,
        **kwargs,
    )
    if parsed.list_diagram:
        bd.report_lists()
        return

    bd.compile()
    bd.report_summary()

    out = sim.run(bd)  # simulate
    print("bdrun exiting")


if __name__ == "__main__":
    try:
        from ._selftest import run_module_test
    except ImportError:
        from bdsim._selftest import run_module_test

    raise SystemExit(run_module_test(__file__))
