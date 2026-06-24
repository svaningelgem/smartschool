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

## Coding guidelines

How the codebase is meant to read and evolve:

### Keep it simple

- Reach for the standard library before adding a dependency, and a few lines
  before a new dependency. Don't introduce an abstraction (an interface with one
  implementation, a factory for one product, config for a value that never
  changes) until something actually needs it.
- Deletion beats addition. When a change makes a variable, import, alias, or
  helper redundant, remove it in the same pass — don't leave cascading dead code.
- Unreachable code *is* dead code: delete it, don't bury it under
  `# pragma: no cover`. A pragma is only for code that is reachable in production
  but genuinely can't be exercised by a test (a `__main__` block, real-network
  wiring with no logic to assert).

### Style

- Prefer `@dataclass` over a hand-written `__init__`.
- Imports go at the top of the file, never inline — the only exception is
  breaking a real circular import.
- Internal modules use relative imports (`from ._objects import …`); user-facing
  code imports from `smartschool` (see *Project layout & the public API*).
- Log through `logprise` / `loguru` with `{}`-style or f-string arguments —
  **never** printf-style. `logger.info("got %d", n)` silently drops the argument
  and logs the literal `"got %d"`; write `logger.info("got {}", n)` or an
  f-string.
- Use a bare `assert` to *document* an invariant that is structurally always
  true; use an explicit `if cond: raise …` to *enforce* a condition that can
  actually fail at runtime — `python -O` strips `assert`, so it must never be
  your only guard.

### Tests

- Test behaviour, not implementation. Drive the public API and assert on
  observable results, backed by the captured fixtures or a real `tmp_path` file.
  Don't patch internal helpers or stdlib calls (`Path.exists`, `Path.is_file`, a
  private function) — a test that only passes because of such a mock isn't
  testing the code.
- Use pytest-mock's `mocker` fixture, not `unittest.mock` directly, and pass
  `autospec=True` when patching something from an external library so signature
  drift is caught.

## Running the tests

```bash
pytest --cov=smartschool --cov-branch --cov-report=term
```

Tests use captured fixtures under `tests/requests/` and never hit the network —
there is no Smartschool account required to run them.

**Coverage must be 100% (line *and* branch).** CI runs with
`--cov-fail-under=100 --cov-branch`, and Codecov gates both `project` and `patch`
at 100%, so every new line and branch needs a test. See *Coding guidelines →
Tests* for the behaviour-over-mocking rule.

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
(`_session.py`, `_results.py`, `_objects.py`, …). They import each other with
**relative** imports (`from ._objects import …`), never the absolute
`from smartschool._objects import …` form — keep it consistent across the
package. These modules are not part of the public API, so never import from
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
