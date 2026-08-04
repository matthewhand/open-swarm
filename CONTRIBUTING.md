# Contributing to Open Swarm

Thanks for your interest. Issues and PRs are welcome — this is an alpha-stage
project under active cleanup, so small, focused contributions land fastest.
Check [ROADMAP.md](ROADMAP.md) first: it lists what is broken, what is
half-finished, and where help is most useful.

## Development setup

Requirements: Python >= 3.10 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/matthewhand/open-swarm.git
cd open-swarm
uv sync --all-extras
```

`uv sync --all-extras` creates `.venv/` and installs the project plus the
`dev`, `test`, `memory`, and `docs` extras from the committed `uv.lock`.

The optional React frontend lives in `webui/frontend/` and needs Node >= 22:

```bash
cd webui/frontend && npm install && npm run build
```

You do not need the frontend for backend or blueprint work — Django falls
back to a template UI when no built `dist/` is present.

## Running tests

```bash
uv run pytest                 # full suite
uv run pytest tests/unit      # a subdirectory
uv run pytest -k spinner      # by keyword
```

Pytest is configured in `pyproject.toml` (Django settings, asyncio mode,
test paths). Some suites are skipped without API keys or optional services;
that is expected.

## Linting

```bash
uv run ruff check src tests
```

Ruff configuration (rule selection, line length) is in `pyproject.toml`.
Honest caveat: the existing codebase does not yet pass ruff cleanly, so the
expectation is that *the files you touch* are lint-clean — do not introduce
new warnings, and feel free to fix existing ones in code you are already
changing.

## Blueprint UX standards

Blueprints (the agent bundles under `src/swarm/blueprints/`) follow shared
conventions for spinner output, result boxes, and test-mode behaviour.
These are documented in
[docs/blueprint_test_mode_ux.md](docs/blueprint_test_mode_ux.md).

Two compliance scripts exist:

```bash
uv run python scripts/check_ux_compliance.py     # runs blueprints in SWARM_TEST_MODE and checks output
uv run python scripts/lint_blueprints.py <file>  # static checks on a blueprint source file
```

If you add or change a blueprint, run these and add or update its tests
under `tests/blueprints/`.

## Pull requests

- **Tests must pass**: `uv run pytest` succeeds, and `uv run ruff check` is
  clean on the files you changed.
- **Keep the lockfile in sync**: if you change dependencies in
  `pyproject.toml`, run `uv lock` and commit `uv.lock` — CI runs
  `uv lock --check` and fails on drift.
- **Conventional commits**, matching the existing history:
  `feat(webui): ...`, `fix(security): ...`, `docs(roadmap): ...`,
  `test: ...`, `chore: ...`, `refactor: ...`.
- **Small and focused**: one logical change per PR, with a short description
  of what changed and why.
- **Be honest in docs**: this project is mid-cleanup; do not document
  features as working unless they are (see `FEATURE_STATUS.md` for the
  current evidence-based audit).

## Where help is wanted

See [ROADMAP.md](ROADMAP.md), in particular:

- Test coverage for retained blueprints (§3.5)
- Release engineering and packaging (§3.6)
- Consolidating duplicate spinner/output implementations

If you are unsure whether something is worth doing, open an issue first and
ask.

## License

By contributing you agree your contributions are licensed under the MIT
license (see [LICENSE](LICENSE)).
