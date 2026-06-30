---
title: "A Meta-Type System for Python: An Expressive Library for Static Typing"
author: "Ilias Dzhabbarov"
date: "May 2026"
documentclass: extarticle
classoption:
  - titlepage
papersize: a4
geometry:
  - left=25mm
  - right=20mm
  - top=20mm
  - bottom=20mm
  - includefoot
fontsize: 14pt
mainfont: "Times New Roman"
colorlinks: true
linkcolor: black
urlcolor: black
citecolor: black
toccolor: black
toc: true
toc-depth: 3
numbersections: true
include-before:
  - \setcounter{page}{2}
header-includes:
  - \usepackage{tikz}
  - \usetikzlibrary{arrows.meta, positioning, shapes.geometric, fit, calc, backgrounds}
  - \usepackage{float}
  - \floatplacement{figure}{H}
  - \input{latex/innopolis-format.tex}
---

# Abstract {.unnumbered}

Python's static type system cannot express types produced by metaprogramming, yet dynamically manipulating classes has been a native feature since day one.

PEP 827 proposes new type manipulation facilities to fill this gap, but whether they are sufficient for all cases remains unknown. This thesis has addressed that question by developing tysql, a PostgreSQL query builder whose result types can be statically inferred — a capability previously unattainable in Python. The tool is available now: `pip install tysql`.

tysql is usable today:
- It statically infers the result type of every SQL statement and rejects ill-typed statements with a type error, using the type operators from PEP 827.
- It capable of inserting type hints into existing code to infer result types of SQL statements in a pre-PEP 827 world, and it and ships a CLI validator that raises errors in the same places any type checker would once PEP 827 lands.

# Introduction

Python's type system is Turing-complete, yet in everyday use it is far less expressive than the language it describes. Classes are created, inspected, and rewritten while the program runs; the type system was added much later and has been catching up ever since. That history shows up as three ways type information is *used*, each building on the one before it.

**Metaprogramming came first.** Long before type hints, Python already rewrote classes at runtime. `enum.Enum` is the clearest case: its metaclass turns plain class-body assignments into singleton member objects.

```python
class Color(enum.Enum):
    RED = 1
    GREEN = 2
    BLUE = 3
```

`EnumMeta` rewrites the body, so an assignment like `RED = 1` no longer holds the integer `1` but a distinct `Color` member. The interactive shell shows what each name became:

```python
>>> Color.RED
<Color.RED: 1>
>>> Color.RED.name, Color.RED.value
('RED', 1)
>>> list(Color)
[<Color.RED: 1>, <Color.GREEN: 2>, <Color.BLUE: 3>]
>>> Color(99)
ValueError: 99 is not a valid Color
```

With no static checking at all, an enum already provides a distinct object rather than a bare `int`, identity comparison, a readable `repr`, `.name` and `.value`, iteration, and runtime rejection of invalid values. The static benefit — a checker enforcing `def paint(c: Color)` and proving a `match` exhaustive — arrived later, with PEP 484. It was a bonus, not the original reason.

**Static checking came next.** Type hints added a second layer that a checker reads and then erases. Because the checker knows `c` is a `Color`, it can prove the `match` below covers every member, with no fallback case:

```python
def is_warm(c: Color) -> bool:
    match c:
        case Color.RED:
            return True
        case Color.GREEN | Color.BLUE:
            return False
    typing.assert_never(c)
```

The closing `assert_never(c)` makes the guarantee explicit: it type-checks only because the checker has narrowed `c` to `Never`, proving every member is handled. Add a fourth color without a branch and `c` is no longer `Never`, so `assert_never` is flagged as a static error.

**Annotations live at runtime, too.** A class is itself an ordinary runtime object,

```python
>>> int
<class 'int'>
```

and an annotation is a reference to such an object. Python keeps annotations in the object model, so libraries can read them back and act on them:

```python
>>> is_warm.__annotations__
{'c': <enum 'Color'>, 'return': <class 'bool'>}
>>> is_warm.__annotations__['c'](1)
<Color.RED: 1>
```

The annotation for `c` is the runtime object class `Color`. It can even be called to construct a member. The brightest example of this is FastAPI, which reads a route's signature to validate requests and to generate its API documentation:

```python
from fastapi import FastAPI
from pydantic import BaseModel

api = FastAPI()


class User(BaseModel):
    id: int
    age: int
    email: str


@api.get("/v1/users/{user_id}")
def get_user(user_id: int) -> User: ...
```

From nothing but these annotations, FastAPI derives the interactive documentation in Fig. 1 — the path, the `user_id` parameter, and the full `User` response schema.

![The interactive API documentation FastAPI generates at runtime from the annotations above.](images/fastapi-swagger.png){ width=88% }

## Current gap

Three decades of work made Python's annotations remarkably capable. Yet one class of types still escapes them: the result of a database query. SQLAlchemy is at once the clearest showcase of annotation-driven runtime behaviour and the clearest demonstration of where it stops.

A relational database stores rows of named, typed columns across related tables. The running example has three (Fig. 2): every post and comment belongs to a user, and every comment belongs to a post.

\begin{figure}[H]
\centering
\begin{tikzpicture}[
  font=\small,
  entity/.style={rectangle, draw, thick, inner sep=4pt, fill=gray!4},
  rel/.style={draw, thick, -{Stealth[length=2mm, width=2mm]}},
]
\node[entity] (users) {%
  \begin{tabular}{@{}l@{\hspace{1.6em}}l@{}}
    \multicolumn{2}{@{}l@{}}{\bfseries users}\\ \hline
    \textit{PK} & id\\ \hline
     & email\\
     & registered\_at\\
  \end{tabular}};
\node[entity, right=20mm of users] (posts) {%
  \begin{tabular}{@{}l@{\hspace{1.6em}}l@{}}
    \multicolumn{2}{@{}l@{}}{\bfseries posts}\\ \hline
    \textit{PK} & id\\
    \textit{FK} & author\_id\\ \hline
     & created\_at\\
  \end{tabular}};
\node[entity, right=20mm of posts] (comments) {%
  \begin{tabular}{@{}l@{\hspace{1.6em}}l@{}}
    \multicolumn{2}{@{}l@{}}{\bfseries comments}\\ \hline
    \textit{PK} & id\\
    \textit{FK} & post\_id\\
    \textit{FK} & author\_id\\ \hline
     & created\_at\\
  \end{tabular}};
\draw[rel] (posts.west) -- node[above, font=\footnotesize]{author\_id} (users.east);
\draw[rel] (comments.west) -- node[above, font=\footnotesize]{post\_id} (posts.east);
\draw[rel] (comments.south) -- ++(0,-7mm) -| node[pos=0.25, below, font=\footnotesize]{author\_id} (users.south);
\end{tikzpicture}
\caption{The example schema. \texttt{posts} and \texttt{comments} reference \texttt{users}, and \texttt{comments} reference \texttt{posts}, by foreign key.}
\end{figure}

How such a table is declared in Python changed fundamentally between SQLAlchemy's two eras (Fig. 3). The 2008 style kept a column's type in the assigned *value*, `Column(Integer)`, with no annotation on the attribute. The 2.0 redesign (2023) moved the type into the *annotation* `Mapped[int]` and reads it back at runtime to build the mapper — so the annotation stopped being a passive hint and started changing runtime behaviour, and a checker now reads `User.id` as `int`. This is runtime introspection of annotations at its most ambitious.

\begin{figure}[H]
\centering
\begin{minipage}[t]{0.46\linewidth}
\centering
\textbf{\small SQLAlchemy 0.x (2008)}\\[4pt]
\begin{Verbatim}[fontsize=\small, frame=single, framesep=5pt]
class User(Base):
    id = Column(Integer)
    email = Column(String)
\end{Verbatim}
\end{minipage}\hfill
\begin{minipage}[t]{0.46\linewidth}
\centering
\textbf{\small SQLAlchemy 2.0 (2023)}\\[4pt]
\begin{Verbatim}[fontsize=\small, frame=single, framesep=5pt]
class User(Base):
    id: Mapped[int]
    email: Mapped[str]
\end{Verbatim}
\end{minipage}
\caption{The same \texttt{users} table in SQLAlchemy 0.x (2008, left) and 2.0 (2023, right): the column's type moves out of the runtime \emph{value} \texttt{Column(Integer)} and into the \emph{annotation} \texttt{Mapped[int]}, which 2.0 reads back to build the column.}
\end{figure}

And yet the gap survives exactly here. A query that projects specific columns loses the column names from its type:

```python
row = session.execute(select(User.id, User.email)).one()
reveal_type(row[0])
reveal_type(row.id)
```

A checker reports `int` for `row[0]` but `Any` for `row.id`: the value is typed only by position, never by name. SQLAlchemy 2.0 gives this projection the type `Row[tuple[int, str]]` — the column names are gone.

A subtler version of the same blind spot appears with relationships. Once the foreign keys of Fig. 2 are declared as ORM relationships, they can be traversed as ordinary attributes:

```python
class User(Base):
    posts: Mapped[list[Post]] = relationship()


class Post(Base):
    author: Mapped[User] = relationship()
    comments: Mapped[list[Comment]] = relationship()
```

Now select a single post and follow the relationships back out:

```python
post = session.scalars(select(Post).where(Post.id == 1)).one()
reveal_type(post.author.posts[0].comments)
```

The checker resolves `post.author.posts[0].comments` to `list[Comment]` — every link is a declared relationship, so the entire chain type-checks. But `select(Post)` fetched a single `posts` row; the post's `author`, that author's other `posts`, and their `comments` were never loaded. The static type asserts a fully materialised object graph the query never produced — at runtime each step either fires another query (lazy loading) or raises on a closed session. Nothing in the result type records what a query actually fetched.

Both failures share one root: the result type is declared up front, never computed from the query that produces it. Computing it from the query instead — so a `SELECT` yields a precise record such as `{"id": int, "email": str}`, naming exactly the columns it returns, and an ill-typed query becomes a type error — is what PEP 827's type manipulation makes possible, and what the rest of this thesis builds and measures.

# Design and methodology

## Two meanings of an annotation: `typing.TYPE_CHECKING`

`typing.TYPE_CHECKING` is a constant that is `True` while a type checker analyses the code and `False` when the program runs. It was introduced for lazy imports and forward references, but it also lets a name exist for the checker and not at runtime — which is exactly where the two readings of an annotation come apart:

```python
if typing.TYPE_CHECKING:

    class Hidden:
        value: int


def build() -> Hidden:
    return Hidden()
```

The checker accepts `build` — `Hidden` is in scope statically — yet the class is never defined at runtime, so calling `Hidden()` raises `NameError`. A meta-type can therefore carry a precise static meaning with no runtime counterpart, and (as later sections show) the reverse. Trusting either reading alone is unsafe.

## Testing both paths

Every feature is therefore exercised twice, by two adjacent functions over the same definition. The static half is type-only: its body lives under `if TYPE_CHECKING:`, so it never runs, but the checker still reads it, and `assert_type` states the expected type. The runtime half evaluates the same definition with `typemap`'s `eval_typing` and inspects the result directly. (`t.NewTypedDict` / `t.Member` are PEP 827 combinators that build a `TypedDict` at the type level; `eval_typing` is `typemap`'s runtime evaluator of the same expression.)

```python
type Row = t.NewTypedDict[t.Member[Literal["a"], int], t.Member[Literal["b"], str]]


def mypy_test_row() -> None:
    if typing.TYPE_CHECKING:
        row: Row = {"a": 1, "b": "x"}
        assert_type(row["a"], int)


def test_row() -> None:
    td = eval_typing(Row)
    assert td.__annotations__ == {"a": int, "b": str}
```

`mypy_test_row` is checked but never collected by pytest (the `mypy_` prefix); `test_row` runs the same `Row` through the runtime evaluator. One definition, both meanings, side by side.

Because the fixtures are ordinary Python, the editor, CI, and the runtime evaluator all see the same code, with the project's real imports and library context in scope — and no separate mypy subprocess is spawned to type-check a snippet. The trade-off is apparent rather than real: the tests do not drive mypy themselves, so it can look like less control over the checker; in practice it is enough, and it keeps the unit under test identical to ordinary library code.

## Honest negative tests

Positive assertions are easy; the hard half is proving that a malformed input is *rejected*, because a missing diagnostic is silent. Two mypy flags turn a suppression comment into a checked assertion:

```python
def mypy_test_row_rejects_bad() -> None:
    if typing.TYPE_CHECKING:
        row: Row = {"a": "oops", "b": "x"}  # type: ignore[typeddict-item]
```

Under `--enable-error-code ignore-without-code` every `# type: ignore` must name its code, and `--warn-unused-ignores` fails the run if the named error is no longer emitted. So `# type: ignore[typeddict-item]` asserts *"mypy must still flag this line"*: the day the negative case silently starts type-checking, the ignore becomes unused and CI turns red. `pytest.mark.xfail(strict=True)` gives the runtime track the same property for known static/runtime divergences — it flips to a failure the moment the gap closes.

## Contributions to PEP 827's tooling

> *(tentative — keep?)* Exercising the runtime track surfaced and fixed real bugs upstream: PR #117 (merged), PR #122 (open), and Issue #123, all on `vercel/python-typemap` — the kind of edge-case discovery PEP 827's standardisation needs.

# tysql: implementation and evaluation

## Schema as types

A table is an ordinary annotated class. `tysql` rewrites each plain annotation into a `Column` that records three facts — the owning table, the column name, and the stored type — so the declaration the user writes and the declaration the checker sees differ (Fig. 4):

\begin{figure}[H]
\centering
\begin{minipage}[t]{0.30\linewidth}
\centering
\textbf{\small You write}\\[4pt]
\begin{Verbatim}[fontsize=\footnotesize, frame=single, framesep=4pt]
class User(Table):
    id:     PrimaryKey[int]
    email:  str
    age:    int | None
\end{Verbatim}
\end{minipage}\hfill
\begin{minipage}[t]{0.66\linewidth}
\centering
\textbf{\small The checker sees}\\[4pt]
\begin{Verbatim}[fontsize=\footnotesize, frame=single, framesep=4pt]
class User(Table):
    id:    Column[User, Literal["id"],    PrimaryKey[int]]
    email: Column[User, Literal["email"], str]
    age:   Column[User, Literal["age"],   int | None]
\end{Verbatim}
\end{minipage}
\caption{\texttt{tysql} rewrites each plain annotation into a \texttt{Column[Owner, Name, Type]}, so every column keeps its table, its name, and its stored type.}
\end{figure}

After the rewrite, `User.age` is no longer just `int | None` with its origin lost; it is `Column[User, Literal["age"], int | None]`. The column carries its table, its name, and its type wherever it goes, and every later operation — projection, `INSERT`, `JOIN` — reads those three facts straight off it.

## The `run` spine: statements as values, type-level dispatch

> One non-overloaded `run[S](stmt: type[S], data: InOf[S]) -> OutOf[S]`. `InOf[S]` / `OutOf[S]` dispatch on the statement kind with chained `IsAssignable` + a `RaiseError` fallback — the organizing mechanism every statement family plugs into.

## Writing: the INSERT family

> The enforced write path on the `run` spine: the `Insert[T]` statement and its computed input row, with `RETURNING` selecting the output type via `OutOf[S]`. *(The earlier `InsertInput[T]` and synthesized-signature spellings are superseded.)*

## Reading: SELECT projection and JOIN

> A `SELECT` projects columns into a named record `{"id": int, "email": str}`, not a positional tuple; a single `INNER JOIN` merges both tables' projected columns. *(The earlier value-builder `select(User.id, …)` spelling is superseded by the type-level statement form.)*

## Evaluation: the typed subset and its walls

> The well-typed subset **S** (CREATE TABLE, INSERT, projection, equality-`WHERE`, single JOIN); the precision ladder (exact → degraded → inexpressible); the walls where PEP 827 runs out (value-level arithmetic and comparison over the schema). Evaluated against PostgreSQL as the oracle.

# Analysis and discussion

> The community debate on whether these facilities belong in Python is ongoing — see the [PEP 827 discussion](https://discuss.python.org/t/106353). To write: the genuine trade-off (expressiveness vs. a second language in the annotations), what acceptance concretely requires (typing\_extensions + ≥1 checker + conformance tests; Pyright and ty reject plugins, so only a spec-able kernel can become first-class), how other languages type SQL, and tysql's roadmap.

# Literature review

Placed here so it does not interrupt the argument, this chapter situates the work against Python's typing philosophy, the shape of the expressiveness gap, and prior attempts to close it.

Python's type hints are optional and tool-oriented: PEP 484 frames them as a notation for offline static analysis, not a mechanism that changes runtime semantics [1]. Because the same annotations are consumed by several independent checkers, *portability* is a first-order constraint — a guarantee that depends on one checker's internals is not a guarantee in Python's ecosystem [1]. PEP 544 adds structural subtyping through `Protocol`, but only constrains existing objects; it cannot construct new types whose shape depends on runtime values [2]. PEP 681's `dataclass_transform` goes further by standardising a *declarative marker*: it performs no transformation itself, it only tells checkers to treat a class as dataclass-like [3]. The recurring choice is visible here — the ecosystem standardises a fixed signal, never type-level computation.

Most hard Python typing problems share one cause: the type depends on runtime values, and the shared language has no portable way to express that dependency. A typed projection makes this concrete. TypeScript builds the result type from the inputs with the `Pick` operator and `const` assertions, so selecting a subset of columns yields a precisely typed record [4][5]. Python performs the same projection at runtime trivially, but cannot *name* the resulting type as a function of the selected keys [1]. The same limit appears with intersection and negation, which are not standardised as user-denotable operators even though narrowing arguments are naturally set-theoretic [6]; different checkers approximate them with incompatible internal rules, fragmenting the effective type system [7].

Where the standard surface falls short, libraries reach for checker plugins. Mypy's plugin system exists precisely to teach the checker about patterns the annotation language cannot express [8]. SQLAlchemy shows both the value and the cost: its mypy plugin added precision for declarative mappings, but became a maintenance liability and was deprecated in 2.0 in favour of native annotations [9][10]. PEP 681 is the middle ground between a bespoke plugin and doing nothing — a shared, declarative contract that multiple tools implement uniformly [3].

Finally, expressiveness is not the obstacle. Roth shows Python's type system is Turing-complete: arbitrary computation can be encoded into subtyping [11]. The limitation is not power but the absence of a designed, readable, portable surface for value-dependent type relationships — the gap PEP 827 targets and this thesis evaluates.

# Conclusion

> Restate the question, summarise what tysql well-types and where PEP 827 stops, the contribution (a working type-level SQL builder + dual-track evidence), limitations, future work.

# References {.unnumbered}

1. PEP 484 — Type Hints. <https://peps.python.org/pep-0484/>
2. PEP 544 — Protocols: Structural Subtyping. <https://peps.python.org/pep-0544/>
3. PEP 681 — Data Class Transforms. <https://peps.python.org/pep-0681/>
4. TypeScript Handbook — Utility Types (`Pick`). <https://www.typescriptlang.org/docs/handbook/utility-types.html>
5. TypeScript Handbook — Everyday Types (`const` assertions). <https://www.typescriptlang.org/docs/handbook/2/everyday-types.html>
6. J. Zijlstra. Gradual negation types and the Python type system. <https://jellezijlstra.github.io/negation-types.html>
7. Astral. ty type checker documentation. <https://docs.astral.sh/ty/>
8. Mypy. Extending mypy with plugins. <https://mypy-lang.blogspot.com/2019/03/extending-mypy-with-plugins.html>
9. SQLAlchemy. Mypy / PEP 484 support for ORM mappings. <https://docs.sqlalchemy.org/en/latest/orm/extensions/mypy.html>
10. SQLAlchemy 2.0 changelog. <https://www.sqlalchemy.org/changelog/CHANGES_2_0_40>
11. O. Roth. Python type hints are Turing complete. <https://arxiv.org/abs/2208.14755>
