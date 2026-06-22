<!-- Copyright (c) 2026 @wimwian -->
<!-- SPDX-License-Identifier: MIT -->
<!-- https://github.com/wimwian-org/t2t -->
# Testing

## Stack

pytest + pytest-cov. Run via uv:

```bash
uv run pytest                                        # full suite (coverage enforced)
uv run pytest tests/test_color.py                   # single file
uv run pytest tests/test_color.py::TestColorRamp    # single class
uv run pytest -k "test_step_500"                    # by name pattern
uv run pytest --cov-report=term-missing             # show which lines are uncovered
```

## Pass criteria

**100% branch coverage is required.** `pyproject.toml` sets `--cov-fail-under=100`, so a plain `uv run pytest` fails if any line is uncovered. Tests are the gate — a PR that drops coverage below 100% does not pass.

The only lines excluded from measurement are those explicitly annotated `# pragma: no cover`. Use this annotation only for code that cannot be tested without mocking OS-level I/O:

- CLI entry points (`main()`)
- Subprocess calls (`_prettier()`)
- TTY-dependent terminal formatting (`print_summary()`, ANSI colour helpers)

Do not use `# pragma: no cover` to skip hard-to-test logic — write the test instead.

## Conventions

Tests are **class-based** — one class per public function or logical grouping, named `Test<Thing>`. Each method is a single assertion or closely related pair.

```python
class TestParseOklch:
    def test_basic(self): ...
    def test_invalid_raises(self): ...
```

Use `pytest.approx` for all float comparisons:

```python
assert L == pytest.approx(27.5)
assert C == pytest.approx(0.10)
```

## Integration vs. unit tests

- `tests/test_integration.py` tests the full pipeline via `main.convert()` and `main.convert_split()` — these are the two public entry points that bypass the CLI.
- Unit tests import directly from individual modules: `from t2t.color import color_ramp`.
- `main.main()`, `_prettier()`, `print_summary()`, and other I/O side-effect functions carry `# pragma: no cover` — test via `convert()` / `convert_split()` instead.

## What to test in new modules

1. Happy path with representative inputs.
2. Edge/boundary values (step 0, step 1000, empty dicts, missing optional keys).
3. Error paths — `ValueError` for bad input, `sys.exit` for hard failures (use `pytest.raises(SystemExit)`).
4. Float outputs use `pytest.approx`.