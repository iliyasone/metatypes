# AGENTS.md

Onboarding notes for AI coding agents and humans working in this repo.

## What this repo is

`metatypes` is a thesis project designing an opt-in **meta-typing layer** for
Python. The `pydantic_extension` package is the flagship case study: a
`BaseModel` whose `model_dump()` returns a precisely-typed `TypedDict`
(`ModelDump[Self]`) instead of `dict[str, Any]`.

## Read these first

Before making non-trivial changes, read:

- [`WHY_METATYPES.md`](WHY_METATYPES.md) — the design rationale: how PEP
  484 / 544 / 681 frame Python's typing surface, why a meta-typing layer is
  opt-in shared infrastructure rather than per-library plugins, and what the
  thesis is aiming for.
- [PEP 827](https://peps.python.org/pep-0827/) — ....

## Important dependencies

- **`typemap`** — pinned to the `develop` branch of
  `iliyasone/python-typemap` (fork). Provides
  `typemap.type_eval.eval_typing`, `eval_call_with_types`, and the
  `typemap_extensions` namespace (`Attrs`, `Iter`, `Member`, `NewTypedDict`,
  `IsAssignable`, `IsEquivalent`, `Slice`, …).
- **`mypy`** — pinned to the `msullivan/mypy-typemap` fork. A custom mypy
  plugin understands the metatypes DSL and evaluates type-level
  combinators. Standard mypy will not type-check this codebase correctly.
- **`pydantic`** — 2.13+. Standard.

## How to run things

```bash
# Lint
uv run ruff check .

# Static type-check (this is the main banger — runs across the whole repo)
uv run mypy --warn-unused-ignores --show-error-codes --enable-error-code ignore-without-code .

# Tests (runtime side)
uv run pytest
```

`--warn-unused-ignores` is load-bearing: each `# type: ignore[<code>]` line
in the test files acts as a **negative assertion** ("this expression must
fail with exactly this error code"). If mypy stops emitting the error, the
ignore becomes unused and the run fails — that's how negative checks stay
honest.

## Test conventions

- **One concern per test function**; descriptive names.
- **Static and runtime tests are paired by feature, side by side.** For a
  feature `X`, two adjacent functions:
  - `mypy_test_X` — type-only. Body wrapped in `if TYPE_CHECKING:`, so it
    never executes at runtime. The `mypy_` prefix means pytest does **not**
    collect it. Mypy still type-checks the body. Uses `assert_type` for
    positives and `# type: ignore[<code>]` for negatives.
  - `test_X` — runtime. Uses `typemap.type_eval.eval_typing` /
    `eval_call_with_types` plus direct introspection (`__annotations__`,
    `__required_keys__`, `issubclass`).

- **Do not** assert against multi-line `textwrap.dedent("""…""")` blobs of
  `format_helper.format_class` output. They are fragile and unreadable. Use
  direct introspection instead.
- Use `pytest.mark.xfail(reason="…", strict=True)` for "we want this to
  work, it doesn't yet" (so when it eventually passes, `strict=True` flips
  it to a failure and forces us to remove the mark).
- Use `pytest.mark.skip(reason="…")` only for "this can never be reflected
  statically at all" (e.g. `model_dump(context=…)`, `fallback=…`).

