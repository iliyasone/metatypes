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

Python's static type system cannot express types produced by metaprogramming, yet dynamically manipulating classes has been a native feature of the language since day one. The clearest casualty is the database query: a `SELECT` that projects a subset of columns loses their names from its type, and a relationship traversal is typed as a fully materialised object graph the query never fetched. PEP 827 (*Type Manipulation*, Draft, targeting Python 3.16) proposes a small set of type-level combinators to close this gap, but whether they are sufficient in practice was unknown. This thesis answers that question empirically by building **tysql**, a PostgreSQL query builder in which a statement is written as a *type* and its result type is computed from that type. Because PEP 827 is not yet in any released checker, every construct is exercised on two tracks at once: at runtime by the `typemap` evaluator and statically by a `mypy` fork, and the two are held in agreement by a paired-test methodology. The result type is then checked against a third, independent authority — a live PostgreSQL server, whose reported result columns are the ground truth. On a defined subset **S** (`CREATE TABLE`, `INSERT … RETURNING`, column projection with aliases, equality-`WHERE` with inferred parameters, and a single `INNER JOIN` with aggregation, grouping and ordering) tysql infers the exact result record for every query, matching PostgreSQL column-for-column. Outside **S** the work maps precisely where the facilities run out: aggregates such as `SUM`/`AVG` and outer-join nullability are *inexpressible*, duplicate projected names collapse the record, and value-level comparison is *unsound* (tysql accepts `WHERE email = 5`, which PostgreSQL rejects). The contribution is a working type-level SQL builder, a reproducible oracle evaluation, upstream fixes to PEP 827's reference tooling, and a concrete account of what standardising the proposal would require.

# Аннотация {.unnumbered}

Статическая система типов Python не умеет выражать типы, порождаемые метапрограммированием, хотя динамическое изменение классов было в языке с самого начала. Ярче всего это видно на запросах к базе данных: `SELECT` с проекцией части столбцов теряет их имена в типе, а обход связей типизируется как полностью загруженный граф объектов, который запрос на самом деле не извлекал. PEP 827 (*Type Manipulation*, статус Draft, цель — Python 3.16) предлагает набор комбинаторов уровня типов, закрывающих этот пробел, но их достаточность на практике не была проверена. В работе этот вопрос исследуется эмпирически: построен **tysql** — конструктор запросов к PostgreSQL, где инструкция записывается как *тип*, а тип результата вычисляется из неё. Так как PEP 827 ещё не поддержан ни одним выпущенным проверяющим, каждая конструкция проверяется одновременно двумя путями — во время выполнения интерпретатором `typemap` и статически форком `mypy`, — а их согласованность обеспечивается методикой парных тестов. Полученный тип затем сверяется с третьим независимым источником истины — работающим сервером PostgreSQL, чьи столбцы результата берутся за эталон. На заданном подмножестве **S** (`CREATE TABLE`, `INSERT … RETURNING`, проекция столбцов с псевдонимами, `WHERE` на равенство с выводом параметров и один `INNER JOIN` с агрегацией, группировкой и сортировкой) tysql выводит точный тип строки для каждого запроса, совпадающий с PostgreSQL столбец в столбец. За пределами **S** работа точно указывает, где средств не хватает: агрегаты `SUM`/`AVG` и опциональность при внешнем соединении *невыразимы*, дублирующиеся имена столбцов схлопывают запись, а сравнение значений *несостоятельно* (tysql принимает `WHERE email = 5`, который PostgreSQL отвергает). Вклад работы — действующий конструктор SQL уровня типов, воспроизводимая оценка с оракулом, исправления в эталонном инструментарии PEP 827 и конкретное описание того, что потребуется для принятия предложения.

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

A decade of work has made Python's annotations remarkably capable. Yet one class of types still escapes them: the result of a database query. SQLAlchemy is at once the clearest showcase of annotation-driven runtime behaviour and the clearest demonstration of where it stops.

A relational database stores rows of named, typed columns across related tables. The motivating schema has three (Fig. 2): every post and comment belongs to a user, and every comment belongs to a post. (The implementation chapter later works over a focused two-table slice of this schema — users and posts.)

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

<TODO>
I would really love if there would be figure relation which would some how emphosize the complication of this query and relation. Maybe take the original figure and show in color with something?
Actually no, it is not worth it, forget about it.
</TODO>

Both failures share one root: the result type is declared up front, never computed from the query that produces it. Computing it from the query instead — so a `SELECT` yields a precise record such as `{"id": int, "email": str}`, naming exactly the columns it returns, and an ill-typed query becomes a type error — is what PEP 827's type manipulation makes possible [12], and what the rest of this thesis builds and measures.

## Research question and contributions

The proposal is new, and its central promise — that a *fixed* set of type-level operators can express the value-dependent types real libraries need — has not been tested against a demanding domain. This thesis takes SQL as that domain and asks, concretely:

- **RQ.** To what extent can PEP 827's type-manipulation facilities *well-type* a subset of PostgreSQL? A query is *well-typed* when the checker infers its exact result type — a record whose keys and value types match the columns PostgreSQL actually returns — and rejects the statement exactly when PostgreSQL would. Two sub-questions follow: which queries have a result type the facilities *cannot* infer, and which ill-typed queries *cannot* be statically rejected?

The answer is delivered as an artefact and an evaluation. The artefact is **tysql**, a query builder in which each statement is a type and its parameters and result rows are computed from that type by PEP 827 combinators. The evaluation defines a subset **S**, runs each query class against a real PostgreSQL server, and reports — reproducibly — where the inferred type is *exact*, where it is only *approximate*, and where the facilities are *not enough*. The specific contributions are:

1. a type-level PostgreSQL builder that infers the result record of every statement in **S** and rejects out-of-schema references at check time (§*tysql: implementation and evaluation*);
2. a **dual-track methodology** that keeps a runtime evaluator and a static checker in lock-step, with negative assertions that fail loudly when a check stops firing (§*Design and methodology*);
3. a **PostgreSQL-oracle evaluation** that confirms exact inference across **S** and pins down the three walls beyond it — inexpressible aggregates and outer-join nullability, collapsing duplicate names, and unsound value comparison (§*tysql: implementation and evaluation*);
4. concrete feedback for standardisation, including fixes merged into PEP 827's reference tooling and an account of what acceptance requires (§*Analysis and discussion*).

The thesis is organised accordingly. *Design and methodology* introduces PEP 827's combinators, the two-evaluator (runtime/static) setup, the paired-test discipline that keeps them honest, and PostgreSQL-as-oracle. *Literature review* places the work against Python's typing philosophy and the two ways other languages type SQL. *tysql: implementation and evaluation* builds the query builder family by family and then measures it against the oracle. *Analysis and discussion* reads the results into the live debate over the proposal, and *Conclusion* summarises the answer and the road to standardisation.

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

The checker accepts `build` — `Hidden` is in scope statically — yet the class is never defined at runtime, so calling `Hidden()` raises `NameError`. A meta-type can therefore carry a precise static meaning with no runtime counterpart, and (as later sections show) the reverse. Trusting either reading alone is unsafe. This is the founding assumption of the methodology: because the two readings can diverge, every claim in this thesis is checked on *both* — never inferred from one.

## PEP 827 in one page

<TODO>
I would actually start with a basics there - now we have tools to create a new type `NewProtocol` and `NewTypedDict`
I think shemas would be very valuable like "this is type manipulation statement" and this is what it resolved to.
</TODO>

The gap the introduction ends on — a type that must be *computed* from a query — is exactly what PEP 827 [12] sets out to make expressible. It adds no new syntax; it adds a set of *type-level combinators*, ordinary generic aliases that a type checker knows how to evaluate. The ones this thesis leans on are few:

- `Attrs[T]` and `Iter[…]` enumerate the members of a class at the type level, so an alias can loop over a schema's columns;
- `Member[name, type]` builds one field, and `NewTypedDict[*Members]` assembles those fields into a fresh `TypedDict` — this is how a result record is *constructed* rather than declared;
- `GetArg`, `GetArgs`, `GetMemberType`, `Length`, `Slice` read structure back out of a type (an argument by index, a member's type, the length of an argument list);
- `IsAssignable` and `IsEquivalent` are the type-level predicates, each evaluating to `Literal[True]` / `Literal[False]`, usable in a `type` alias's conditional expression;
- `UpdateClass[*Members]`, used as the return annotation of `__init_subclass__`, tells the checker to *rewrite* a class's members — the mechanism that turns a plain column annotation into a rich `Column`;
- `RaiseError[Literal["msg"]]` produces a type that, when evaluated, surfaces a diagnostic — the proposal's designated way to signal an ill-formed type (its role, and why the bottom type `Never` cannot play it, is examined in *Analysis and discussion*).

A small example shows the shape of the whole idea. The alias below loops over a class's attributes and rebuilds them as a `TypedDict`, keeping every name but wrapping each value type:

```python
type Wrap[T] = t.NewTypedDict[
    *[t.Member[x.name, Boxed[x.type]] for x in t.Iter[t.Attrs[T]]]
]
```

Nothing here is a value being computed at runtime in the ordinary sense; it is a *type* being computed, by rules the checker follows. PEP 827 is a Draft targeting Python 3.16 [12], so no released checker evaluates these rules yet — which is the practical problem the next section addresses.

## Two evaluators for one language


~Because no shipping tool implements PEP 827~, <TODO>too bold claim. The authors make an evaluator and a mypy static checker. So we actually have tools provided from the PEP authors</TODO>  this thesis runs the same combinator language through two independent evaluators and requires them to agree.

- **The runtime track — `typemap`.** Annotations are first-class objects, so the combinators can be interpreted at run time. `typemap`'s `eval_typing(Wrap[User])` walks the alias and returns an actual `TypedDict` class, with real `__annotations__` and `__required_keys__` [13]. This is the track a program can use *today*, with no special checker, and the track the runtime tests introspect directly.

<TODO>I remember typemap have something like nice_print_types we can show another interactive sheel there with a Wrap[User] result</TODO>
- **The static track — a `mypy` fork.** A fork of `mypy` evaluates the very same aliases during type-checking, so a call site like `run(Select[User], data=…)` is validated with no runtime call at all [14]. This is the experience PEP 827 promises once standardised, available now to anyone who installs the fork.

The two are not redundant. The static track is where the proposal's real value lies — errors before the program runs — but it is also where the fork's incompleteness bites, and several design decisions in tysql exist only because a construct that evaluates cleanly at runtime does *not* survive the fork (§*tysql: implementation and evaluation* returns to this repeatedly). The runtime track is complete enough to serve as a second opinion and as a fallback distribution channel. Holding a feature to *both* is what makes a green build meaningful (Fig. 4).

\begin{figure}[H]
\centering
\begin{tikzpicture}[
  font=\small, node distance=6mm,
  box/.style={rectangle, draw, thick, rounded corners, inner sep=5pt, fill=gray!4, align=center},
  db/.style={rectangle, draw, thick, inner sep=5pt, fill=blue!5, align=center},
  op/.style={-{Stealth[length=2mm]}, thick},
]
\node[box] (src) {one combinator program\\\texttt{ResultOf[Select[User, ...]]}};
\node[box, above right=5mm and 20mm of src] (rt) {runtime track\\\texttt{typemap.eval\_typing}};
\node[box, below right=5mm and 20mm of src] (st) {static track\\\texttt{mypy} fork};
\node[box, right=18mm of rt] (rtd) {\texttt{TypedDict}\\(introspected)};
\node[box, right=18mm of st] (std) {revealed type\\(\texttt{assert\_type})};
\node[box, right=14mm of $(rtd)!0.5!(std)$] (agree) {paired tests:\\\textbf{must agree}};
\node[db, below=9mm of agree] (pg) {PostgreSQL\\(oracle)};
\draw[op] (src.north) to[out=50,in=180] (rt.west);
\draw[op] (src.south) to[out=-50,in=180] (st.west);
\draw[op] (rt) -- (rtd);
\draw[op] (st) -- (std);
\draw[op] (rtd.east) to[out=0,in=90] (agree.north);
\draw[op] (std.east) to[out=0,in=-90] (agree.south);
\draw[op] (agree) -- node[right, font=\footnotesize]{ground truth} (pg);
\end{tikzpicture}
\caption{The dual-track methodology. One combinator program is evaluated two independent ways --- interpreted at runtime by \texttt{typemap} and type-checked by the \texttt{mypy} fork --- and paired tests require the two results to agree. For the query subset, a live PostgreSQL adds a third, external check on whether the agreed type is actually correct.}
\end{figure}

<TODO>
A lot of questions to this take. The reason we have 2 ways is deeply related with a Python dynamic nature - types are **runtime values**, and type annotations interpetered as a normal (lazy since Python 3.14) python statemenets. That is why we have 2 ways - because python type maniputors (and type annotations in general) should work in genuely 2 absolutely different context: 
- static, evaluated by a tool at lint time
- runtime, evaluted by Python Interpretator, at the runtime (when introspected)

There we can add a statement about lazy annotations - maybe even another subchapter?
idea: before python 3.14 (find exact pep pls) annotations were evaluated immediatly and something like this was not possible:

```
class Node[T]:
    value: T
    left: Node[T]
    right: Node[T]
```

But there was a trick - `from future import annotations` which, if ever invoked, changed the CPython behaviour and just making annottaions strings. We lose the runtime class reference for introspection, but also all erros related to circular imports, ... etc are just stopped being a runtime issue.

The problem is that this solution is just not Pythonic enough. Big part of annotations was that they contain actual class objects. Since Python 3.14 this issue was solved elegantly: the annotations remained python statemenets, but now they are evaluated only when you directly try to access them. so this is lazy statemnets.

</TODO>

## Testing both paths

<TODO>
I definetly had a few cases where mypy and typemap test results are drifted (mention in one sentence which one). most of the times it is just the bug either into the mypy-fork or in runtime evaluators. But because of the typing.TYPE_CHECKING the drift may actually be real: if some annottains purely static only, we can't investigate it. in general those 2 paths may not be same. For the sake of a mental helth of a python developer, I would argue that into the Post 3.14 world (with lazy annotations), and especcially post 3.16 world the use of a typing.TYPE_CHECKING should be a code smell. (Opinion)
</TODO>

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

## Four points of truth

<TODO>
This part is a real interested. We have those 3 levels - but they are not particually related to the tysql. I would not actually mention it there, or mention less. what I want to show is the simple example

```python
type X = int if typing.Bool[Literal[True]] else str
```
And this is where the got middle of the icebeirg is appearing - this statements should be valid python code.

The reader my ask: why the type manipulation statemenst look so ugly? That is precisy the reason.
we can't make a tuple type by `(int, 1 | 2)` - because this is just evaluate literally a tuple, and the 1 | 2 would be evaluated as a binary operator, not what intended to be `tuple[int | Literal[1] | Litera[2]]`. 

The good news is that the sytanx may be always impoved later (for example https://imogenbits-peps.readthedocs.io/en/ast_format/pep-9999/ - suggests stop evaluating the anntotains and store them AST) or (some another pep which is suggests some new syntax... I remember something like <> used to distignush type level statemeents and the normal level)

But at the end of the day any type annotation statement should be translated to python objects (because we should allow runtime introspection), so eventually the nice `(int, 1 | 2)` will still evaluate to the `tuple[int, Literal[1] | Literal[2]]`, so maybe it is even better that we using python type manipulatio statements from the day one?

---

Going back to the example, 

```python
type X = int if typing.Bool[Literal[True]] else str
```

Type statements are stayed lazy untill explicit introspection
But what if we do?

```python
>>> X.evaluate_value() 
<class 'str'>
```

Why? One level down to the icebeirg!

The PEP 827 idea was so the all types, which was suggested - staying "inert", meaning that there is no any atomatic reduction of the `GetMember[User, Literal["id"]]` to the `int`. 
Even when evaluated and introspected, they stayed as a type aliases. This is intentional design decision in PEP 827. Take a moment to realize that `inert` and `lazy` are not the same thing. Annotation is evaluated, but not reducted according to the rules.

Who is doing the reduction? There are only 2 possible situations where we need to get a reducted type:
- we are static type checker, and we are prepared for such case. we have resolving rules.
- we are runtime introspection library, and we need to adapt. if we was expecting just some type to do some runtime introspection magic (final type, like `Pubic[Hero]`), in post PEP 827 we should deduct the types manually, using the 3rd-party `typemap` library. I would actually argue it should be in standart library as a part of language specification. 

## Problem: if is evaluted

consider this statement:
```python
def test() -> int if typing.Bool[Literal[True]] else str:
    ...
```

one point into the icebearg bellow. 
if you type this value literally in the interpetator shell:

```python
>>> int if typing.Bool[Literal[True]] else str
<class 'str'>
```

because the boolean special forms always going to False into the runtime

the typemap runtime doing some magic to actually prevent it. (I am not sure but I am guessing it is investigating the AST before evaluating the type - because it is taking as input still lazy not evaluted python statement in closure)

if you first try to inspect annotations using normal tools, you will get an WRONG RESULT
```python
>>> test.__annotations__ # or typing.get_type_hints(test)
{'return': str}
```

But if you use the evaluator

```python
from typemap.type_eval import eval_typing

from typing import get_type_hints

def test() -> int if typing.Bool[Literal[True]] else str:
    ...
    
>>> eval_typing(test)
<function __main__.test() -> int>
```

you will get correct result. and this **is not a bug**, as this behaviour is exactly described into the PEP 827 (boolean special forms is always to False because the stdlib should not now how to deduct)

This is a tradeoff when you allow to use <... if ... else>
(I hope I did everyhing correctly here?..)

I think it not a really big deal, as the runtime introspection in post PEP 827 would just use the evaluator. but it is still maybe accidentally be cursed (because if the normal annotations would be called first, it would actually compute to the wrong branch and stayed forever - the typemap evalator is not doing this)

I would suggest making of a Boolean speical forms __bool__ raise an error into the context free statements (when no evaluator is called, not simply return False).

[Shit this is actually bigger then I though! lets format it nicely and then I will open an issue into the typemap repo, it is whole a lot topic. Also in last chapters, about plans, we could tell that this is what I am going to do next.] 

</TODO>

The paired tests answer *"do the two evaluators agree?"* They do not, by themselves, answer *"is the agreed-upon type correct?"* For that the query needs an authority outside the type system entirely. tysql therefore treats each statement as having four separate, checkable facts, and the methodology is to line them up:

| Observation | What it reports |
| --- | --- |
| `stmt.__value__` | what the combinators *encoded* — the statement type before any evaluation |
| `eval_typing(ResultOf[stmt])` | what the **runtime** track (`typemap`) computes the result to be |
| `reveal_type` / `assert_type` | what the **static** track (the `mypy` fork) computes the result to be |
| **PostgreSQL result metadata** | the **ground truth** — the columns the query actually returns |

The first three live inside the type system; the fourth does not. A relational database already knows the precise shape of any query's result: after preparing a statement, PostgreSQL reports each output column's name and type in the row description, which a driver such as `psycopg` exposes through `cursor.description` [23]. That description is independent of tysql, of `typemap`, and of the fork — it is what the engine itself will return. Taking it as the *oracle* turns the research question into something measurable: a query is well-typed exactly when the record from the middle two rows matches the columns from the last one. The evaluation chapter runs this comparison for every query class in the subset; the harness that does so is described there.

## Fixing the evaluator: an upstream contribution

Holding a feature to both tracks did more than catch divergences in tysql — it surfaced genuine defects in the reference tooling itself, which is exactly the edge-case exercise a Draft PEP needs before standardisation. Three issues on the `typemap` evaluator came out of this work: a fix now merged (PR #117), a fix still open (PR #122), and a reported defect (Issue #123).

PR #122 is representative. Evaluating a `TypedDict`-building alias over an *empty* member list — the honest result of a comprehension whose filter rejects every column — drove the evaluator down a branch that assumed at least one member and raised instead of returning the empty `TypedDict`. The alias was correct PEP 827; the interpreter was not. The fix makes the zero-member case return a well-formed empty `TypedDict`, matching how the static fork already treats it, so the two tracks agree again. The value of the contribution is less the patch than the *method*: differential testing between a runtime interpreter and a static checker for the same specification is how ambiguities in that specification become visible while it is still a draft.

## The check contract

For the two-track discipline to mean anything it must be *enforced*, not merely intended, so the whole of it runs in continuous integration and every claim in this thesis is reproducible from the same commands. Four checks gate the work:

- **`ruff`** lints the source, and — because the code examples in this document are real Python — a small script extracts every fenced Python block from the thesis and runs `ruff format --check` over it, so a snippet that does not parse and format cannot be committed. The examples the reader sees are the examples the formatter accepts.
- **The forked `mypy`**, run with `--warn-unused-ignores` and `--enable-error-code ignore-without-code`, is the static track. The two flags are what turn a suppression comment into a *checked negative assertion*: every `# type: ignore[code]` must name its code, and must still be *used* — the day a negative case silently starts type-checking, the ignore becomes unused and the run turns red. A missing diagnostic is therefore as loud as a wrong one.
- **`pytest`** is the runtime track, evaluating the same aliases through `typemap` and introspecting the resulting classes; `xfail(strict=True)` marks known static/runtime divergences so they, too, flip to failures the moment they are closed.
- **The oracle harness** renders and executes the subset against a real PostgreSQL and compares, as the evaluation chapter reports.

Nothing here relies on a human remembering to re-run a check or eyeballing a diagnostic. That is the point: a green build is a machine-verified statement that both evaluators agree, that every negative case still fails, and — for the subset — that the database agrees too.

# Literature review

This chapter situates the work against three bodies of knowledge: Python's own typing philosophy and why it stops short of value-dependent types; how other languages already type SQL, which divides cleanly into two strategies; and the specific proposal — PEP 827 — this thesis evaluates, together with the earlier features its implementation stands on.

## Python's typing philosophy: portable, optional, first-order

Python's type hints are optional and tool-oriented: PEP 484 frames them as a notation for offline static analysis, not a mechanism that changes runtime semantics [1]. Because the same annotations are consumed by several independent checkers, *portability* is a first-order constraint — a guarantee that depends on one checker's internals is not a guarantee in Python's ecosystem [1]. PEP 544 adds structural subtyping through `Protocol`, but only *constrains* existing objects; it cannot *construct* new types whose shape depends on runtime values [2]. PEP 681's `dataclass_transform` goes further by standardising a *declarative marker*: it performs no transformation itself, it only tells checkers to treat a class as dataclass-like [3]. The recurring choice is visible across all three — the ecosystem standardises a fixed signal, never type-level computation.

Most hard Python typing problems share one cause: the type depends on runtime values, and the shared annotation language has no portable way to express that dependency. A typed projection makes this concrete. TypeScript builds the result type from the inputs with the `Pick` operator and `const` assertions, so selecting a subset of columns yields a precisely typed record [4][5]. Python performs the same projection at runtime trivially, but cannot *name* the resulting type as a function of the selected keys [1]. The same limit appears with intersection and negation, which are not standardised as user-denotable operators even though narrowing arguments are naturally set-theoretic [6]; different checkers approximate them with incompatible internal rules, fragmenting the effective type system [7].

Crucially, expressiveness is not the obstacle. Roth shows Python's type system is already Turing-complete: arbitrary computation can be encoded into subtyping [11]. The limitation is not power but the absence of a *designed, readable, portable* surface for value-dependent type relationships — the gap PEP 827 targets and this thesis measures.

## Two ways to type SQL

SQL is the sharpest test of value-dependent typing: a query's result type is a function of the query text and the schema, and getting it wrong is a common source of runtime errors. Languages that type SQL fall into two families.

**Code generation — types produced by an external step.** Rust's `sqlx` verifies a SQL string *against a live database at compile time* and expands the query macro into an anonymous struct with typed fields:

```rust
// sqlx: the string is checked against the DB at compile time; the row struct
// (id: i32, email: String) is generated from the database's own metadata.
let rows = sqlx::query!("SELECT id, email FROM users WHERE age > $1", 18)
    .fetch_all(&pool).await?;
```

Prisma takes the same idea from a schema file rather than a live connection: `prisma generate` reads a `.prisma` schema and emits a fully typed TypeScript client, so a projection is typed by generated code [21].

```typescript
// Prisma: `prisma generate` produced the client's types from the schema.
const rows = await prisma.user.findMany({ select: { id: true, email: true } });
//    rows : { id: number; email: string }[]
```

Both are effective and both pay the same price: a build step, a generated artefact that can drift from source, and — for `sqlx` — a database reachable at compile time [22]. The types are correct but they are not written in, or computed by, the host language's own type system.

**Type-level embedding — the host language computes the *result type*.** The distinguishing axis is not whether a schema is ever generated but *who computes the type of a query's result*. Rust's Diesel encodes the schema in a `table!` macro (which its tooling can generate from the database) but then lets the trait system infer *result types* directly — a `select` of two columns yields a `(i32, String)` the compiler derives, not a struct emitted by a generator [19]:

```rust
// Diesel: the trait system derives the result type (i32, String) at compile time.
let rows: Vec<(i32, String)> =
    users.filter(age.gt(18)).select((id, email)).load(&mut conn)?;
```

Haskell's Squeal goes furthest: the schema *is* a type, and a query is a typed expression whose result row is computed by the type checker, so an out-of-schema column or a shape mismatch is a type error in ordinary Haskell [20]. This second family — a SQL DSL embedded in the host language, whose *result types* are computed by that language's type system rather than emitted by an external generator — is precisely what Python has lacked. PEP 827 is what would let Python join it, and tysql is this thesis's test of whether it can.

## The features tysql stands on

tysql is not built on PEP 827 alone; it composes several recently standardised typing features, each load-bearing:

- **PEP 695** — type parameter syntax — gives the `class Column[Owner, Name, T]` and `type Alias[T] = …` forms used throughout, and the concise `type` statement that carries the combinator programs [17].
- **PEP 646** — variadic generics (`TypeVarTuple`, `Unpack`) — lets a statement carry a variable-length list of modifiers, as in `Select[Src, *Mods]` and `Insert[T, *Mods]` [15].
- **PEP 692** — `Unpack` of a `TypedDict` for `**kwargs` — is the natural way to type an `INSERT`'s keyword arguments, and its interaction with PEP 827 is where one concrete wall appears: a *computed* `TypedDict` cannot be consumed as `**kwargs` (documented in the appendix) [16].
- **PEP 649/749** — deferred evaluation of annotations — means, from Python 3.14, that annotations are lazy expressions rather than eagerly evaluated objects; this is what makes runtime interpretation of a combinator program by `typemap` viable at all [18].

The through-line is that Python has spent a decade shipping *fixed, declarative* typing features. PEP 827 is the first to standardise type-level *computation* over them.

## PEP 827 and its reference tooling

PEP 827, *Type Manipulation* [12], is the proposal under evaluation. It is a **Draft** and targets **Python 3.16** — a status that matters here as a constraint, not a footnote: no released type checker implements it, so a proof of practicality cannot lean on production tooling and must instead demonstrate the facilities working end to end on prototype implementations. Two such implementations exist and are the substrate of this work: `typemap`, a runtime evaluator of the combinators [13], and a fork of `mypy` that evaluates them during type-checking [14]. This thesis uses the author's fork of `typemap` (the runtime track) and the `mypy` fork (the static track); the differential-testing methodology of the previous chapter is, in effect, a conformance check of these two prototypes against each other.

Where the standard surface has fallen short before, Python libraries reached for checker *plugins*. Mypy's plugin system exists precisely to teach the checker about patterns the annotation language cannot express [8]. SQLAlchemy shows both the value and the cost: its mypy plugin added precision for declarative mappings, then became a maintenance liability and was deprecated in 2.0 in favour of native annotations [9][10]. A plugin is also inherently non-portable — it is one checker's internal extension, exactly the guarantee PEP 484 warns against relying on [1]. PEP 827's ambition is to move this capability from per-library, per-checker plugins to a *shared, spec-able surface* every checker can implement — the same trajectory PEP 681 followed for the narrow case of dataclasses [3]. Whether the surface it proposes is expressive enough for a real domain is the open question this thesis takes up.

# tysql: implementation and evaluation

## Schema as types

A table is an ordinary annotated class. `tysql` rewrites each plain annotation into a `Column` that records three facts — the owning table, the column name, and the stored type — so the declaration the user writes and the declaration the checker sees differ (Fig. 5):

\begin{figure}[H]
\centering
\begin{minipage}[t]{0.30\linewidth}
\centering
\textbf{\small You write}\\[4pt]
\begin{Verbatim}[fontsize=\footnotesize, frame=single, framesep=4pt]
class User(Table):
    id:    PrimaryKey[int]
    age:   int
    email: str
\end{Verbatim}
\end{minipage}\hfill
\begin{minipage}[t]{0.66\linewidth}
\centering
\textbf{\small The checker sees}\\[4pt]
\begin{Verbatim}[fontsize=\footnotesize, frame=single, framesep=4pt]
class User(Table):
    id:    Column[User, Literal["id"],    PrimaryKey[int]]
    age:   Column[User, Literal["age"],   int]
    email: Column[User, Literal["email"], str]
\end{Verbatim}
\end{minipage}
\caption{\texttt{tysql} rewrites each plain annotation into a \texttt{Column[Owner, Name, Type]}, so every column keeps its table, its name, and its stored type.}
\end{figure}

The rewrite is done by `__init_subclass__`, whose PEP 827 return annotation is the whole trick. It declares that subclassing `Table` produces a class whose members are the `Column`-wrapped versions of the originals, and the checker believes it:

```python
class Table:
    def __init_subclass__[T](
        cls: type[T],
    ) -> t.UpdateClass[
        *[t.Member[x.name, Column[T, x.name, x.type]] for x in t.Iter[t.Attrs[T]]]
    ]:
        # runtime half: materialise each annotation as a real Column descriptor,
        # so User.id also exists at runtime carrying the same triple.
        for name, annotation in get_type_hints(cls).items():
            setattr(cls, name, Column(cls, name, annotation))
```

<TODO>
I would not actually be so proud about merging the runtime and type paths in one class. But it felt nicely here, epseccially because without it `User.age` would be accesible in runtime, only into the static time. So the runtime half is a good to make the actual type manipualtion statements correct in a way what they are descrining. But in general they may not be defined in the same place and I don't have an answer wheneve this is a code smell or no.
</TODO>

The body is the *runtime* half and the return annotation is the *static* half, and they are deliberately the same rewrite expressed twice — the pattern the whole project rests on. After it runs, `User.age` is no longer just `int` with its origin lost; it is `Column[User, Literal["age"], int]`, carrying its table, its name and its type wherever it goes, and every later operation — projection, `INSERT`, `JOIN` — reads those three facts straight off it. A nullable column declared `T | None` is wrapped the same way, its `T | None` preserved verbatim in the third slot; this running two-table schema (used unchanged through the evaluation) keeps the columns non-null for brevity.

## Keys, and a lesson in where a combinator may sit

Two column kinds carry extra meaning. `PrimaryKey[T]` marks the table's key: it is *optional* on insert (the database assigns it) and *unwrapped* on read (a `PrimaryKey[int]` column comes back as plain `int`), and in DDL it renders as `SERIAL PRIMARY KEY` for an integer key. `ForeignKey[Owner, Name]` records a reference to another table's column, and renders as a `REFERENCES` constraint; it is also what a join reads to know two tables are related.

<TODO>
Lets just rename `PrimaryKey` to `SerialPrimatyKey`. It is just seems wrong that PrimaryKey is not actually resolved to a PrimaryKey into the postgresql. and mark the normal PrimaryKey as not implemented

</TODO>

The foreign key's *spelling* is a small but instructive design scar. The natural way to write it would nest a column reference — `ForeignKey[Col[User, Literal["id"]]]` — but `Col` is a conditional alias with a `RaiseError` branch, and in **annotation position** the static fork eagerly evaluates that branch even when it is not taken, so a perfectly valid foreign key would trip its own "no such column" guard. Splitting the reference into two plain type arguments, `ForeignKey[User, Literal["id"]]`, keeps a conditional combinator out of annotation position entirely, and the error disappears. It is the same lesson the flat `Col` conditional and the name-slot scope check teach from other angles: on the static track, *where* a combinator sits — annotation versus value position, name slot versus value slot, taken versus untaken branch — changes whether it fires, and the library's shape is dictated as much by these evaluation-order facts as by the SQL it models.

## Two readings, and why neither can be trusted alone

<TODO>
I think it should be positioned as "look" i find bug in mypy fork, that is. Interesting still!
This is proofs that the testing setup may found subtle bugs.
</TODO>

The rewrite exposes the split the methodology chapter warned about, in its sharpest form. Consider a class transformed by a marker like `Table`, and a type-level predicate asking whether one of its members is a `Column`:

```python
class Point(WrapFields):
    x: int  # becomes CustomField[int] after the transform
    y: CustomField[int]


type IsCustomField[C, N] = (
    Bool[Literal[True]]
    if t.IsAssignable[t.GetMemberType[C, N], CustomField[Any]]
    else t.RaiseError[Literal["Field is not a CustomField!"]]
)
```

Ask `IsCustomField[Point, "x"]` and the two tracks disagree in an instructive way. Statically, `reveal_type(Point.x)` is `CustomField[int]` — the transform has been applied — yet *inside* the predicate the fork still evaluates against the *pre-transform* schema, where `x` was a bare `int`, and so it emits the error branch's message even though the final result type still evaluates to `Literal[True]`. The lesson recorded in the test suite is blunt: a meta-type can carry one meaning to a `reveal_type` and a different one to a combinator that inspects it, and only the runtime evaluator, walking the fully-built class, settles which is real. This is precisely why every construct below is pinned to both tracks *and*, ultimately, to PostgreSQL.

## Statements as types: the `run` spine

Every SQL statement is written as a *type*, never as a chain of method calls: `Select[User]`, `Insert[User]`, `Select[User, Cols[…], Where[…]]`. A single function consumes them all:

```python
def run[S: Statement](stmt: type[S], data: ParamsOf[S]) -> ResultOf[S]:
    """The typed contract of a statement: `data` in, rows out."""
    raise NotImplementedError
```

`run`'s signature *is* the product. `ParamsOf[S]` is the `TypedDict` of parameters the statement takes; `ResultOf[S]` is the list of rows it yields. Both are computed from `S` by PEP 827 combinators, and both are what a checker enforces at every call site — there is no database bridge, so the body only ever raises. Dispatch on the statement kind is a single conditional ladder that pairs the two facts on one branch so they can never drift apart:

```python
type SpecOf[S: Statement] = (
    Spec[Row[t.GetArg[S, Insert, Literal[0]]], int]
    if t.IsAssignable[S, Insert[Any, *tuple[Any, ...]]]
    else Spec[_SelectParams[S], _SelectResult[S]]
    if t.IsAssignable[S, Select[Any, *tuple[Any, ...]]]
    else Spec[None, None]
    if t.IsAssignable[S, CreateTable[Any]]
    else t.RaiseError[Literal["run: unsupported statement"]]
)

type ParamsOf[S: Statement] = t.GetArg[SpecOf[S], Spec, Literal[0]]
type ResultOf[S: Statement] = t.GetArg[SpecOf[S], Spec, Literal[1]]
```

An `Insert[User]` takes the non-primary-key columns as its `data` and yields the generated key; a `CreateTable` takes and returns nothing; anything the ladder does not recognise falls through to a `RaiseError`. The families plug into this spine one by one below.

## Referring to a column, and an unavoidable wart

<TODO>
I think we should mention also GetMemberType before, when we are talked about ugliness about python types. Is this block a kinda a repeat?
<TODO>

There is a syntactic price for keeping statements at the type level. A programmer would like to write `User.id`, but `User.id` is a *value* (the `Column` descriptor), not a type, and a statement type needs a *type-level* reference to the column. So a column is named with a combinator instead:

```python
type Col[C, N] = (
    t.RaiseError[Literal["Col: no such column"]]
    if t.IsEquivalent[t.GetMemberType[C, N], Never]
    else t.GetMemberType[C, N]
)
```

`Col[User, Literal["id"]]` resolves to the column `User` declares under `"id"`, or to a `RaiseError` if there is none — so a typo is a type error at the reference site, the smallest possible unit of checking. The `if/else` is a deliberately *flat* two-way conditional: a chained `A if … else B if … else C` makes the static fork eagerly evaluate the deepest branch even when it is not taken, so a `RaiseError` in a trailing `else` fires for *valid* columns. Keeping the error in the taken-only branch is the difference between a check that works and one that rejects correct code — a recurring constraint the fork imposes on how these programs may be written. The verbosity of `Col[User, Literal["id"]]` over `User.id` is the honest cost of the approach; §*Analysis and discussion* returns to whether it is acceptable.

## Writing: `INSERT`, `RETURNING`, and the input row

The write path is the mirror of the read path. An `INSERT` does not project columns; it *consumes* them, and the parameters it consumes are computed from the schema by the same combinator idiom. The `Row` alias walks the table's columns and keeps every one *except* the primary key — the database fills that in — so the required `data` for an insert is exactly the insertable columns:

```python
type Row[T] = t.NewTypedDict[
    *[
        t.Member[x.name, t.GetArg[x.type, Column, Literal[2]]]
        for x in t.Iter[t.Attrs[T]]
        if not t.IsAssignable[x.type, Column[Any, Any, PrimaryKey[Any]]]
    ]
]
```

The filter is the mirror image of `ResultRow`'s omission: a `SELECT` *returns* the primary key (unwrapped), whereas an `INSERT` must *not* be given it. On the `run` spine, `Insert[User]` therefore takes `data: {"age": int, "email": str}` and — because the ladder pairs it with `int` as its result — yields the generated key. Supplying a missing, extra, mis-typed, or primary-key column is a `TypedDict` violation, checked at the call site:

```python
def mypy_test_gate_insert_rejects_primary_key() -> None:
    if TYPE_CHECKING:
        # the database fills the primary key; supplying it is an error.
        run(Insert[User], data={"id": 1, "age": 3, "email": "x"})  # type: ignore[typeddict-item]
```

## Rendering to PostgreSQL text

Inference says what a statement *returns*; a companion `render` says what it *is*. It walks the statement type at runtime with `typing.get_origin`/`get_args` and emits SQL a person would recognise — quoted identifiers, `psycopg`'s named placeholders (`%(name)s`), a `RETURNING` clause on inserts, and `SERIAL`/`REFERENCES` in DDL — without ever touching a database. The two halves stay consistent because they read the same statement type: `render` maps `PrimaryKey[int]` to `SERIAL PRIMARY KEY` exactly where `ResultRow` unwraps it to `int`, and emits one `%(name)s` placeholder per column exactly where `Row` makes that column a required key. So the aggregate example from the design renders to precisely the SQL one would write by hand:

```sql
SELECT "user"."id", count("post"."id") AS "n_posts"
FROM "user" INNER JOIN "post" ON "user"."id" = "post"."author"
GROUP BY "user"."id" ORDER BY "user"."id" ASC;
```

`render` is what makes the oracle evaluation possible at all: it is the bridge from a statement *type* to a string PostgreSQL can execute, and thus to the ground truth against which the inferred type is judged in the next sections.

## Reading: projection, unwrapping, aliases and aggregates

A `SELECT` computes a record from what it projects. Two helpers do the type-level work. `Unwrap` turns a stored `PrimaryKey[int]` back into the `int` the database returns; `ResultRow` walks a table's columns and rebuilds them as a `TypedDict`:

```python
type Unwrap[T] = (
    t.GetArg[T, PrimaryKey, Literal[0]] if t.IsAssignable[T, PrimaryKey[Any]] else T
)

type ResultRow[T] = t.NewTypedDict[
    *[
        t.Member[x.name, Unwrap[t.GetArg[x.type, Column, Literal[2]]]]
        for x in t.Iter[t.Attrs[T]]
    ]
]
```

So `Select[User]` — a bare source, meaning `SELECT *` — yields `list[{"id": int, "age": int, "email": str}]`, with the primary key already unwrapped. A projection `Cols[…]` narrows this to exactly the items listed, in order; an `As[col, Literal["alias"]]` renames the output key; and a `Count[col]` aggregate is typed `int`. Each of these is a one-item helper applied to the projection's loop variable, because — another fork constraint — a *single* comprehension over a helper alias evaluates on both tracks, whereas a *nested* comprehension does not. The payoff is that the record names exactly the columns the query returns, and reading a column that was not projected is a type error:

```python
def mypy_test_select_projection() -> None:
    if TYPE_CHECKING:
        rows = run(
            Select[User, Cols[Col[User, Literal["id"]], Col[User, Literal["email"]]]],
            data=None,
        )
        assert_type(rows[0]["id"], int)
        assert_type(rows[0]["email"], str)
        rows[0]["age"]  # type: ignore[misc]  # not projected -> not a key
```

The paired runtime test evaluates the same `ResultOf[…]` through `typemap` and asserts the `TypedDict`'s `__annotations__` are `{"id": int, "email": str}` — the two tracks, one definition.

## Joins come for free

The hardest-looking feature turned out to need no new type-level machinery at all. An `INNER JOIN` is written as the source of a `Select`, carrying its predicate as an `On` modifier:

```python
type UserPosts = InnerJoin[
    User, Post, On[Eq[Col[User, Literal["id"]], Col[Post, Literal["author"]]]]
]
```

Because `ResultRow`/`ProjectedRow` resolve each projected `Col` against *its own* owner table — the first argument of `Column[Owner, Name, T]` — pointing a projection at a join Just Works: `Col[User, "email"]` and `Col[Post, "text"]` each know their own table, so both land in one merged record `{"email": str, "text": str}`. The expected-hard part was easy precisely because the column already carries its origin; the surprise, next, was that the easy-looking part was hard.

## `WHERE`: the wall the fork puts up

Inferring a statement's *parameters* from its `WHERE` clause is where PEP 827's reference tooling ran out first. The goal is that each bound parameter in the clause becomes a required key of `data`:

```python
type FlatParams[W] = t.NewTypedDict[
    *[
        t.Member[
            t.GetArg[t.GetArg[pred, Eq, Literal[1]], Param, Literal[0]],
            t.GetArg[t.GetArg[pred, Eq, Literal[1]], Param, Literal[1]],
        ]
        for pred in t.Iter[t.GetArgs[W, Where]]
    ]
]
```

This reads each `Eq[column, Param[name, type]]` predicate and collects the `Param`s into a `TypedDict`, so `Where[Eq[Col[User, "age"], Param["min_age", int]]]` makes `data` require `{"min_age": int}`. It is deliberately *flat* — a single conjunction (`AND`) of equalities — and that is not a stylistic choice. The wishlist form was a nested `Where[Or[Eq[…], Eq[…]]]`, whose parameter collection needs to walk a predicate tree; walking a tree needs either a recursive type alias or a nested comprehension, and the `mypy` fork supports *neither* (a recursive alias collapses to `Never`; a nested `for` is rejected). Both work at runtime, so `Or`-trees can be typed by `typemap` today — but not by the static track, and a feature that is only half-checked was judged worse than a smaller feature checked on both. A second consequence of the same limits: with no way to *scan* the modifier list for the `WHERE`, the clause is read at a fixed position, guarded by `Length` checks so the out-of-range lookup is never evaluated when there is no such modifier. These are the fingerprints of an incomplete evaluator, and mapping them precisely is part of this thesis's answer.

## Mapping a column to its table: a check that had to be forced

A subtler question is whether a projected column even *belongs* to the query. `Select[User, Cols[Col[Post, "text"]]]` — projecting `Post.text` from a query over `User` alone — is nonsense PostgreSQL rejects, and it should be a type error. The check is conceptually simple ("is this column's owner one of the tables in the `FROM`?"), but making it *fire on the static track* exposed the deepest fork quirk of the project. A `RaiseError` placed in the *value* slot of a `Member` stays lazy on the fork and never fires; the same `RaiseError` placed in the *name* slot does fire, because `NewTypedDict` must force every key to build the dict. So the scope check rides the name slot:

```python
type ProjectedRow[Src, P] = t.NewTypedDict[
    *[
        t.Member[
            t.RaiseError[Literal["Col: table is not in the FROM clause"]]
            if not column_in_scope(Src, c)  # membership test, written inline
            else ItemName[c],  # normal path: the output key
            ItemType[ItemExpr[c]],
        ]
        for c in t.Iter[t.GetArgs[P, Cols]]
    ]
]
```

With it, `Col[Post, "text"]` over a `User` query fails with *"Col: table is not in the FROM clause"* on both tracks — for single tables and for joins (the owner must be one of the join's two sides). Two honest caveats, both recorded in the tests: the static error is reported at *file* level with no line number and is not suppressible by a line `# type: ignore`, a fork limitation; and it only fires once the result is *bound* (`rows = run(…)`), not when the call's result is discarded. This is the "map the column to the table" idea, and it is where the most checking is bought for the least type-level code.

## A worked example

Put together, the families read the way the SQL reads, and every intermediate type is checkable. Two tables — the users-and-posts core of the schema in Fig. 2 — declared as classes:

```python
class User(Table):
    id: PrimaryKey[int]
    age: int
    email: str


class Post(Table):
    id: PrimaryKey[int]
    author: ForeignKey[User, Literal["id"]]
    text: str
```

A row is inserted and its generated key read back — `data` is exactly the non-key columns, and because the statement carries no `RETURNING` beyond the key, `run` yields the key's row:

```python
run(Insert[User], data={"age": 22, "email": "a@b.c"})
```

Then the flagship query: *how many posts has each user written?* It is one type — a join, a projection with an aggregate, a grouping and an ordering — and its result record is inferred, not annotated:

```python
rows = run(
    Select[
        InnerJoin[
            User, Post, On[Eq[Col[User, Literal["id"]], Col[Post, Literal["author"]]]]
        ],
        Cols[
            Col[User, Literal["id"]],
            As[Count[Col[Post, Literal["id"]]], Literal["n_posts"]],
        ],
        GroupBy[Col[User, Literal["id"]]],
        OrderBy[Col[User, Literal["id"]], Literal["asc"]],
    ],
    data=None,
)
assert_type(rows[0]["id"], int)
assert_type(rows[0]["n_posts"], int)
rows[0]["email"]  # type: ignore[misc]  # not projected -> not a key
```

The checker knows `rows[0]` has exactly the keys `id` and `n_posts`, both `int`; asking for `email` is a type error because it was not projected. Nothing above is annotated by hand — the record is a function of the statement — and, as the next sections show, it is the same record PostgreSQL reports for the rendered query. This is the capability the introduction said Python lacked: a query's result type, computed from the query, and checked.

## The subset S

Collecting the families gives the subset **S** this thesis claims to well-type, and its explicit boundary:

- **`CREATE TABLE`** — rendered from the class, including `SERIAL PRIMARY KEY` and `REFERENCES` for foreign keys (no result type; DDL).
- **`INSERT`** — parameters inferred as the non-primary-key columns (the database fills the key), `RETURNING` the generated key.
- **`SELECT *`** — the full row, primary key unwrapped.
- **`SELECT` projection** — `Cols[…]` of columns, `As[…]` aliases, and the `Count` aggregate (typed `int`).
- **`WHERE`** — a conjunction of equalities, with each `Param` collected into the inferred parameter mapping.
- **`INNER JOIN`** — with an explicit `On` predicate, columns from both sides merged into one record.
- **`GROUP BY` / `ORDER BY`** — rendered; they do not change the result type.

Deliberately outside **S**: `OR`/nested predicates (the fork wall above), outer joins, aggregates other than `Count`, subqueries, and any dynamic (string-built) SQL. The next section measures how well **S** holds up, and characterises the first thing beyond each edge.

## Evaluation against PostgreSQL as the oracle

The claim "tysql infers the right type" is only meaningful against an authority that is not tysql. The methodology chapter named that authority: a real PostgreSQL server, whose `cursor.description` reports the true name and type of every result column. The evaluation harness (`scripts/pg_oracle_eval.py`) makes the comparison mechanical (Fig. 6): for each statement it (a) renders the SQL and executes it against PostgreSQL 17, reading back the reported columns; (b) evaluates `ResultOf[stmt]` through `typemap` to get the inferred `TypedDict`; and (c) checks that the two agree name-for-name, in order, with compatible types.

\begin{figure}[H]
\centering
\begin{tikzpicture}[
  font=\small, node distance=7mm,
  box/.style={rectangle, draw, thick, rounded corners, inner sep=5pt, fill=gray!4, align=center},
  op/.style={-{Stealth[length=2mm]}, thick},
]
\node[box] (stmt) {statement\\\texttt{Select[User, Cols[...]]}};
\node[box, above right=6mm and 20mm of stmt] (render) {\texttt{render} $\rightarrow$ SQL text};
\node[box, right=22mm of render] (pg) {PostgreSQL 17\\\texttt{cursor.description}};
\node[box, below right=6mm and 20mm of stmt] (eval) {\texttt{ResultOf} $\rightarrow$ \texttt{eval\_typing}};
\node[box, right=22mm of eval] (td) {inferred\\\texttt{TypedDict}};
\node[box, right=16mm of pg] (cmp) {compare\\names + types};
\draw[op] (stmt.north) to[out=60,in=180] (render.west);
\draw[op] (render) -- (pg);
\draw[op] (stmt.south) to[out=-60,in=180] (eval.west);
\draw[op] (eval) -- (td);
\draw[op] (pg.east) to[out=0,in=90] (cmp.north);
\draw[op] (td.east) to[out=0,in=-90] (cmp.south);
\end{tikzpicture}
\caption{The oracle evaluation. The same statement type is taken down two independent paths --- rendered and executed on PostgreSQL, and evaluated by \texttt{typemap} --- and the database's reported columns are compared against the inferred record.}
\end{figure}

Run over the subset **S**, every query class matches PostgreSQL exactly (Table I): identical column names, in the same order, with types that correspond one-to-one. The full row unwraps the primary key to `int`; the projection and alias name exactly what they select; the join merges both tables; and the aggregate query returns `{"id": int, "n_posts": int}` — the exact example from the design. One scope note on the `WHERE` case: what the oracle confirms is the *result* record `{"id": int, "email": str}`, since `cursor.description` reports output columns only. The inferred *parameter* mapping `{"min_age": int}` is a separate tysql fact — PostgreSQL validates it merely by accepting the parametrised query, and its correctness is asserted on the runtime and static tracks (the parameter-collection tests), not by the oracle.

\begin{table}[H]
\centering
\caption{tysql's inferred result record vs. PostgreSQL's reported columns, for each class in the subset S. Every case matches.}
\begin{tabular}{@{}p{0.40\linewidth} p{0.36\linewidth} c@{}}
\hline
Query class & Inferred / reported record & Match\\
\hline
\texttt{SELECT *} & \texttt{\{id:int, age:int, email:str\}} & exact\\
projection & \texttt{\{id:int, email:str\}} & exact\\
alias (\texttt{id AS user\_id}) & \texttt{\{user\_id:int\}} & exact\\
\texttt{WHERE age = :min\_age} & \texttt{\{id:int, email:str\}} & exact\\
\texttt{INNER JOIN} projection & \texttt{\{email:str, text:str\}} & exact\\
\texttt{JOIN}+\texttt{Count}+\texttt{GROUP BY} & \texttt{\{id:int, n\_posts:int\}} & exact\\
\hline
\end{tabular}
\end{table}

The more informative result is where **S** ends. The same harness then probes the oracle with raw SQL just past each edge — queries PostgreSQL accepts but tysql cannot express — and the ground truth it reports places every failure on a precision ladder (Fig. 7):

- **Degraded — right Python type, lost precision.** `Count` is typed `int`, but PostgreSQL returns `count(...)` as `bigint` (`int8`); the Python-level type is right and a driver hands back an `int`, but the exact SQL type is coarsened. The same coarsening would hide the *nullability* of `SUM`/`AVG` even if those were added.
- **Inexpressible — no type can be formed.** A projection with duplicate output names — `SELECT user.id, post.id` — returns *two* columns both named `id`; a `TypedDict` cannot hold two keys `id`, so the record model simply cannot represent it. `SUM`/`AVG` have no combinator at all. And outer joins are worse than unimplemented: a `LEFT JOIN` makes the right side's columns nullable, but PostgreSQL's row description does *not* mark them nullable (`null_ok` is unset), so even the oracle cannot confirm the property — it must be derived from the query's structure, which is exactly the kind of type-level reasoning that would have to be built.
- **Unsound — a wrong type is accepted.** `Where[Eq[Col[User, "email"], Param["p", int]]]` compares a `str` column to an `int` and is *accepted*: `Eq` never checks that its two sides are comparable. PostgreSQL rejects the rendered query outright (*"operator does not exist: text = integer"*). This is the one place tysql is not merely incomplete but wrong, and it is the sharpest answer to the sub-question "which ill-typed queries cannot be statically rejected": those whose ill-formedness is a *value-level* relationship (comparability, arithmetic) rather than a *name/shape* relationship. Column existence and scope are names and shapes, and those tysql checks; operand compatibility is a value-level fact, and there the current design is silent.

\begin{figure}[H]
\centering
\begin{tikzpicture}[font=\small, node distance=3mm]
\node[draw, thick, rounded corners, fill=green!8, inner sep=6pt, align=center, text width=0.9\linewidth] (a)
  {\textbf{Exact} --- inferred record = PostgreSQL columns\\ \footnotesize all of S: \texttt{SELECT *}, projection, alias, \texttt{WHERE} params, \texttt{INNER JOIN}, \texttt{Count}+\texttt{GROUP BY}};
\node[draw, thick, rounded corners, fill=yellow!12, inner sep=6pt, align=center, text width=0.78\linewidth, below=of a] (b)
  {\textbf{Degraded} --- right Python type, coarser SQL type\\ \footnotesize \texttt{Count} is \texttt{int} but PostgreSQL \texttt{count} is \texttt{bigint}};
\node[draw, thick, rounded corners, fill=orange!14, inner sep=6pt, align=center, text width=0.66\linewidth, below=of b] (c)
  {\textbf{Inexpressible} --- no type can be formed\\ \footnotesize duplicate names, \texttt{SUM}/\texttt{AVG}, outer-join nullability};
\node[draw, thick, rounded corners, fill=red!12, inner sep=6pt, align=center, text width=0.54\linewidth, below=of c] (d)
  {\textbf{Unsound} --- wrong type accepted\\ \footnotesize \texttt{Eq} over incomparable operands};
\end{tikzpicture}
\caption{The precision ladder. Everything in the subset S sits at the top rung; each step down is the first thing encountered past one of S's edges.}
\end{figure}

Read against the research question, the evaluation is decisive in both directions. Within a schema-shaped subset, PEP 827's facilities are *sufficient*: they infer the exact result record for every query in **S**, confirmed against the database itself, and they reject out-of-schema references exactly where PostgreSQL does. Outside it, the boundary is not vague — it is a small, nameable set of walls: value-level relationships the facilities do not reach, structural facts (duplicate names, outer-join nullability) the `TypedDict` model or the wire protocol cannot carry, and an incompleteness in the reference *checker* (recursion, nested comprehensions) that is a property of the prototype rather than of the proposal.

## Using it today: the CLI validator

The findings above assume a checker that understands PEP 827, which no released tool yet does — so a reasonable objection is that none of this is usable until the language accepts the proposal. It is usable now. Because the static track *is* a real (forked) `mypy`, tysql ships a thin command-line wrapper around it, so the same errors surface in an ordinary project today:

```bash
tysql check [PATH ...]   # type-check paths with the PEP 827-aware mypy fork
tysql mypy  [ARG ...]    # forward arguments straight to the fork
```

`tysql check some_file.py` reports, for instance, `Col: no such column` where a statement references a column that does not exist — precisely the diagnostic a stock checker will emit once PEP 827 is standard. The wrapper runs `python -m mypy` in the current interpreter and first checks that the importable `mypy` really is the fork (a marker file in the fork's bundled typeshed), warning otherwise that the combinator types will "collapse to `Any`." This is the concrete meaning of the abstract's claim that tysql is usable in two worlds: with the plugin-free runtime evaluator anyone gets the computed types at run time, and with the fork anyone gets the full static experience — a working preview of the post-acceptance world, and a way to give the proposal the real-project mileage its reviewers asked for.

# Analysis and discussion

The evaluation answers the research question, but the more interesting discussion is what the answer *means* for a proposal still under debate. PEP 827 is contested. On the discussion thread [24] a member of the Python Typing Council, Jelle Zijlstra, calls it "a chance to make the type system radically more powerful," while another core developer, Ivan Levkivskyi, records that he is "strong -1 on this PEP (and more broadly on the whole idea)." tysql is a piece of evidence in exactly that argument, and this section reads the results into it.

## Is a domain like this worth typing statically?

One recurring skeptical position on the thread is that computation-in-types is rarely worth it: *if your logic is dynamic enough to need, for instance, conditional types, then it is probably not worth trying to type it statically.* The evaluation lets this be answered with a case rather than an opinion. SQL is precisely such a domain — the result type is a conditional function of the query — and yet the payoff is not marginal. The gap the introduction opened with (a projection typed by position, a relationship traversal typed as an object graph the query never fetched) is closed for the whole subset **S**, and the closure is verified against the database itself, not merely asserted. The skeptic is right that not everything should be typed this way; the evaluation shows that a schema-shaped domain, where the type genuinely is a function of the inputs, is on the worthwhile side of that line. The place the skeptic is *most* right is the unsound rung: `Eq` over incomparable operands is a value-level relationship, and pretending it is a name/shape relationship is where the design over-reaches. That is a boundary to respect, not evidence the whole enterprise is misguided.

## A second language in the annotations

The strongest principled objection is not about SQL at all: PEP 827's combinators are, in effect, a small second language living inside type annotations, and — because it reuses Python's own `if/else` and comprehension syntax — a language that *looks* like ordinary Python while obeying different rules. This thesis met that gap concretely. The same alias can carry one meaning to `reveal_type` and another to a combinator that inspects it (the pre-/post-transform split of §*Two readings*); a `RaiseError` fires in a `Member`'s name slot but not its value slot; a chained conditional eagerly evaluates its untaken branch. None of these are bugs in tysql — they are places where the "looks like Python" surface diverges from Python's semantics, and every one had to be learned empirically. This is the real cost the objection points at: not that the feature is too powerful, but that its evaluation model is subtle enough that a library author cannot reason about it by Python intuition alone. The counter-argument the results support is narrower than "it is worth it": it is that the subtlety is *containable* behind a library. A tysql user writes `Select[User, Cols[…]]` and never sees a `Member` name slot; the second language is spoken by the library author, once, and the surface handed to the user is ordinary types. Whether the ecosystem wants even library authors writing that second language is the genuine, unresolved trade-off — and it is a policy question, not a technical one.

## Errors as types: `RaiseError`, not `Never`

A smaller design debate on the thread is settled cleanly by the evidence here, and it happens to be one where the Typing Council member and the PEP author agree: Zijlstra argues "it's a mistake to use `Never` for errors; that's not what it's meant for." The tysql experiments show *why* in operational terms. Returning `Never` to signal an ill-typed statement is silently absorbed — a `Never` is assignable to anything and appears to have every attribute, so `b: int = <Never>` and `<Never>.anything()` both type-check clean, and the error vanishes. `RaiseError[Literal["msg"]]` instead surfaces a diagnostic when evaluated, and does so *lazily* — a statement carrying it stays quiet until `run` forces resolution, so the error appears at the call site where it is actionable. The *name/scope* gates in tysql — an unknown column, a column whose table is not in the `FROM` — are built on `RaiseError` for exactly this reason; the *shape* gates — a missing, extra, or wrong-typed parameter or insert value — ride ordinary `TypedDict` checking (a `typeddict-item` error), because there the built-in mechanism already fails loudly. Both are honest; only the first needed `RaiseError` to become so. The finding is small but concrete feedback for the spec: error-signalling must be a first-class construct, because the bottom type cannot be repurposed for it.

## What acceptance would require

Zijlstra's constructive ask on the thread is specific: to move forward, the PEP "should make sure [it] gets implemented in typing-extensions and at least one type checker so people can play with it and we can get a sense for the edge cases." This thesis is, in a modest way, that exercise. It runs the facilities through two independent implementations, finds real edge cases (the fork's lack of recursion and nested comprehensions; the name-slot/value-slot asymmetry; the empty-`TypedDict` evaluator bug fixed upstream), and reports them. The broader requirement follows the trajectory of every prior typing feature: a portable surface needs `typing_extensions` staging, at least one conforming checker, and a conformance test suite, so that no guarantee depends on one checker's internals — the portability constraint PEP 484 set at the start [1]. There is a structural wrinkle worth stating plainly: some newer checkers (Astral's `ty`, and Pyright) decline to load third-party plugins, so the plugin route SQLAlchemy took is closed to them by design [7]. That makes the case for a *spec-able kernel* stronger, not weaker: only a standardised surface, not a plugin, can become first-class in every checker. tysql's subset **S** is a candidate shape for such a kernel — small, total, and demonstrably sufficient for a real domain.

## Discrepancies, limitations, and external validity

Several results are properties of the *prototype*, not the *proposal*, and honesty requires separating them. The `WHERE`-tree limitation and the file-level unsuppressable error are `mypy`-fork incompletenesses; they would not constrain a mature implementation and should not be read as PEP 827 limits. The duplicate-name and outer-join-nullability walls are genuinely structural — the former is a `TypedDict` limitation (no repeated keys), the latter a fact the wire protocol does not even carry — and would face any type-level SQL library in any language, including the Diesel/Squeal family [19][20]. The unsound `Eq` is a design gap in tysql that PEP 827 could close (an `IsAssignable` check between operands), and the fact that it is *closable* is itself a data point about the proposal's reach. Beyond SQL, the same machinery types other value-dependent shapes: the appendix reports a Pydantic `model_dump()` whose result is a precise `TypedDict` that flows into a `**kwargs` call the checker validates, which suggests the facilities are not SQL-specific but generally applicable wherever a type is a function of a schema. Finally, a performance concern raised on the thread — that re-evaluating annotations on every call would be expensive, "even for a tool like pydantic" — is real but orthogonal to this work: tysql's evaluation is a *type-checking-time* activity with no runtime cost on the static track, and the runtime track's cost is paid once per type, not per call.

## Where tysql sits among typed-SQL systems

The literature review split typed SQL into two families; the evaluation lets tysql be placed within them precisely. Against the *code-generation* family — `sqlx`, Prisma — tysql gives up their two advantages: those tools verify against the *real* database (`sqlx` at compile time) or a complete schema file, so they cover the full SQL surface and even catch the value-level mismatches tysql misses, because the authority doing the checking is the database or a generator, not the host type system. What tysql gains in return is what that family gives up: no build step, no generated artefact to drift, and — decisively for the research question — the types are computed *by Python's own type system*, so they compose with ordinary annotations and need no tool beyond the checker. Against the *type-level embedding* family — Diesel, Squeal — tysql is the same *kind* of thing, and the comparison is therefore the most honest measure of PEP 827's maturity. Squeal, in a language built for type-level programming, expresses outer-join nullability and richer predicates that tysql cannot; the gap is not that Python's approach is wrong but that its type-level facilities and, more acutely, their *prototype checker* are younger. The evaluation's contribution is to quantify that gap concretely: on subset **S** the embedding is exact and database-verified, and each step beyond it is a named, mostly-closable deficiency rather than a vague "not there yet."

## Threats to validity

Three qualifications bound the claims. First, the **oracle is not omniscient**: PostgreSQL's row description reports column names and type OIDs but not nullability, so the harness confirms names and value types exactly but cannot, by itself, adjudicate `T | None` versus `T` — the outer-join case is inferred from this limit, not merely from tysql's coverage. Second, the **schema is a toy**: the evaluation uses a small social-graph schema (users, posts), and while the query *classes* are representative of everyday CRUD, this is not a corpus study of real-world SQL; a wider survey could surface query shapes that stress the facilities differently. Third, and most important, several findings are properties of the **prototype, not the proposal** — the fork's lack of recursion and nested comprehensions, and the file-level unsuppressable error, are implementation limits of one experimental checker, and a conformant implementation could lift them; conversely, the exact-inference result depends on two prototypes *agreeing*, which is strong evidence but not a substitute for a conformance suite. These do not undermine the central finding — exact inference across **S**, verified against the database — but they scope how far it generalises.

# Conclusion

This thesis asked how far PEP 827's type-manipulation facilities can *well-type* a subset of PostgreSQL, and answered it by building a query builder in which every statement is a type and measuring the inferred result against the database itself. The answer is sharp in both directions. On a defined subset **S** — `CREATE TABLE`, `INSERT … RETURNING`, column projection with aliases, equality-`WHERE` with inferred parameters, and a single `INNER JOIN` with `Count`, `GROUP BY` and `ORDER BY` — the facilities are *sufficient*: tysql infers the exact result record for every query, confirmed column-for-column against PostgreSQL, and rejects out-of-schema references exactly where the database would. Outside **S** the limits are not vague but nameable: value-level comparison is unsound, `SUM`/`AVG` and outer-join nullability are inexpressible, and duplicate output names collapse the record — with the important caveat that some walls (recursion, nested comprehensions) belong to the reference checker, not the proposal.

The route there retraces the layers of Python's type system, each of which the work had to use in earnest: annotations are runtime objects (so a class can be inspected and rewritten); their static and runtime readings can diverge (so `TYPE_CHECKING` and the two-track methodology are load-bearing); since Python 3.14 annotations are lazily-evaluated expressions (so a runtime evaluator like `typemap` is viable at all); and PEP 827 adds, on top, the ability to *compute* over them. The practical contributions are a working type-level PostgreSQL builder and its CLI validator (usable today via the two prototype tracks, without waiting for language acceptance); a dual-track testing methodology with honest negative assertions; a reproducible PostgreSQL-oracle evaluation; and direct feedback to the proposal, including a merged fix to its reference evaluator and a concrete account of what standardisation requires.

The limitations are the walls above, and the ergonomic cost of writing columns as `Col[User, Literal["id"]]` rather than `User.id`. The next steps follow from the evaluation: closing the unsound `Eq` with an operand-compatibility check; extending the reference checker so `OR`-trees and outer-join nullability become expressible; and lowering the barrier to *seeing* what is now possible by building an online evaluator for tysql's types, at `tysql.vercel.app`, so the examples in this thesis can be run in a browser. The larger aim is unchanged: to give the community concrete evidence, from a real domain checked against a real database, that Python's long-hidden type-level computation can be turned into a designed, portable surface — and thereby to improve PEP 827's chances of acceptance.

# Appendix {.unnumbered}

## Beyond SQL: a precise `model_dump()` for Pydantic

The facilities are not SQL-specific. A separate case study, `pydantic_extension`, applies the same idea to Pydantic's `model_dump()`, whose declared return type is `dict[str, Any]` — it discards every field name and type. A PEP 827 alias recovers them:

```python
type ModelDump[T] = t.NewTypedDict[
    *[
        t.Member[field.name, field.type]
        for field in t.Iter[t.Attrs[T]]
        if t.IsAssignable[field.definer, _BaseModel]
        and not t.IsEquivalent[field.definer, _BaseModel]
        and not t.IsEquivalent[
            t.Slice[field.name, Literal[0], Literal[2]], Literal["__"]
        ]
    ]
]
```

The comprehension keeps each user-declared field, filters out Pydantic's internals (`__pydantic_fields__`, `model_config`, dunder attributes via the name-`Slice` guard), and rebuilds a `TypedDict`. A `BaseModel` subclass overriding `model_dump` to return `ModelDump[Self]` then makes the dump precise, and — the load-bearing usability claim — lets it spread into a function whose parameters are named after the fields, with the checker validating the call:

```python
def mypy_test_dump_spreads_into_matching_kwargs() -> None:
    if TYPE_CHECKING:

        def write_user(*, name: str, age: int) -> None: ...

        u = User(name="i3s", age=22)
        write_user(**u.model_dump())  # checked against {"name": str, "age": int}
```

Renaming a parameter, dropping one, or mistyping a value each becomes a static error, and the paired runtime test confirms `eval_typing(ModelDump[User]).__annotations__ == {"name": str, "age": int}`. A forward-looking test matrix maps which `model_dump` keyword arguments *could* be reflected in the type (`include`/`exclude` narrow keys; `exclude_unset`/`_none`/`_defaults` make keys `NotRequired`; `mode="json"` rewrites value types) and which are opaque by nature (`context`, `fallback`, `serialize_as_any`). The same result shows up as the appendix does for SQL: schema-shaped transformations are typeable; value-dependent ones at the edges are not.

## The PEP 692 × PEP 827 wall

One negative result is worth recording because it is a clean interaction between two PEPs. The natural way to type an `INSERT`'s keyword arguments is PEP 692's `Unpack` of a `TypedDict`: `def insert(**kwargs: Unpack[InsertInput[T]])`. It does not work. `Unpack[K]` for a `TypedDict`-bound `TypeVar` *infers* `K` from the caller's kwargs (it captures whatever is passed), which is the opposite of what an `INSERT` needs — the kwargs must be *constrained* to a pre-computed schema. Constraining via the bound (`K: InsertInput[T]`) fails because a bound cannot reference an earlier type parameter, and a *computed* bound is not recognised as a TypedDict bound. The computation itself is fine (`InsertInput[User]` evaluates correctly); the wall is specifically that a computed `TypedDict` cannot be *consumed* through PEP 692's `**kwargs`. The working alternatives — a positional `TypedDict` parameter, or synthesising the keyword signature in return position with `Params`/`Param[name, type, "keyword"]` — are what tysql uses instead, and the interaction is exactly the kind of edge case the standardisation process needs surfaced [16][12].

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
12. M. J. Sullivan et al. PEP 827 — Type Manipulation. Status: Draft; target: Python 3.16. <https://peps.python.org/pep-0827/>
13. I. Dzhabbarov. `python-typemap`: runtime evaluator for PEP 827 type manipulation (fork). <https://github.com/iliyasone/python-typemap>
14. `mypy-typemap`: a `mypy` fork evaluating PEP 827 combinators during type-checking. <https://github.com/iliyasone/mypy-typemap>
15. PEP 646 — Variadic Generics. <https://peps.python.org/pep-0646/>
16. PEP 692 — Using TypedDict for More Precise \*\*kwargs Typing. <https://peps.python.org/pep-0692/>
17. PEP 695 — Type Parameter Syntax. <https://peps.python.org/pep-0695/>
18. PEP 649 — Deferred Evaluation of Annotations Using Descriptors <https://peps.python.org/pep-0649/>; and PEP 749 — Implementing PEP 649 (the Python 3.14 refinement) <https://peps.python.org/pep-0749/>.
19. Diesel — A safe, extensible ORM and query builder for Rust. <https://diesel.rs/>
20. E. Chatav. Squeal — a deep embedding of PostgreSQL in Haskell. <https://hackage.haskell.org/package/squeal-postgresql>
21. Prisma — Next-generation ORM for Node.js and TypeScript. <https://www.prisma.io/docs>
22. `sqlx` — compile-time checked queries against a live database for Rust. <https://github.com/launchbadge/sqlx>
23. psycopg 3 documentation — cursor result metadata (`cursor.description`). <https://www.psycopg.org/psycopg3/docs/>
24. Python Discourse. PEP 827: Type Manipulation — discussion thread. <https://discuss.python.org/t/106353>
