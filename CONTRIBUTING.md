# CONTRIBUTING

Contributions are welcome, and are accepted via pull requests.
Please review these guidelines before submitting any pull requests.

## Process

1. Fork the project
1. Create a new branch
1. Code, test, commit and push
1. Open a pull request detailing your changes

## Guidelines

* Please ensure the coding style by running the commands in the [Lint](#lint) section below.
* Send a coherent commit history, making sure each individual commit in your pull request is meaningful.
* You may need to [rebase](https://git-scm.com/book/en/v2/Git-Branching-Rebasing) to avoid merge conflicts.
* Please remember that we follow [SemVer](http://semver.org/).

## Setup

Clone your fork, then install the dev dependencies:
```bash
uv sync --all-extras
```

Install the pre-commit hooks so linting and formatting run on each commit:
```bash
uv run pre-commit install
```
## Lint

Format and lint your code:
```bash
uv run ruff format src tests
uv run ruff check src tests
```

Check types:
```bash
uv run mypy
```

## Tests

Run the tests, skipping the ones that need a live Ableton (this is what CI runs):
```bash
uv run pytest -m "not integration"
```

Tests marked `integration` need a running Ableton with the remote script enabled, so they are deselected by default. Run the full suite, including those, once Ableton is up:
```bash
uv run pytest
```
