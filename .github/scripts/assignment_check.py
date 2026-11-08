#!/usr/bin/env python3
"""Check that the author of a pull request is assigned to the issue it addresses.

bdsim asks contributors to ask to be assigned an issue, and to wait, before opening a
pull request (CONTRIBUTING.md).  This enforces it, so that several people, or agents,
do not race each other to the same issue.  The rule, for an author who is not a
maintainer or a bot:

* the pull request mentions an issue (``Fixes #12``, ``Addresses #12``): the author must
  be assigned to it;
* it mentions none, and only changes documentation: it passes, a typo needs no issue;
* it mentions none and changes anything else: it fails.

A maintainer can waive the rule for a pull request with the ``no-issue-needed`` label.

The verdict is the exit status.  Unless ``DRY_RUN`` is ``true`` a failure also leaves a
comment, kept up to date as the pull request changes, and the ``needs-assignment`` label.

SECURITY.  This runs on ``pull_request_target``, which runs the base branch's workflow
with a token that can write, even for a fork.  It must therefore never check out, build
or run anything from the pull request, and never put text from the pull request into a
shell command.  It only calls the GitHub API, with the arguments of ``gh`` as a list.

Environment: ``REPO`` (owner/name), ``PR_NUMBER``, ``GH_TOKEN``, ``DRY_RUN``.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

MARKER = "<!-- assignment-check -->"
WAIVER_LABEL = "no-issue-needed"
NEEDS_LABEL = "needs-assignment"
TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}

# Only these words link an issue.  "Part of #118" does not: that is an umbrella issue.
ISSUE_REF = re.compile(
    r"\b(?:fix(?:e[sd])?|close[sd]?|resolve[sd]?|address(?:e[sd])?|refs?)\b[ :]*#(\d+)",
    re.IGNORECASE,
)
# What counts as documentation: prose files, and images under docs/.  Not docs/conf.py.
DOC_PATH = re.compile(
    r"(\.(md|rst|txt)$)|((^|/)(README|CONTRIBUTING|AGENTS|CHANGELOG)[^/]*$)"
    r"|(^docs/.*\.(png|svg|jpe?g|gif|css)$)"
)


@dataclass
class Verdict:
    ok: bool
    reason: str
    issues: list[int] = field(default_factory=list)


def issue_numbers(title: str, body: str) -> list[int]:
    """Issue numbers that a pull request says it addresses, in order, without repeats."""
    found: list[int] = []
    for text in (title or "", body or ""):
        for match in ISSUE_REF.finditer(text):
            number = int(match.group(1))
            if number not in found:
                found.append(number)
    return found


def is_docs_only(paths: list[str]) -> bool:
    """True if the pull request changes at least one file and only documentation."""
    return bool(paths) and all(DOC_PATH.search(path) for path in paths)


def decide(
    author: str,
    association: str,
    is_bot: bool,
    labels: set[str],
    assignees: dict[int, list[str]],
    paths: list[str],
) -> Verdict:
    """The verdict for a pull request.

    :param assignees: the genuine issues that the pull request mentions, and who is
        assigned to each
    :param paths: the files it changes, needed only when it mentions no issue
    """
    if is_bot:
        return Verdict(True, "the author is a bot")
    if association in TRUSTED:
        return Verdict(True, "the author is a maintainer")
    if WAIVER_LABEL in labels:
        return Verdict(True, f"a maintainer added the {WAIVER_LABEL} label")
    issues = sorted(assignees)
    if issues:
        mine = [n for n in issues if author in assignees[n]]
        if mine:
            return Verdict(True, f"the author is assigned to #{mine[0]}", issues)
        return Verdict(False, "not assigned", issues)
    if is_docs_only(paths):
        return Verdict(True, "it changes only documentation, which needs no issue")
    return Verdict(False, "no issue")


def message(verdict: Verdict, author: str) -> str:
    """The comment that explains a verdict."""
    guide = (
        "[CONTRIBUTING.md]"
        "(https://github.com/petercorke/bdsim/blob/main/CONTRIBUTING.md"
        "#before-you-open-a-pull-request)"
    )
    if verdict.ok:
        return f"{MARKER}\nAssignment check passed: {verdict.reason}."
    if verdict.reason == "no issue":
        return (
            f"{MARKER}\nThank you for the pull request. bdsim asks contributors to be "
            f"assigned an issue before opening one (see {guide}), and this pull request "
            "does not say which issue it addresses.\n\n"
            "- If there is an issue for this, mention it in the description, for example "
            "`Fixes #123`. Comment on the issue to ask to be assigned, and wait for a "
            "maintainer.\n"
            "- Small documentation fixes do not need an issue. A maintainer can also "
            f"waive the requirement with the `{WAIVER_LABEL}` label.\n\n"
            "This check runs again when the description is edited or a label changes."
        )
    numbers = ", ".join(f"#{n}" for n in verdict.issues)
    return (
        f"{MARKER}\nThank you for the pull request. The issue it addresses ({numbers}) "
        f"is not assigned to `{author}`. bdsim asks contributors to comment on the "
        f"issue to ask to be assigned, and to wait for a maintainer before opening a "
        f"pull request (see {guide}). A pull request for an issue that is not assigned "
        "to its author may be closed without review.\n\n"
        "This check runs again when the description is edited or a label changes, and "
        "a maintainer can run it again once the issue is assigned."
    )


# ---- GitHub, through the gh command, whose arguments are never passed to a shell ----


def gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)  # nosec B603 B607
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}: {result.stderr.strip()}")
    return result.stdout


def gh_json(*args: str) -> object:
    return json.loads(gh(*args))


def linked_issues(repo: str, number: int) -> list[int]:
    """Issues that GitHub itself links to the pull request (closing keywords, sidebar)."""
    owner, name = repo.split("/")
    query = (
        "query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){"
        "pullRequest(number:$n){closingIssuesReferences(first:20){nodes{number}}}}}"
    )
    data = gh_json(
        "api",
        "graphql",
        "-f",
        f"query={query}",
        "-f",
        f"o={owner}",
        "-f",
        f"r={name}",
        "-F",
        f"n={number}",
    )
    nodes = data["data"]["repository"]["pullRequest"]["closingIssuesReferences"][
        "nodes"
    ]  # type: ignore[index]
    return [node["number"] for node in nodes]


def issue_assignees(repo: str, number: int) -> list[str] | None:
    """Who is assigned to an issue; None if it is not a genuine issue (a PR, or missing)."""
    try:
        issue = gh_json("api", f"repos/{repo}/issues/{number}")
    except RuntimeError:
        return None
    if "pull_request" in issue:  # type: ignore[operator]
        return None
    return [a["login"] for a in issue["assignees"]]  # type: ignore[index]


def changed_paths(repo: str, number: int) -> list[str]:
    out = gh(
        "api",
        f"repos/{repo}/pulls/{number}/files",
        "--paginate",
        "--jq",
        ".[].filename",
    )
    return [line for line in out.splitlines() if line]


def upsert_comment(repo: str, number: int, body: str, create: bool) -> None:
    """Update our comment if there is one; make it only if ``create`` (a failure)."""
    out = gh(
        "api",
        f"repos/{repo}/issues/{number}/comments",
        "--paginate",
        "--jq",
        f'.[] | select(.body | startswith("{MARKER}")) | .id',
    )
    existing = out.split()
    if existing:
        gh(
            "api",
            "-X",
            "PATCH",
            f"repos/{repo}/issues/comments/{existing[0]}",
            "-f",
            f"body={body}",
        )
    elif create:
        gh(
            "api",
            "-X",
            "POST",
            f"repos/{repo}/issues/{number}/comments",
            "-f",
            f"body={body}",
        )


def set_label(
    repo: str, number: int, name: str, present: bool, current: set[str]
) -> None:
    if present and name not in current:
        gh(
            "api",
            "-X",
            "POST",
            f"repos/{repo}/issues/{number}/labels",
            "-f",
            f"labels[]={name}",
        )
    elif not present and name in current:
        gh("api", "-X", "DELETE", f"repos/{repo}/issues/{number}/labels/{name}")


def main() -> int:
    repo, number = os.environ["REPO"], int(os.environ["PR_NUMBER"])
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    pr = gh_json("api", f"repos/{repo}/pulls/{number}")
    author = pr["user"]["login"]  # type: ignore[index]
    labels = {label["name"] for label in pr["labels"]}  # type: ignore[index]
    is_bot = pr["user"]["type"] == "Bot" or author.endswith("[bot]")  # type: ignore[index]

    mentioned = issue_numbers(pr["title"], pr["body"] or "")  # type: ignore[index]
    for n in linked_issues(repo, number):
        if n not in mentioned:
            mentioned.append(n)
    assignees = {}
    for n in mentioned:
        people = issue_assignees(repo, n)
        if people is not None:
            assignees[n] = people
    paths = [] if assignees else changed_paths(repo, number)

    verdict = decide(author, pr["author_association"], is_bot, labels, assignees, paths)  # type: ignore[index]
    print(
        f"#{number} by {author} ({pr['author_association']}): "  # type: ignore[index]
        f"{'PASS' if verdict.ok else 'FAIL'} - {verdict.reason}; issues {mentioned or 'none'}; "
        f"assignees {assignees or 'n/a'}; docs-only {is_docs_only(paths) if paths else 'n/a'}"
    )

    if not dry_run:
        upsert_comment(repo, number, message(verdict, author), create=not verdict.ok)
        set_label(repo, number, NEEDS_LABEL, not verdict.ok, labels)
    return 0 if verdict.ok else 1


if __name__ == "__main__":
    sys.exit(main())
