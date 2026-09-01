# smartschool

Unofficial Python API for the Smartschool platform. `src/smartschool` is the shipped
package; `dev/` and `scripts/` are tooling; `tests/requests/` holds captured server
responses used as fixtures.

## Releasing

Releases are **fully tag-driven** by `.github/workflows/release.yml` ("Publish to PyPI").
The only manual step is pushing a **lightweight** tag in the bare `X.Y.Z` form (no `v`
prefix — `tag_format = "$version"`) on **master HEAD**.

The workflow then runs `poetry version <tag>` (CI-only), ruff + tests + coverage,
`cz changelog`, `poetry build`, publishes to PyPI via trusted publishing, creates the
GitHub Release itself (`gh release create`, notes from
`.github/changelog/release_notes.md.j2`), attaches the wheel + sdist, and commits the
regenerated `CHANGELOG.md` back to master.

- **Do not manually `gh release create`** — a pre-existing release collides with the
  workflow's own step.
- `pyproject.toml`'s `version` is never committed back and stays stale. Don't bump it.
- Release notes only include `feat` / `fix` / `refactor` / `perf` / `BREAKING` commits
  since the last tag; commitizen excludes chore/docs/ci/deps. Squash-merge PRs with a
  conventional title so they appear.
- Semver: `fix`/`refactor` → patch, `feat` → minor, `BREAKING CHANGE` → major.
- The changelog push-back needs `RELEASE_PAT` to bypass the master PR rule. If only that
  step fails, PyPI publish and the GitHub Release already succeeded.

## Exploring Smartschool endpoints

`dev/web_monitor.py` (`SmartschoolMonitor`) drives a real browser through the login chain
(login → birthday account verification → optional TOTP), visits any path, and records
every non-static network call plus response bodies, a screenshot and a DOM dump under
`dev/_captures/<path>/`. This is how `/mydoc` was mapped — use it to discover the
XHR/fetch API behind any part of Smartschool, or to confirm real-world behaviour.

```bash
python dev/web_monitor.py /mydoc /intradesk   # --headed, --fresh
```

Needs `credentials.yml` at the repo root (`main_url`/`username`/`password`/`mfa`
birthday/optional `totp`) and `pip install playwright && playwright install chromium`
(deliberately kept out of project deps). Login state is cached to a storage-state file so
reruns reuse the session — Smartschool rate-limits failed logins.

Captures hold real account data (response bodies, screenshots, DOM dumps), which is why
`dev/_captures/` is gitignored — scrub anything you lift out of one into `tests/requests/`.

## Stubs

`./restub` regenerates the `.pyi` files (`dev/generate_stubs.py`). CI regenerates and
auto-commits them, so run it after changing public signatures in a stubbed module
(`_agenda`, `_courses`, `_messages`, `_reports`, `_results`).

## CI notes

- Lint job runs `ruff check --no-fix .` and `ruff format --diff .` with the *latest*
  ruff, not the pinned one — a new rule can fail CI on untouched files.
- Tests run on Python 3.11 and 3.12 even though `pyproject.toml` declares `^3.10`.
- SonarCloud gates on new-code Reliability/Security; `sonar-project.properties` documents
  why each exclusion exists — read the comments there before adding one.
