"""The rule that a pull request's author must be assigned to the issue it addresses.

The script lives in .github/scripts and is run by .github/workflows/assignment.yml, so it
is loaded by path.  Only the rule is tested here, not the calls to GitHub.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

PATH = (
    Path(__file__).resolve().parents[1] / ".github" / "scripts" / "assignment_check.py"
)
spec = importlib.util.spec_from_file_location("assignment_check", PATH)
ac = importlib.util.module_from_spec(spec)
sys.modules["assignment_check"] = ac  # a dataclass looks its module up here
spec.loader.exec_module(ac)


def decide(
    author="newcomer",
    association="NONE",
    bot=False,
    labels=(),
    assignees=None,
    paths=(),
):
    return ac.decide(
        author, association, bot, set(labels), assignees or {}, list(paths)
    )


class IssueNumbersTest(unittest.TestCase):
    def test_closing_and_addressing_words(self):
        for text in (
            "Fixes #12",
            "closes #12",
            "Resolved #12",
            "Addresses #12",
            "Refs: #12",
            "fix #12",
        ):
            with self.subTest(text):
                self.assertEqual(ac.issue_numbers("", text), [12])

    def test_an_umbrella_issue_is_not_a_reference(self):
        body = "Addresses #220 (part of #118)."
        self.assertEqual(ac.issue_numbers("", body), [220])
        self.assertEqual(ac.issue_numbers("", "Part of #118"), [])

    def test_several_in_order_without_repeats(self):
        self.assertEqual(
            ac.issue_numbers("Fixes #5", "closes #6, fixes #5, Fixes #7"), [5, 6, 7]
        )

    def test_a_bare_number_is_not_a_reference(self):
        self.assertEqual(ac.issue_numbers("see #9", "like #10"), [])


class DocsOnlyTest(unittest.TestCase):
    def test_prose_and_images_under_docs(self):
        self.assertTrue(
            ac.is_docs_only(
                [
                    "README.md",
                    "docs/source/index.rst",
                    "docs/figs/a.png",
                    "CONTRIBUTING.md",
                ]
            )
        )

    def test_code_and_configuration_are_not_documentation(self):
        for path in (
            "src/bdsim/block.py",
            "docs/source/conf.py",
            "pyproject.toml",
            "docs/notebooks/a.ipynb",
        ):
            with self.subTest(path):
                self.assertFalse(ac.is_docs_only(["README.md", path]))

    def test_no_files_is_not_documentation(self):
        self.assertFalse(ac.is_docs_only([]))


class DecideTest(unittest.TestCase):
    def test_the_author_assigned_to_the_issue_passes(self):
        self.assertTrue(decide(assignees={12: ["newcomer"]}).ok)

    def test_one_of_several_issues_is_enough(self):
        self.assertTrue(decide(assignees={12: [], 13: ["newcomer", "other"]}).ok)

    def test_an_issue_assigned_to_someone_else_fails(self):
        verdict = decide(assignees={12: ["other"]}, paths=["README.md"])
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.issues, [12])

    def test_an_unassigned_issue_fails_even_for_documentation(self):
        self.assertFalse(decide(assignees={12: []}, paths=["README.md"]).ok)

    def test_no_issue_and_only_documentation_passes(self):
        self.assertTrue(decide(paths=["README.md", "docs/source/x.rst"]).ok)

    def test_no_issue_and_code_fails(self):
        verdict = decide(paths=["README.md", "src/bdsim/block.py"])
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason, "no issue")

    def test_maintainers_bots_and_the_waiver_pass(self):
        code = ["src/bdsim/block.py"]
        for association in ("OWNER", "MEMBER", "COLLABORATOR"):
            self.assertTrue(decide(association=association, paths=code).ok, association)
        self.assertTrue(decide(bot=True, paths=code).ok)
        self.assertTrue(decide(labels=[ac.WAIVER_LABEL], paths=code).ok)

    def test_a_contributor_who_is_not_a_maintainer_does_not_pass_on_association(self):
        for association in (
            "CONTRIBUTOR",
            "FIRST_TIME_CONTRIBUTOR",
            "FIRST_TIMER",
            "NONE",
        ):
            self.assertFalse(
                decide(association=association, paths=["src/a.py"]).ok, association
            )


class MessageTest(unittest.TestCase):
    def test_every_message_carries_the_marker_that_finds_it_again(self):
        for verdict in (
            ac.Verdict(True, "x"),
            ac.Verdict(False, "no issue"),
            ac.Verdict(False, "not assigned", [3]),
        ):
            self.assertTrue(ac.message(verdict, "someone").startswith(ac.MARKER))

    def test_the_failure_names_the_issue_and_the_way_out(self):
        text = ac.message(ac.Verdict(False, "not assigned", [12, 14]), "newcomer")
        self.assertIn("#12, #14", text)
        self.assertIn("newcomer", text)
        text = ac.message(ac.Verdict(False, "no issue"), "newcomer")
        self.assertIn(ac.WAIVER_LABEL, text)
        self.assertIn("documentation", text)


if __name__ == "__main__":
    unittest.main()
