"""The startup banner is the docstring of the script that creates BDSim.

It is not printed in a notebook, where the docstring is noise, or with quiet.
"""

import contextlib
import io
import unittest
from unittest import mock

import bdsim.run_sim

# run as module-level code, as a script's own would be: the banner is the __doc__ of
# the frame that constructs BDSim
SCRIPT = '''"""Hello from the script"""
import bdsim
sim = bdsim.BDSim(sysargs=False, graphics=False, progress=False, **options)
'''


def banner_text(notebook: bool, **options) -> str:
    out = io.StringIO()
    with mock.patch.object(bdsim.run_sim.smb, "isnotebook", return_value=notebook):
        with contextlib.redirect_stdout(out):
            exec(compile(SCRIPT, "script.py", "exec"), {"options": options})
    return out.getvalue()


class BannerTest(unittest.TestCase):
    def test_the_docstring_of_a_script_is_printed(self):
        self.assertIn("* Hello from the script", banner_text(notebook=False))

    def test_it_is_not_printed_in_a_notebook(self):
        self.assertNotIn("Hello from the script", banner_text(notebook=True))

    def test_it_is_not_printed_when_quiet(self):
        self.assertNotIn("Hello from the script", banner_text(False, quiet=True))

    def test_it_is_not_printed_when_turned_off(self):
        self.assertNotIn("Hello from the script", banner_text(False, banner=False))


if __name__ == "__main__":
    unittest.main()
