# Contributing to bdsim

Thanks for your interest in contributing! We welcome bug reports, fixes, new features, and documentation improvements.

## Reporting issues

Please use the issue template and include:

- Your operating system, Python version, and bdsim version
- A short, self-contained code example that reproduces the problem

## Looking for somewhere to start?

Issues labelled [`good first issue`](https://github.com/petercorke/bdsim/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) or [`help wanted`](https://github.com/petercorke/bdsim/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) are a good place to start.

## Before you open a pull request

Several people (and AI coding agents) often pick up the same issue at about the same time, which wastes everyone's effort. To avoid duplicates:

1. **Check for existing work.** Look at the linked pull requests on the issue page, and search open PRs, for example `gh pr list --state open --search "#123"`. If a PR for the same issue already exists, review it or suggest improvements there instead of opening a competing one.
2. **Claim the issue.** Comment on the issue to say you are working on it. For larger items, the maintainer may assign the issue to you as an "in progress" marker; if you stop working on it, please say so, so someone else can take it.
3. **Say if you used AI assistance.** AI-assisted contributions are welcome, but please state it in the PR description, and make sure you have read, run and understood the change yourself.
4. **Flag behaviour changes.** If a change alters numerical results or public behaviour, say so explicitly in the PR description, even if it is a bug fix.

## Contributing code

- Keep pull requests scoped to a single feature or fix. If you have several unrelated changes, open separate PRs so each can be reviewed and merged independently.
- For API changes, propose the change in [Discussions](https://github.com/petercorke/bdsim/discussions) before opening a PR.
- PR titles follow [Conventional Commits](https://www.conventionalcommits.org/) (`type: description`) — checked automatically on the PR.
- Code is formatted and linted with [ruff](https://docs.astral.sh/ruff/); configuration is in `pyproject.toml` under `[tool.ruff]`. CI runs `ruff check .` and `ruff format --check .`, so before pushing run:

  ```
  ruff format .
  ruff check .
  ```

  `pip install -e '.[dev]'` installs the pinned ruff version. Please don't reformat code you are not otherwise changing.
- New or changed code should be type-hinted using modern syntax (`X | Y`, `X | None`, `list[X]`, `dict[K, V]` — not `Union`, `Optional`, `List`, `Dict`).
- Docstrings use reST style (`:param:`, `:returns:`). Type hints in the function signature already cover types, so `:type:`/`:rtype:` are rarely needed.
- Any code change should be covered by tests and must not break existing ones. Tests live in `tests/`. Install the dev dependencies with `pip install -e '.[dev]'` (add `,docs` too if you're touching documentation), then run:

  ```
  pytest --capture=no --timeout=50 --timeout_method=thread
  ```

- Target branch is `main`.

## License

By contributing, you agree that your contributions will be licensed under this project's [MIT License](LICENSE).
