import argparse
import sys

from bdsim import BDSim
from bdsim.blockdiagram import bdload


def _parse_bdrun_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    """Build/parse bdrun CLI flags and keep remaining args for BDSim."""
    parser = argparse.ArgumentParser(
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
    parser.add_argument("-h", "--help", action="store_true", dest="help")
    parser.add_argument("--safe-eval", action="store_true", dest="safe_eval")
    parser.add_argument("--force-eval", action="store_true", dest="force_eval")
    parser.add_argument("--trace-eval", action="store_true", dest="trace_eval")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose")
    parser.add_argument("filename", nargs="?")
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        dest="list_diagram",
        help="show diagram block and wire list, then exit",
    )

    args, remaining = parser.parse_known_args(argv)
    if args.safe_eval and args.force_eval:
        raise ValueError("cannot use --safe-eval and --force-eval together")
    return args, remaining


def _print_full_help(passthrough_argv: list[str]) -> None:
    """Print bdrun help and delegated BDSim help in one place."""
    parser = argparse.ArgumentParser(
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
    parser.add_argument("-h", "--help", action="store_true", dest="help")
    parser.add_argument("--safe-eval", action="store_true", dest="safe_eval")
    parser.add_argument("--force-eval", action="store_true", dest="force_eval")
    parser.add_argument("--trace-eval", action="store_true", dest="trace_eval")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose")
    parser.add_argument("filename", nargs="?")
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        dest="list_diagram",
        help="show diagram block and wire list, then exit",
    )
    parser.print_help()

    original_argv = sys.argv
    # Ensure BDSim enters its own help path regardless of bdrun parsing.
    sys.argv = [sys.argv[0], "-h", *passthrough_argv]
    try:
        BDSim()  # prints BDSim help and exits via SystemExit
    except SystemExit:
        pass
    finally:
        sys.argv = original_argv


def bdrun() -> None:
    """Load a ``.bd`` model file and run it via ``BDSim``.

    CLI entry point: reads ``sys.argv[1:]``.  Options recognised by bdrun
    are stripped; the remainder are forwarded to ``BDSim``.
    """
    parsed, passthrough_argv = _parse_bdrun_args(sys.argv[1:])

    if parsed.help or parsed.filename is None:
        _print_full_help(passthrough_argv)
        return

    allow_eval: bool | None = None
    if parsed.safe_eval:
        allow_eval = False
    elif parsed.force_eval:
        allow_eval = True

    original_argv = sys.argv
    sys.argv = [sys.argv[0], *passthrough_argv]
    try:
        sim = BDSim()  # create simulator (reads its own flags from sys.argv)
    finally:
        sys.argv = original_argv
    bd = sim.blockdiagram()

    bd = bdload(
        bd,
        filename=parsed.filename,
        allow_eval=allow_eval,
        trace_eval=parsed.trace_eval,
        verbose=parsed.verbose,
    )
    if parsed.list_diagram:
        bd.report_lists()
        return

    bd.compile()
    bd.report_summary()
    sim.run(bd)
    print("bdrun exiting")


if __name__ == "__main__":
    try:
        from ._selftest import run_module_test
    except ImportError:
        from bdsim._selftest import run_module_test

    raise SystemExit(run_module_test(__file__))
