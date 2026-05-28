---
title: "A Meta-Type System for Python: An Expressive Library for Static Typing"
author: "Ilias Dzhabbarov"
date: "May 2026"
geometry: margin=2.5cm
fontsize: 11pt
linkcolor: blue
header-includes:
  - \usepackage{tikz}
  - \usetikzlibrary{arrows.meta, positioning, shapes.geometric, fit, calc}
  - \usepackage{caption}
  - \captionsetup[figure]{name=Fig., labelsep=period, font=small, labelfont=bf}
  - \usepackage{float}
  - \floatplacement{figure}{H}
---

## 3. Design and Methodology

### 3.1 System design

When PEP 827 (Type Manipulation) was published, the focus of this thesis shifted. The original goal of designing and testing an in-house meta-typing DSL gave way to evaluating the published proposal directly: exercising it through runtime checks, surfacing weaknesses and bugs, suggesting fixes, and verifying that the DSL holds up not only on toy examples, but on real production libraries.

The authors of PEP 827 provide two playgrounds for the proposed DSL. The first is the **typemap** runtime library, which operates on annotations as ordinary Python objects. The second, discussed in Section 3.2, is the **mypy-typemap plugin**, which evaluates the same combinators during static type-checking.

One might expect a runtime type evaluator to offer little value, given that the entire motivation for PEP 827 — and for this thesis — is to provide static analysis tools. That intuition is largely correct, yet it overlooks a property of Python that is central to the language: type annotations are first-class objects at runtime. They can be inspected, transformed, and used by frameworks to derive runtime behavior.

FastAPI is a standard example. A path operation function is not merely checked statically: FastAPI inspects its runtime signature. Parameter annotations are used to parse, validate, and document request data, while metadata carried through `typing.Annotated`, such as `Depends(...)`, is used to construct dependency injection behavior. For example:
```python
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

app = FastAPI()


def get_db() -> Session: ...


@app.get("/users")
def list_users(db: Annotated[Session, Depends(get_db)]) -> list[User]: ...
```

In this example, the annotation is not only a hint for a static type checker. It is part of the object inspected by the framework at runtime. FastAPI reads the function signature, recovers the `Annotated` metadata, resolves the dependency, and may also use the return annotation to derive the response model.


```python
from functools import singledispatch

type Json = dict[str, Json] | list[Json] | str | bool | float | int | None


@singledispatch
def render(node: Json) -> str:
    return repr(node)


@render.register
def _(node: dict) -> str:
    return "{ " + ", ".join(f"{k}: {render(v)}" for k, v in node.items()) + " }"


@render.register
def _(node: list) -> str:
    return "[" + ", ".join(render(v) for v in node) + "]"
```

The recursive alias `type Json = dict[str, Json] | list[Json] | str | bool | float | int | None` deserves its own remark: a complete, type-checkable specification of JSON values in a single line is a feature one usually associates with Haskell or OCaml, not with a dynamically typed scripting language. Modern Python typing is closer to that lineage than its reputation suggests.

— In the author's view, this single-line recursive alias is one of the most striking demonstrations of how far Python's type system has evolved; it earns its place in any introduction to the topic.

A more substantial example follows from the [FastAPI SQL-databases tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/#heroupdate-the-data-model-to-update-a-hero), which shows that three near-identical classes are required for the basic Create, Read, and Update operations of a Pydantic-backed CRUD API:

```python
class HeroBase(SQLModel):
    name: str = Field(index=True)
    age: int | None = Field(default=None, index=True)


class Hero(HeroBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    secret_name: str


class HeroPublic(HeroBase):
    id: int


class HeroCreate(HeroBase):
    secret_name: str


class HeroUpdate(HeroBase):
    name: str | None = None
    age: int | None = None
    secret_name: str | None = None
```

This thesis argues that the pattern is not Pythonic. Create, Read, and Update are boilerplate projections of a single underlying class; whether they should live under one namespace is a separate design discussion, with reasonable arguments on both sides. The point relevant here is more narrow: these classes can already be generated in Python at runtime, and have been for some time, by a function of roughly the following shape:

```python
HeroPublic = public_model(Hero)
HeroUpdate = update_model(Hero)
HeroCreate = create_model(Hero)
```

Such an approach has clear advantages and clear costs.

Advantages:

1) all benefits of a typed schema, such as dynamically generated API documentation;
2) substantially less boilerplate code.

Disadvantages:

1) broken static analysis: language servers no longer understand the generated classes;
2) typos and shape mismatches surface only at runtime, often in production.

The remainder of this chapter shows how the two PEP 827 playgrounds, taken together, allow both columns to be enjoyed (Fig. 1 anticipates the resulting picture and is discussed in full in Section 3.3.3).

### 3.2 Assumptions

The strength of the PEP 827 primitives is that they describe roles and actions: each combinator names what it does, and the combinators compose. This is closer to a convention than to a syntactic extension.

The second playground of PEP 827 is the **mypy-typemap plugin**, the piece that bridges Python's dynamic runtime with static checkability. The plugin has nothing to do with runtime; it is a tool for linting and static analysis only. Mypy has a long history of plugins that teach the checker about advanced patterns in specific libraries. The PEP 827 plugin can be viewed as the *last* such plugin mypy needs, in the sense that most other plugin behaviours can be reduced to PEP 827 combinators.

The plugin therefore restores the missing side: static analysis.

While mypy is not the fastest checker and does not currently provide language-server support — both of which matter to modern developers — it serves as a credible proof of concept and as a tool already usable in real projects.

The relevant components can be stated compactly:

1) the typemap runtime provides the tools for evaluating types at runtime;
2) the mypy-typemap plugin provides the corresponding static evaluator;
3) PEP 827 requires no syntactic change to the Python language.

These three together let projects adopt the typemap DSL today, without waiting for PEP 827 to be accepted into the language. A developer who installs only the runtime obtains dynamic evaluation; a developer who additionally installs the mypy plugin obtains the full static experience. The runtime evaluator is an ordinary dependency, and the static checker is an ordinary developer tool.

— The most underappreciated property of this design, in the author's view, is that it does not ask Python to change; it composes with the language as it already exists, so individual libraries may begin benefiting without waiting on a PEP cycle.

This combination unlocks advanced type manipulation starting today.

### 3.3 Problems and simplifications

#### 3.3.1 Duality of Python annotations: static versus runtime

The central difficulty encountered while exercising the typemap DSL is the **genuine semantic gap** between annotations as static artefacts and annotations as runtime values. This is the point at which critics of Python typing tend to feel vindicated.

The constant `typing.TYPE_CHECKING` evaluates to `False` at runtime and to `True` during static analysis. It was introduced in 2016 (see [python/typing issue #230](https://github.com/python/typing/issues/230)) to address two narrow problems:

1) lazy imports of heavy libraries that are referenced only in annotations;
2) forward references to self and to classes not yet declared at the point of use.

Over time, however, `TYPE_CHECKING` has acquired a third and far more powerful use: *declaring entire classes that exist only for the type-checker*. A class defined under `if TYPE_CHECKING:` is visible to mypy and to other static tools, yet absent from the module globals at runtime. The test suite of this thesis exercises that case directly (see `tests/test_pydantic_extension.py`, the `HiddenAtRuntime` block):

```python
if TYPE_CHECKING:

    class HiddenAtRuntime(BaseModel):
        secret: str


def mypy_test_type_checking_only_class_visible_to_mypy() -> None:
    if TYPE_CHECKING:
        h = HiddenAtRuntime(secret="x")
        assert_type(h.model_dump()["secret"], str)
```

The static side type-checks cleanly; the runtime side cannot even resolve the name `HiddenAtRuntime`. This asymmetry is exactly what the PEP 827 plugin must reason about: any meta-type that takes such a class as its argument has a well-defined static meaning and no runtime counterpart. The corresponding runtime test is marked `xfail(strict=True)` precisely to document this limit and to keep it visible in the pytest report.

#### 3.3.2 TypeAliases are not runtime classes

The expression `Create[Hero]` evaluates, under the typemap runtime, to a structure of the form

```python
class Create[__main__.Hero]:
    name: str
    age: int | None = None
    secret_name: str
```

The subtle point is that the result is a `TypeAlias`, not a runtime class. Therefore `Create[Hero]()` cannot be used directly to construct an instance. This is not a serious obstacle, because Pydantic already provides a runtime API (`pydantic.create_model`) for synthesising classes from a field specification. Once a `Create[Hero]` alias is in hand, lifting it into an instantiable class is mechanical:

```python
def create_model[T](model: type[T]) -> type[T]:
    ...
    return pydantic.create_model(...)
```

The implementation is in progress and remains one of the open tasks of this thesis.

#### 3.3.3 The triumvirate of Python type systems

Python is best understood as carrying three partially overlapping type systems.

First, **structural typing**, also known as duck typing or protocol typing. The principle is captured by the phrase *"if it behaves like a duck, it is a duck"*; structural typing arguably predates the static layer and is the most natural style for the language.

```python
class Duck(Protocol):
    name: str

    def migrate(self) -> None: ...


def prepare_for_winter(duck: Duck) -> None:
    print("Duck %s moving to the South" % duck.name)
    duck.migrate()


class Database:
    user: str
    password: str
    ip: str
    port: str
    name: str

    def migrate(self) -> None: ...


prepare_for_winter(Database())  # accepted; no static warning
```

One may reasonably argue that this is not an error: `prepare_for_winter` declared a structural interface and the `Database` class happens to satisfy it. Whether explicit or implicit interfaces are preferable is a separate discussion. The PEP 827 combinator that lifts this layer to the meta level is `NewProtocol`.

Second, **TypedDict-based subtyping**. The relation `{"name": str, "age": int} <: {"name": str}` holds, while `{"name": str}` is *not* a subtype of an arbitrary `dict`. The PEP 827 combinator for this layer is `NewTypedDict`.

Third, **nominal typing**, by class hierarchy. PEP 827 currently provides no general meta combinator for this layer. The proposal sketches one, `NewProtocolWithBases[Bases: tuple[type], *Ms: Member]`, but no implementation is yet available. A direct consequence is that `Create[Hero]` is not statically a Pydantic model: it is structurally compatible with one, yet the nominal relationship cannot yet be expressed at the meta level.

\begin{figure}[H]
\centering
\begin{tikzpicture}[
  node distance=7mm and 22mm,
  box/.style={draw, rectangle, rounded corners=2pt, minimum width=3.6cm, minimum height=10mm, align=center, font=\small},
  dashedbox/.style={box, dashed},
  group/.style={draw, rectangle, dashed, inner sep=10pt, rounded corners=4pt, fill=gray!5},
  lift/.style={->, dashed, >=Stealth, thick}
]
\node[box] (S) {Structural / Protocol\\(PEP 544)};
\node[box, below=of S] (T) {TypedDict\\(PEP 589)};
\node[box, below=of T] (N) {Nominal\\(PEP 484)};

\node[box, right=of S] (NP) {NewProtocol};
\node[box, right=of T] (NTD) {NewTypedDict};
\node[dashedbox, right=of N] (NPB) {NewProtocolWithBases\\(proposed, not implemented)};

\draw[lift] (S) -- node[midway, above, font=\scriptsize]{lifts to} (NP);
\draw[lift] (T) -- node[midway, above, font=\scriptsize]{lifts to} (NTD);
\draw[lift] (N) -- node[midway, above, font=\scriptsize]{lifts to} (NPB);

\node[group, fit={(S)(T)(N)}, label={[font=\small\bfseries]above:Python static type system}] {};
\node[group, fit={(NP)(NTD)(NPB)}, label={[font=\small\bfseries]above:PEP 827 meta-level}] {};
\end{tikzpicture}
\caption{The three coexisting type systems in Python and their PEP 827 counterparts at the meta level. The dashed node marks the meta combinator that the proposal sketches but does not yet implement.}
\end{figure}

— Working with these three layers in parallel is, in the author's experience, the single largest source of pathological corner cases in Python typing; gradual standardisation, one combinator at a time, is the realistic path forward. TypeScript's advanced type manipulation did not arrive in a single release either.

## 4. Implementation and Results

### 4.1 Implementation

The implementation began with typing the result of `pydantic.BaseModel.model_dump()`. The current state of the work is that the resulting `TypedDict` is inferred correctly for the basic, the inherited, and the empty-model cases (see `tests/test_pydantic_extension.py`, sections labelled *leaf dump fields*, *inherited fields in dump*, *empty model has no keys*, and *pydantic internals filtered*).

The choice of `model_dump()` rather than, for instance, `model_validate()`, deserves a short justification. The essence of Pydantic is that `model_validate` is a *type guard*: it takes an untyped input and produces either a typed object or a validation error. Adding a precise input type to `model_validate` therefore works against the very property that makes the function useful. By contrast, `model_dump()` flows in the opposite direction, from a typed object to an untyped dictionary, and is exactly the case where a precise output type recovers information that would otherwise be lost.

A counter-argument is that typing the result of `model_dump()` is not useful, since a dump is most often serialised to storage. This thesis disagrees. The most compelling use case is *passing a dump as keyword arguments to a downstream function*:

```python
def write_with_extra(*, name: str, age: int, extra: str) -> None: ...


u = User(name="i3s", age=22)
write_with_extra(**u.model_dump())  # rejected; would be impossible without PEP 827
```

The fixtures `User`, `Admin`, and `Empty` used throughout the test suite are deliberately minimal:

```python
from pydantic_extension import BaseModel


class User(BaseModel):
    name: str
    age: int


class Admin(User):
    role: str


class Empty(BaseModel):
    pass
```

The signature definition itself is short:

```python
type ModelDump[T] = typing.NewTypedDict[
    *[
        typing.Member[field.name, field.type]
        for field in typing.Iter[typing.Attrs[T]]
        if typing.IsAssignable[field.definer, _BaseModel]
        and not typing.IsEquivalent[field.definer, _BaseModel]
        and not typing.IsEquivalent[
            typing.Slice[field.name, Literal[0], Literal[2]], Literal["__"]
        ]
    ]
]
```

Three concrete issues surfaced while exercising this definition against the typemap runtime:

1) the runtime entry point `eval_call_with_types` carried a broken type-hint signature; this was fixed by [PR #117](https://github.com/vercel/python-typemap/pull/117), which has since been merged into `vercel/python-typemap`;
2) `Attrs[T]` evaluated the methods of a class in addition to its attributes, which is inconsistent with the documented behaviour and may cause spurious failures when methods carry `if TYPE_CHECKING:`-only annotations; this is tracked in open [PR #122](https://github.com/vercel/python-typemap/pull/122);
3) the `Self` type is not substituted into the bound class during runtime evaluation, which prevents `eval_call_with_types(User.model_dump, User)` from succeeding; this is tracked in [Issue #123](https://github.com/vercel/python-typemap/issues/123) and is currently under investigation.

— In the author's experience working through these three issues, the `Self`-substitution gap proved the most consequential in practice; it is what currently forces the test suite to address `ModelDump[User]` as a *type alias* rather than as the return type of the bound method `User.model_dump`.

### 4.2 Structure of `ModelDump[T]`

`ModelDump[T]` walks the attributes of `T` and, for each attribute `field`, emits a `Member[field.name, field.type]` only when three conditions hold:

1) the field is defined on `pydantic.BaseModel` or on a subclass of it — that is, `IsAssignable[field.definer, _BaseModel]`, which on the type level is the equivalent of `issubclass` on the value level;
2) the field is *not* defined directly on `pydantic.BaseModel` itself, which removes the framework's internal fields such as `model_config`;
3) the field name does not begin with two underscores, which removes dunder attributes.

```python
typing.NewTypedDict[
    *[
        typing.Member[field.name, field.type]
        for field in typing.Iter[typing.Attrs[T]]
        if typing.IsAssignable[field.definer, _BaseModel]
        and not typing.IsEquivalent[field.definer, _BaseModel]
        and not typing.IsEquivalent[
            typing.Slice[field.name, Literal[0], Literal[2]], Literal["__"]
        ]
    ]
]
```

The condition on `field.definer` is the load-bearing piece, because in Python a "field of a class" is genuinely a field of *some* class along the MRO, not of the leaf class as a whole. The following minimal example makes the point:

```python
class A:
    bad_class_var_const = 1


class B(A):
    pass


B.bad_class_var_const += 1
A.bad_class_var_const  # 1 or 2?
```

After the in-place addition, `A.bad_class_var_const` is still `1`, while `B.bad_class_var_const` is `2`. The lookup `B.bad_class_var_const` on the right-hand side returned `A`'s class variable; the increment produced a new integer; the assignment installed the result on `B` rather than on `A`. The class dictionaries make the effect visible directly:

```python
>>> A.__dict__
mappingproxy({'__module__': '__main__',
              '__firstlineno__': 1,
              'bad_class_var_const': 1,
              '__static_attributes__': (),
              '__dict__': <attribute '__dict__' of 'A' objects>,
              '__weakref__': <attribute '__weakref__' of 'A' objects>,
              '__doc__': None})
>>> B.__dict__
mappingproxy({'__module__': '__main__',
              '__firstlineno__': 11,
              '__static_attributes__': (),
              '__doc__': None,
              'bad_class_var_const': 2})
```

\begin{figure}[H]
\centering
\begin{tikzpicture}[
  node distance=7mm,
  box/.style={draw, rectangle, rounded corners=2pt, minimum width=7cm, minimum height=10mm, align=center, font=\small},
  arrow/.style={->, >=Stealth, thick}
]
\node[box] (inst) {instance attribute lookup\\\texttt{obj.name}};
\node[box, below=of inst] (mro) {walk \texttt{type(obj).\_\_mro\_\_}};
\node[box, below=of mro] (chk) {for each class C in the MRO,\\check \texttt{'name' in C.\_\_dict\_\_}};
\node[box, below=of chk] (hit) {first hit returns (C, value)};
\node[box, below=of hit] (attrs) {\texttt{Attrs[T]} therefore walks the MRO,\\not \texttt{T.\_\_dict\_\_} alone};

\draw[arrow] (inst) -- (mro);
\draw[arrow] (mro) -- (chk);
\draw[arrow] (chk) -- (hit);
\draw[arrow] (hit) -- (attrs);
\end{tikzpicture}
\caption{Attribute resolution on instances and the reason \texttt{Attrs[T]} is defined to walk the MRO rather than only the leaf class. Each attribute is owned by exactly one class along the chain --- its \texttt{definer} --- and the filters in \texttt{ModelDump[T]} are predicated on that ownership.}
\end{figure}

— The asymmetry between class-level and instance-level attribute resolution is, in the author's view, the single most underappreciated detail in Python's data model; it is exactly the reason `Attrs[T]` must inspect every base class along the MRO rather than the leaf's `__dict__` alone.

The forward-looking signature of `model_dump` accepts a substantial set of keyword arguments — `mode='json'`, `include=`, `exclude=`, `by_alias=`, `exclude_unset=`, `exclude_defaults=`, `exclude_none=`, `exclude_computed_fields=`, `round_trip=`, and the opaque kwargs `context=`, `fallback=`, `warnings=`, `serialize_as_any=`, `polymorphic_serialization=`. None of these currently narrows the resulting `TypedDict`. The file `tests/test_model_dump_kwargs.py` serves as the *static specification* for each of them: every kwarg with a well-defined static meaning is captured as an `mypy_test_<kwarg>` paired with an `xfail(strict=True)` runtime test, so that the moment the static layer learns to narrow that kwarg the corresponding `# type: ignore[assert-type]` becomes unused and `--warn-unused-ignores` flags it. The opaque kwargs (`context=`, `fallback=`, etc.) are marked `pytest.mark.skip` with an explanation, because they cannot in principle be statically reflected: their effect depends on runtime values supplied by user code.

### 4.3 Testing setup

#### 4.3.1 Duality of the tests

Because annotations have two distinct meanings in Python, the test suite carries two kinds of tests next to each other:

1) **runtime evaluation tests.** These are the source of truth for the typemap playground; annotations in Python are not erased at runtime and are used for dynamic reasoning, which makes their runtime semantics directly observable.
2) **static mypy tests.** These describe how most users will interact with the types, since most tools and libraries do not inspect annotations dynamically; developers see warnings and type errors in their editor and in CI rather than in `pytest` output.

The author chose to keep both kinds in ordinary function definitions, with the mypy variant wrapped in `if TYPE_CHECKING:` to make the static-only nature explicit. A side-by-side example follows:

```python
def mypy_test_leaf_dump_fields() -> None:
    if TYPE_CHECKING:
        u = User(name="i3s", age=22)
        dump = u.model_dump()
        assert_type(dump["name"], str)
        assert_type(dump["age"], int)


def test_leaf_dump_fields() -> None:
    dump_type = eval_typing(ModelDump[User])
    assert dump_type.__annotations__["name"] is str
    assert dump_type.__annotations__["age"] is int
```

The runtime test uses `ModelDump[User]` directly via `eval_typing` rather than `eval_call_with_types(User.model_dump, User)`, because the latter path is the one currently affected by Issue #123 (`Self` substitution).

The function `mypy_test_leaf_dump_fields` has no runtime effect. When mypy enters its body it checks that the inferred type matches each `assert_type`; a mismatch raises a static error during the lint stage. The function `test_leaf_dump_fields` is an ordinary pytest test that evaluates the same definition at runtime and confirms that the resulting annotations agree.

The convention has three pieces:

1) static and runtime tests sit next to each other, one pair per feature;
2) mypy-test bodies are wrapped in `if TYPE_CHECKING:` so the static-only nature is explicit at the call site;
3) functions whose names do not begin with `test_` are not collected by pytest, by convention.

The benefit of this arrangement is that a single command runs mypy and pytest over the whole codebase, so that both layers stay in agreement on every file.

#### 4.3.2 Negative tests

Expected failures are simple in pytest; with the mypy half of the suite they require slightly more care. The question is how to mark that something does *not* type-check, how to detect when the negative assertion silently flips to a positive (which would be welcome but must not pass unnoticed), and how to enforce all of this with a tool that only emits lint diagnostics.

The configuration relies on two mypy flags:

```bash
uv run mypy --warn-unused-ignores --enable-error-code ignore-without-code .
```

The flag `--warn-unused-ignores` makes mypy report an error whenever a `# type: ignore` comment is no longer needed. The flag `--enable-error-code ignore-without-code` forbids bare `# type: ignore`, so that every ignored line must carry a specific error code.

Together, the two flags turn `# type: ignore[<code>]` into a *negative assertion*: the test asserts that mypy emits exactly `<code>` on this line. When the assertion holds, the ignore consumes the error and the run succeeds. When the assertion silently flips — that is, when mypy no longer emits `<code>` — the ignore becomes unused and the run fails, forcing the maintainer to remove the mark and acknowledge that the previously failing case now passes.

\begin{figure}[H]
\centering
\begin{tikzpicture}[
  node distance=9mm and 13mm,
  box/.style={draw, rectangle, rounded corners=2pt, align=center, font=\scriptsize, text width=3.2cm, minimum height=14mm},
  decision/.style={draw, diamond, aspect=1.8, align=center, font=\scriptsize, inner sep=1pt, text width=2.4cm},
  arrow/.style={->, >=Stealth}
]
\node[box] (src) {source line:\\\texttt{x = f()}\\\texttt{\# type: ignore[arg-type]}};
\node[box, right=of src] (mypy) {\texttt{uv run mypy}\\\texttt{-{}-warn-unused-ignores}\\\texttt{-{}-enable-error-code}\\\texttt{ignore-without-code}};
\node[decision, right=of mypy] (q) {does mypy still emit error code `arg-type' on this line?};
\node[box, above right=of q] (ok) {ignore consumed; negative assertion holds; exit 0};
\node[box, below right=of q] (fail) {ignore unused; negative assertion violated; exit non-zero};

\draw[arrow] (src) -- (mypy);
\draw[arrow] (mypy) -- (q);
\draw[arrow] (q) -- node[above, font=\scriptsize, sloped]{yes} (ok);
\draw[arrow] (q) -- node[below, font=\scriptsize, sloped]{no} (fail);
\end{tikzpicture}
\caption{The negative-test workflow. Each \texttt{\# type: ignore[<code>]} line acts as an assertion that mypy still emits \texttt{<code>} on that line; \texttt{-{}-warn-unused-ignores} flips the assertion to a failure the moment the underlying error disappears.}
\end{figure}

#### 4.3.3 Comparison with alternative testing setups

Because the project aims to expose issues that arise when established Python libraries are used through PEP 827, the unit of investigation must remain as close as possible to ordinary library code. Three families of approach were considered for testing the static behaviour of such code:

1) **subprocess-driven testing**, in which a pytest fixture launches `mypy` as an external process against a temporary file or a string snippet, parses its standard output, and asserts on the diagnostics;
2) **API-driven testing**, in which the same work is done in-process via `mypy.api.run`, which returns the lint output as a triple of strings;
3) **in-file testing**, the approach adopted in this thesis, in which negative assertions are encoded as `# type: ignore[<code>]` markers on ordinary Python source and enforced by `--warn-unused-ignores` together with `--enable-error-code ignore-without-code`.

The three approaches involve different trade-offs. Subprocess-driven and API-driven approaches scale well to large negative-test suites, can target a single snippet at a time, and produce structured diagnostics that are convenient to assert on. They do not, however, integrate naturally with the editor: the test file is, from the editor's perspective, ordinary Python that happens to contain string-typed snippets, so the static analysis the developer sees while writing the test does not match the analysis the test fixture will eventually run. The in-file approach inverts that trade-off. Each test is a real Python function that mypy, pytest, and the editor all see in the same way, which makes the test as readable as ordinary code and as discoverable as any other pytest case. The cost is one global mypy flag (`--warn-unused-ignores`) and a stricter rule on comments (`--enable-error-code ignore-without-code`), both of which apply uniformly to the codebase.

For a project whose explicit goal is to exercise PEP 827 against established Python libraries, the in-file approach was selected because it keeps the unit of investigation — a real Python function consuming a real library — identical between the static and runtime layers. This is the property that allows a single test file to serve simultaneously as the static specification and as the runtime regression test.

— What this setup does *not* yet evaluate, the author wishes to note, is whether the same approach scales to a project with hundreds of negative assertions distributed across many independent files; that question is left to future work, once the static layer accumulates a broader catalogue of meta-types.
