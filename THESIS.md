---
title: "Well-Typed PostgreSQL in Python: The Limits of PEP 827's Type Manipulation"
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

A checker reports `int` for `row[0]` but `Any` for `row.id`: the value is typed only by position, never by name. SQLAlchemy 2.0 gives this projection the type `Row[tuple[int, str]]` — the column names are gone. The same blind spot appears with relationships: a loaded `Post` is typed as if `post.comments` were always a `list[Comment]`, even when the query never fetched them.

Recovering the names — a precise record `{"id": int, "email": str}` — and rejecting queries that do not type-check is exactly what PEP 827's type manipulation makes possible, and what the rest of this thesis builds and measures.

# Type manipulation facilities

> what should be there?

## Proposed solution

> and there?

# Analysis and discussion
- the main debate: does it needed to be in Python?
- what needed to be done so the PEP 827 would be accepted in Python?
- tysql plans and checks

# Literature review
<think>seems to put it in the so it would not distract the flow of a thesis</think>
