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

## Abstract

Python's type system cannot express types produced by metaprogramming, yet metaprogramming is a native for Python and used

PEP 827 introduced new typing manipulation facilities to fill this gap. In this Thesis we will try to evaluate whenever this tools is actually enough to well-type something big, next level typings, which was not possible (to which extend we are clearly defined) before the PEP 827. Typing the untypable is now a reality: well-type PostgreSQL query builder.  Checkout demo at `github.com/iliyasone/tysql`

## 1. Introduction

Python type system is turing complete yet lacking expressivnes. 

Classes in Python are dynamically created and can be expected, updated during the runtime.

? stage 1: pure metatyping
```python
from enum import Enum

class Color(Enum):     # EnumMeta rewrites the body:
    RED = 1            #   `RED = 1` (a plain int)  ->  Color.RED (a Color *member object*)
    GREEN = 2
    BLUE = 3

Color.RED            # <Color.RED: 1>  — a singleton, not just 1
Color.RED.name       # 'RED'
Color.RED.value      # 1
list(Color)          # iterable: [<Color.RED: 1>, ...]
Color(99)            # ValueError at runtime — invalid value rejected
```
So even with **zero** static checking, an enum gives you: a distinct object (not a naked int), identity (`is`), a real `repr`, `.name`/`.value`, iteration, and **runtime rejection of invalid values**. That's all runtime.
he *static* benefit (`def paint(c: Color)` that a checker enforces, plus exhaustiveness checking in `match`) was a **bonus that arrived later** with PEP 484 — not the original reason:

? stage 2: static analysis
- Then the type hints was added gradually - introduced new layer: static analysis of a python types

```python
def p(c: Color) -> bool:
    if c == Color.RED:
        ...
    <make some expressive function which definetly knows >
```

? stage 3.

Type annotations are exist in the runtime itself - and used for advanced types introspection:

```python
>>> p.__annotations__
{"c": Color, "return": bool}
#     ^^^^^
#     reference to a class Color
>>> p.__annotations__["c"]() # can be used for an object construction.
```

the brightest example is fastapi 

```python
class User(BaseModel):
    id: int
    age: int
    email: str

@api.route("/v1/users")
def get_user(user_id: int) -> User:
    ...
```

<todo>there should be a picture of a documentation in swagger</todo>




### Current gap

The FastAPI using this for the generatic documentation based on the function signature.

<fix>probably SQL 2008 vs 20023 example is extra there... but it was nice!</fix>
Another good example of introspection of typehints is SQLalchemy 2008 vs 2023

Despite the big progress since 2008, we still have some cases 


```python
class User(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    registered_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # back-populated collections
    posts: Mapped[list[Post]] = relationship(back_populates="author")
    comments: Mapped[list[Comment]] = relationship(back_populates="author")


class Post(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id")) 
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    author: Mapped[User] = relationship(back_populates="posts")
    comments: Mapped[list[Comment]] = relationship(back_populates="post")


class Comment(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    post: Mapped[Post] = relationship(back_populates="comments")
    author: Mapped[User] = relationship(back_populates="comments")

>>> post = await session.scalar(select(Post).where(Post.id == 1))
>>> # post.comments  -> typed list[Comment], a type checker says it's fine
>>> # ...but it was NOT loaded by this query
```

we can't really now by the result itself, does the post.comments has their own comments?

In general, the type picking only by the
```python
row = session.execute(select(User.id, User.email)).one()
reveal_type(row[0])    # int   ✅ typed — positionally
reveal_type(row.id)    # Any   ❌ the NAME is not in the type
```
### Type manipulation facilities

> what should be there?

### Proposed solution

> and there?

## Analysis and discussion
- the main debate: does it needed to be in Python?
- what needed to be done so the PEP 827 would be accepted in Python?
- tysql plans and checks

## Literature review
<think>seems to put it in the so it would not distract the flow of a thesis</think>
