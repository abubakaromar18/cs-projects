# 034 · CI Pipeline Template

A reusable **GitHub Actions** pipeline that lints, tests, builds and releases a
project, plus a small sample Python library (`slugkit`) so every stage has real
work to do. The workflow files are tested too: a policy test suite parses the
YAML and checks the pipeline's shape and security rules.

```
push / PR ──► lint ──► test (matrix: 3 Pythons × Linux, + macOS, Windows) ──► build ──► artifacts
tag v*.*.* ──► verify (tag == version, lint, test) ──► build ──► GitHub Release (dist/* attached)
```

## What's inside

| Path | Purpose |
|---|---|
| `.github/workflows/ci.yml` | Lint → test matrix → build, on every push to `main` and every PR |
| `.github/workflows/release.yml` | Tag-triggered release: version check, tests, build, `gh release create` |
| `.github/dependabot.yml` | Weekly update PRs for pinned actions and pip deps |
| `src/slugkit/` | Sample library + CLI that the pipeline builds and tests |
| `scripts/check_version.py` | Fails a release when the git tag ≠ `pyproject.toml` version |
| `tests/test_workflows.py` | Policy tests for the workflow YAML itself |
| `Makefile` | Runs the same steps locally (`make ci`) |

## Key concepts demonstrated

- **Pipelines as DAGs.** Jobs are linked with `needs:`; the tests check that every
  dependency exists and that the graph has no cycles (Kahn's topological sort).
- **Fail fast, cheap checks first.** Lint runs before the costly matrix; `build` only
  runs once lint *and* tests pass.
- **Matrix builds.** One job definition fans out across Python versions and OSes;
  `fail-fast: false` lets every cell report.
- **Least-privilege tokens.** Workflows default to `contents: read`; only the single
  `release` job gets `contents: write`.
- **Concurrency control.** CI cancels superseded runs; releases never cancel midway.
- **Caching and artifacts.** pip cache keyed on `pyproject.toml`; wheels and
  coverage reports pass between jobs as artifacts.
- **Reproducible releases.** Tag/version guard, smoke-test of the built wheel,
  auto-generated release notes.
- **Supply-chain hygiene.** Every `uses:` is pinned to a version or commit SHA, and
  Dependabot keeps those versions current.
- **Script-injection guard.** A test forbids expanding untrusted `github.event.*`
  values (PR titles, branch names) directly inside `run:` shells.

## Using the template

GitHub only runs workflows from the repository root, so these do **not** run inside
this monorepo folder. To use them:

1. Copy `.github/` into the root of your own repo.
2. Swap the Python commands for your stack (e.g. `npm ci && npm test`).
3. Push a branch / open a PR and watch the **Actions** tab.
4. Release: bump `version` in `pyproject.toml` (and `__version__`), then
   `git tag v0.2.0 && git push --tags`.

## Build, run, test locally

```bash
python -m venv .venv && source .venv/bin/activate
make install      # editable install + ruff + build
make ci           # lint, test (with 90% coverage gate), build
make actionlint   # optional, if actionlint is installed
```

Example:

```text
$ slugkit "Héllo, Wörld!"
hello-world
$ slugkit "the quick brown fox" --max-length 12
the-quick
$ python scripts/check_version.py v9.9.9
::error::tag 'v9.9.9' does not match pyproject version '0.1.0'
$ make test
36 passed in 0.32s
TOTAL  46  0  100%
```

The workflows were checked locally with the policy test suite. `actionlint` and an
actual GitHub run were not part of this build, so try a run in a scratch repo before
relying on it.

## Possible extensions

- Turn the CI into a **reusable workflow** (`on: workflow_call`) and call it from release.
- Publish to PyPI with **trusted publishing** (OIDC, `id-token: write`), no stored token.
- Add CodeQL / dependency-review jobs and a required-status-check branch protection rule.
- Upload coverage to a reporting service and fail PRs that lower it.
- Build and push a container image, with build provenance attestations.
