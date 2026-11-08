"""Environment bootstrap for bdsim's Jupyter notebooks.

bdsim's copy of the canonical template, rvc-ecosystem/notebooks/bootstrap_template.py,
with only the repo-specific constants changed.  Installs bdsim (and reports how) in a
local Jupyter/VS Code install, on Google Colab and in JupyterLite.  A notebook asks for
more in its metadata, under bdsim_bootstrap: extras (["control"]),
packages and min_version.  sync_bootstrap.py, from rvc-ecosystem, pastes this into
every notebook as a generated cell; never edit that cell.  See docs/notebooks/README.md.
"""

import subprocess
import sys

# --- Repo-specific: the only part a repo should change -----------------------------

# the PyPI name of the toolbox, and the name it is imported under
PACKAGE = "bdsim"
IMPORT_NAME = "bdsim"

# Where the development version lives, for a notebook that needs more than the release on
# PyPI has (see ``min_version``).  None if the repo has no such fallback.
GIT_URL: str | None = "https://github.com/petercorke/bdsim"

# JupyterLite only: packages installed, with their dependencies, before the toolbox.
# Everything the notebooks' plotting needs that Pyodide does not already have.
JL_PACKAGES = []

# JupyterLite only: packages installed with deps=False before everything else, for a
# dependency whose normal resolution fails in Pyodide.  Empty now: spatialmath-python
# <= 1.1.18 listed pre-commit, a dev tool, as a runtime dependency, which needs a
# newer packaging than Pyodide's, and had to be listed here
# (rai-opensource/spatialmath-python#250).  1.1.19 fixed it, so a repo that requires
# spatialmath-python>=1.1.19 needs no entry.
JL_NO_DEPS: list[str] = []

# extras of the toolbox that need more than Pyodide has, installed in JupyterLite as
# these packages instead of through the extra: extra name -> packages
JL_EXTRAS: dict[str, list[str]] = {"control": ["control"]}

# Colab only: packages installed with the toolbox.  Colab does not ship ipympl,
# which the notebooks select with %matplotlib ipympl.
COLAB_PACKAGES = []

# ---------------------------------------------------------------------------------


def _version_of(package: str, module) -> str:
    """The installed version of the package: its metadata, else its ``__version__``."""
    import importlib.metadata

    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return str(getattr(module, "__version__", "unknown"))


def _older(version: str, required: str) -> bool:
    """True if ``version`` is older than ``required``; False if they cannot be compared."""
    try:
        from packaging.version import InvalidVersion, Version

        return Version(version) < Version(required)
    except (ImportError, InvalidVersion):
        return False


async def ensure_installed(
    extras: tuple[str, ...] | list[str] = (),
    packages: tuple[str, ...] | list[str] = (),
    min_version: str | None = None,
) -> bool:
    """Install the toolbox if needed, and report the environment.

    The arguments are set per notebook in its metadata (``<nickname>_bootstrap``) and
    passed here by the generated cell.

    :param extras: toolbox extras the notebook needs, for example ``["ik"]``
    :param packages: other packages the notebook needs, for example ``["control"]`` or
        another toolbox.  Installed in JupyterLite and on Colab; locally the cell only
        says which are missing
    :param min_version: the oldest version of the toolbox the notebook works with.  On
        Colab, if the release on PyPI is older (a notebook that uses what the next
        release will have) the cell installs the development version from ``GIT_URL``
        instead and says so.  Locally it says what to run.  In JupyterLite there is no
        check, since the site's wheel was built from the same commit as the notebook
    :returns: True if running on Google Colab, False otherwise.
    """
    if sys.platform == "emscripten":
        # In JupyterLite, piplite looks in this site's own package index first, so the
        # toolbox it installs is the wheel that was built with the site.  micropip
        # alone cannot see that index and would install the last release from PyPI.
        # (There is no /pypi folder in the kernel to glob for a wheel.)  Outside
        # JupyterLite, for example a test under Node, there is no piplite.
        try:
            import piplite

            install = piplite.install
        except ImportError:
            import micropip

            install = micropip.install

        for name in JL_NO_DEPS:
            await install(name, deps=False)
        for name in JL_PACKAGES:
            await install(name)
        for extra in extras:
            for name in JL_EXTRAS.get(extra, []):
                await install(name)
        for name in packages:
            await install(name)
        await install(PACKAGE)
        where, colab = "in browser", False
    else:
        try:
            import google.colab  # noqa: F401
        except ImportError:
            where, colab = "locally", False
        else:
            print(f"Installing {PACKAGE}...")
            requirement = PACKAGE
            if extras:
                requirement += "[" + ",".join(extras) + "]"
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", requirement]
                + list(packages)
                + COLAB_PACKAGES,
                check=True,
            )
            # matplotlib renames the module://ipympl... backend to "widget", and looks
            # it up in a list of backends that it builds once, from the installed
            # packages, the first time it needs it.  Colab imported matplotlib before
            # ipympl was installed, so %matplotlib ipympl is rejected ("... is not a
            # valid value for backend") until the session restarts.  Make matplotlib
            # build the list again.  Clearing the registry is what its own tests do,
            # and it is needed: only resetting the flag registers the backends that
            # were already there (matplotlib-inline's) twice, which is an error.
            # _clear is private, hence the guards.
            try:
                from matplotlib.backends import backend_registry
            except ImportError:
                pass  # an older matplotlib has no registry to refresh
            else:
                clear = getattr(backend_registry, "_clear", None)
                if clear is not None:
                    clear()

            # ipympl figures need Colab's custom widget manager, enabled before the
            # first figure is created.
            from google.colab import output

            output.enable_custom_widget_manager()
            where, colab = "on Colab", True

    import importlib

    module = importlib.import_module(IMPORT_NAME)
    version = _version_of(PACKAGE, module)

    if colab and min_version is not None and _older(version, min_version) and GIT_URL:
        # The release on PyPI is older than this notebook needs.  The package is pure
        # Python in the repos that use this, so installing from GitHub is quick.  Its
        # dependencies are in already.  Reinstall even if the version number is the
        # same, since the development version often has the number of the last release.
        print(
            f"{PACKAGE} {version} on PyPI is older than {min_version}, installing from GitHub..."
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-q",
                "--force-reinstall",
                "--no-deps",
                f"{PACKAGE} @ git+{GIT_URL}@main",
            ],
            check=True,
        )
        importlib.invalidate_caches()
        version = _version_of(PACKAGE, module)
        where += ", development version from GitHub"

    if not colab and where == "locally":
        import importlib.metadata

        for name in packages:
            try:
                importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                print(f"This notebook needs {name}: pip install {name}")

    if (
        min_version is not None
        and where in ("locally", "on Colab")
        and _older(version, min_version)
    ):
        print(
            f"This notebook needs {PACKAGE} {min_version} or later: pip install -U {PACKAGE}"
        )

    print(f"Running {where} using {PACKAGE} v{version}")
    return colab
