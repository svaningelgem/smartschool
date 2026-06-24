# Contributing

Thanks for helping improve **smartschool**! This guide covers the local setup,
the conventions the CI enforces, and how the package is structured.

## Getting started

The project uses [Poetry](https://python-poetry.org/) and targets Python 3.10+.

```bash
git clone https://github.com/svaningelgem/smartschool
cd smartschool
poetry install
```

Run everything below either inside `poetry run …` or after activating the
virtualenv (`poetry shell`).

## Running the tests

```bash
pytest --cov=smartschool --cov-branch --cov-report=term
```

Tests use captured fixtures under `tests/requests/` and never hit the network —
there is no Smartschool account required to run them.

**Coverage must be 100% (line *and* branch).** CI runs with
`--cov-fail-under=100 --cov-branch`, and Codecov gates both `project` and `patch`
at 100%, so every new line and branch needs a test. Prefer behavioural tests over
mocking internals: if you find yourself patching an implementation detail (a
private helper, `Path.exists`, …), reach for a real `tmp_path` file or fixture
instead.

## Linting & formatting

```bash
ruff check --fix .
ruff format .
```

CI runs `ruff check --no-fix .`, so make sure it is clean before pushing. Style
rules (and the 160-char line length) live in `pyproject.toml`.

## Type stubs

A few modules ship hand-checked-but-generated `.pyi` stubs (the ones mixing
pydantic dataclasses with the session mixin). If you change a class that has a
stub, regenerate them:

```bash
./restub
```

CI will also auto-commit regenerated stubs, but regenerating locally keeps the
diff clean.

## Project layout & the public API

**Everything a user needs is importable from the package root:**

```python
from smartschool import Smartschool, PathCredentials, Results, ResultType
```

Implementation lives in **private, underscore-prefixed modules**
(`_session.py`, `_results.py`, `_objects.py`, …). They import each other
directly, but they are not part of the public API — never import from
`smartschool._something` in user-facing code, the bundled scripts, or the docs.

When you add a new public class, function, or enum:

1. Define it in the appropriate `_module.py`.
2. Re-export it from `src/smartschool/__init__.py` and add it to `__all__`.
3. If a public function returns or accepts it, it **must** be re-exported too —
   a user should never have to reach into a private module to name a type.

Tests and scripts import from `smartschool` as well; the only exception is unit
tests that deliberately exercise a private internal (e.g. `_build_alias_map`).

## Commits & pull requests

PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `refactor:`, `chore:`, …) — they become the squash-merge commit
subject and a CI check (`commitizen`) validates them. Use `!` or a
`BREAKING CHANGE:` footer for anything that changes the public API.

Before opening a PR, make sure `pytest` (100% coverage), `ruff check`, and
`ruff format --check` all pass locally.
