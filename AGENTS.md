# AGENTS.md

Onboarding notes for AI coding agents and humans working in this repo.

## What this repo is

`metatypes` is a thesis project evaluating **PEP 827 (Type Manipulation)**
as the shared substrate for an opt-in meta-typing layer in Python — a
way for library authors to generate precisely-typed APIs at the *type*
level (not just the value level), so that boilerplate CRUD models, sqlalchemy complex queries, numpy fixed lenght arrays, dynamically generated subclasses or typed dicts, can be expressed once and
stay statically checkable. The bigger story lives in [THESIS.md](THESIS.md).

## PEP 827 is the foundation

[PEP 827](https://peps.python.org/pep-0827/) proposes a small set of
*type-level* combinators — `Attrs[T]`, `Iter`, `Member[name, type]`,
`NewTypedDict[*Members]`, `IsAssignable`, `IsEquivalent`, `Slice`, … —
for building new types from existing ones, without new syntax.

## The two execution tracks

PEP 827 has two playgrounds:

- **Runtime track — `typemap`.** Annotations are first-class objects
  in Python. `typemap.type_eval.eval_typing(ModelDump[User])` returns
  the actual `TypedDict` class — with proper `__annotations__` and
  `__required_keys__` — by interpreting the PEP 827 combinators at
  call time. This is the substrate for dynamic class factories and
  introspection-based dispatch.

- **Static track — `mypy-typemap` plugin.** A custom mypy plugin
  understands the same combinators and evaluates them during
  type-checking, so call sites like
  `write_user(**u.model_dump())` validate without any runtime call.

Together these mean PEP 827 can be used in real projects *today*,
without waiting for language acceptance: users without the plugin
still get the runtime evaluator (no advanced static checks), users
with it get the full static experience. 

## Learn more

- [`WHY_METATYPES.md`](WHY_METATYPES.md) — the design rationale: how
  PEP 484 / 544 / 681 frame Python's typing surface, why a meta-typing
  layer is opt-in shared infrastructure rather than per-library
  plugins, and what the thesis is aiming for.
- [`THESIS.md`](THESIS.md)

## Important dependencies
`typemap` pinned to the iliyasone/python-typemap (fork) - runtime side of PEP 827
`mypy` pinned to the `msullivan/mypy-typemap` - static side of PEP 827

## How to run things

```bash
uv sync --all-groups
# Lint
uv run ruff check .

# Static type-check (this is the main banger — runs across the whole repo)
uv run mypy --warn-unused-ignores --show-error-codes --enable-error-code ignore-without-code .

# Run time type check
uv run pytest
```

`--warn-unused-ignores` is load-bearing: each `# type: ignore[<code>]` line
in the test files acts as a **negative assertion** ("this expression must
fail with exactly this error code"). If mypy stops emitting the error, the
ignore becomes unused and the run fails — that's how negative checks stay
honest.

## Building the thesis

```bash
# install dependencies 
sudo apt update
sudo apt install texlive-xetex texlive-latex-extra texlive-fonts-recommended
sudo apt install fonts-dejavu fonts-liberation
# build THESIS
pandoc THESIS.md -o THESIS.pdf --pdf-engine=xelatex
```


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
