# A Meta-Type System for Python: An Expressive Library for Static Typing

> 🛠️ **Note:** This package is a work in progress. If you’d like to contribute or discuss ideas, feel free to reach out on Telegram [@iliyasone](https://t.me/iliyasone) or by email: [iliyas.dzabbarov@gmail.com](mailto:iliyas.dzabbarov@gmail.com).  
> 🚧 For now, this repository serves as the homepage for my thesis. Later it will become a standalone library and a mypy plugin.

#### Abstarct Aiming
Python’s static type system is formally Turing complete, yet its practical expressiveness remains limited. For more than a decade, the Python community has debated the addition of basic constructs like the Intersection type, but these have yet to be accepted. Most modern type checkers, such as Pyright and Ty, do not offer any mechanism for extensibility at the meta-type level. Their position is that libraries should not rely on plugins but should use the standard PEP approach. I can agree with this view to some extent. Mypy does provide a clear way to write plugins, but each plugin is specific to a particular library. This leaves many advanced patterns — such as well-typed SQL in ORMs — either impossible or forced into tool-specific plugins or code generation tools. In this thesis, I want to introduce and develop a meta-type system for Python, packaged as an experimental library, which enables the definition and evaluation of advanced type-level constructs through a unified interface. My aim is not to propose a PEP or to challenge the core language philosophy, but to demonstrate a practical approach to expressive type checking that may be used by community-driven libraries and static analysis tools to declare typing constructs previously unachievable. The library is designed to be fully compatible with the optional, tool-enforced nature of type hints. I believe that a meta-type layer can substantially increase the power and utility of static type checking in Python, without requiring changes to the language itself. These types will be checked by a custom mypy plugin written by me, and I will be seeking recognition by Ty and Pyright.

## 1. Introduction
### 1.1 Background 

Python’s type system has expanded from simple optional hints into a mix of nominal types, structural protocols, and checker-specific extensions. Yet many libraries now depend on logic that goes beyond these standard constructs, and they achieve it by embedding custom rules inside type checker plugins. This effectively creates **hidden meta-typing** inside tools like mypy, but it is fragmented, undocumented, and inconsistent across type checkers. Newer checkers such as Ty show that richer type operators—like intersections — are feasible, but Python still lacks a unified user-level way to express type-level computation or constraints. As a result, developers who need expressive static guarantees rely on ad-hoc mechanisms rather than a coherent meta-type system.


### 1.2 Problem Statement

Although Python’s type system has become more expressive, it still cannot represent many useful static invariants that appear naturally in real code. There is no unified way to perform type-level computation or to combine constraints through operators such as intersections, refinements, or length-indexed relationships. As a result, even simple specifications that a programmer might reasonably want to express remain impossible, for example typing an intersection of behaviours (`User & Admin`) or describing an operation on length-indexed data (`Vec[T, N] → Vec[T, N+1]`). Current type checkers support such patterns only through ad-hoc plugins or not at all, which prevents developers from writing precise, composable typings for advanced libraries. What is missing is a coherent meta-typing layer that allows these constraints to be expressed directly and checked consistently.


### 1.3 Design Solution
#### 1.3.1 Fixed-Length Vector Operations
Consider the following proposed meta-types: `Add`, `AnyNat`, `Mul`, `Len`, and `Equals` (see their documentation in [`src/metatypes/__init__.py`](https://github.com/iliyasone/metatypes/blob/main/src/metatypes/__init__.py)). With these primitives, it becomes possible to express and statically check the full suite of fixed-length vector operations in Python. The file [`vectors.py`](https://github.com/iliyasone/metatypes/tree/main/examples/vectors.py) is not part of the library itself, but serves as an expressive example. It is intended to type-check correctly out of the box.

[`vectors.py`](https://github.com/iliyasone/metatypes/tree/main/examples/vectors.py)
```python
class Vector[Typ, N]:
    """Vector of length N with elements of type Typ."""

def matmul[Typ, N: AnyNat, K: AnyNat, M: AnyNat](
    a: Vector[Vector[Typ, K], N],       # Matrix (N x K)
    b: Vector[Vector[Typ, M], K],       # Matrix (K x M)
) -> Vector[Vector[Typ, M], N]:         # Matrix (N x M)
    """Matrix multiplication: (N x K) * (K x M) = (N x M)"""
```

#### 1.3.2 Intersection Type

From [CarliJoy/intersection_examples](https://github.com/CarliJoy/intersection_examples/blob/main/legacy_examples/typed_dict.py):
```python
from typing import TypedDict
from metatypes import Intersection


class Movie(TypedDict):
    name: str
    year: int


class BookBased(TypedDict):
    based_on: str


def foobar() -> Intersection[Movie, BookBased]:
    return {
        "name": "Name",
        "year": 123,
        "based_on": "Movie",
    }
```

#### 1.3.3 Well-Typed SQL Queries in ORM
> 🛠️ *Work In Progress* 🚫
I am exploring which exact meta-types are required to correctly type expressions like the one below. As of December 3, 2025, I do not yet have a theoretical solution.

```python
from metatypes import Intersection, Row, Select, Join, ...
from future_orm import BaseTable, select

class Table(BaseTable):
    pass

class User(Table):
    id: int
    email: str

class Post(Table):
    id: int
    title: str
    published: bool
    author_id: int

rows = (
    select(User.email, Post.title)
    .join(Post, User.id == Post.author_id)
    .where(Post.published == True)
)
reveal_type(rows)  # E: Any 🚫
```

Expected:

```python
reveal_type(rows)  # E: Record[email: str, title: str]
```



## 2. Literature Review  (draft)
> 🛠️ *Work In Progress*

### 2.1 Key community discussions and proposals

[Opened Oct 16, 2014 – Closed Jan 14, 2015]
[An Intersection type? · Issue #18 · python/typing](https://github.com/python/typing/issues/18)  
Early discussion about adding an `Intersection` type to the standard typing module; Guido basically says “not now”, so the idea is postponed rather than designed. ([GitHub][1])

[Opened May 6, 2016 – still open ~9 years later]
[Introduce an Intersection · Issue #213 · python/typing](https://github.com/python/typing/issues/213)  
Main long-running issue about intersection types in the `typing` repo: semantics, use-cases, and open design questions; still not resolved after almost a decade. ([GitHub][2])

[Opened Jul 14, 2016]
[A milestone for dropping provisional status? · Issue #247 · python/typing](https://github.com/python/typing/issues/247)  
General discussion about moving `typing` out of provisional status; explicitly lists “Introduce an Intersection #213” as one of the “smaller things” that *should* be easy to implement but never actually landed. ([GitHub][3])

[Opened Apr 19, 2025]
[[RFC] Latest status of draft · Issue #53 · CarliJoy/intersection_examples](https://github.com/CarliJoy/intersection_examples/issues/53)  
Status thread for a nearly-ready PEP draft on user-denotable intersection types (and carefully limited negation); includes a PDF draft and discussion of which motivating examples to keep. ([GitHub][4])


### 2.2 Checkers and plugin philosophy

[Opened Apr 5, 2020]
[Plugins? · Issue #607 · microsoft/pyright](https://github.com/microsoft/pyright/issues/607)
Pyright maintainers explain why they **won’t** add a mypy-style plugin system: they see too many problems with a proprietary plugin model and prefer to keep semantics in the core checker instead of arbitrary user code. ([GitHub][6])

### 2.3 Python type hints as a Turing-complete meta language

[Paper, 2022–2023]
[Python Type Hints are Turing Complete – Ori Roth (arXiv / ECOOP 2023)](https://arxiv.org/abs/2208.14755)   
Formal result showing that PEP 484’s subtyping relation can simulate Turing machines, so Python’s type hints are *in principle* a Turing-complete meta language; also discusses the undecidability and performance implications for real checkers. ([arXiv][8])

[GitHub implementation]
[OriRoth/python-typing-machines](https://github.com/OriRoth/python-typing-machines)  
Reference implementation that compiles Turing machines into Python type hints (“subtyping machines”), demonstrating the theoretical construction against real tools like mypy. ([GitHub][9])

### 2.4 Negation / “hidden” intersection behaviour in today’s typing

[Blog / note]
[Gradual negation types and the Python type system – Jelle Zijlstra](https://jellezijlstra.github.io/negation-types.html)  
Explains how *negation types* fit into Python’s gradual type system and argues that explicit negation operators shouldn’t be added (yet), but also shows how current control-flow narrowing already behaves like a form of implicit negation. ([Discussions on Python.org][10])

[Opened Feb 18, 2023]
[Type guard doesn’t intersect types like instance check · Issue #1351 · python/typing](https://github.com/python/typing/issues/1351)  
Discussion showing that `isinstance` checks effectively produce intersection-like behaviour in type checkers, and that current type guard APIs do not fully capture that, highlighting how intersection / negation behaviour is already implicit in control flow. ([GitHub][11])


[1]: https://github.com/python/typing/issues/18?utm_source=chatgpt.com "An Intersection type? · Issue #18 · python/typing"
[2]: https://github.com/python/typing/issues/213?utm_source=chatgpt.com "Introduce an Intersection · Issue #213 · python/typing"
[3]: https://github.com/python/typing/issues/247?utm_source=chatgpt.com "A milestone for dropping provisional status? #247"
[4]: https://github.com/CarliJoy/intersection_examples/issues/53 "[RFC] Latest status of draft · Issue #53 · CarliJoy/intersection_examples · GitHub"
[5]: https://discuss.python.org/t/proposal-add-a-true-union-merge-join-intersection-type-annotation/39386?utm_source=chatgpt.com "Add a \"true union\" / merge / join / intersection type annotation"
[6]: https://github.com/microsoft/pyright/issues/607?utm_source=chatgpt.com "Plugins? · Issue #607 · microsoft/pyright"
[7]: https://docs.basedpyright.com/v1.23.1/usage/mypy-comparison/?utm_source=chatgpt.com "Mypy comparison"
[8]: https://arxiv.org/abs/2208.14755?utm_source=chatgpt.com "Python Type Hints are Turing Complete"
[9]: https://github.com/OriRoth/python-typing-machines?utm_source=chatgpt.com "Python type hints are Turing complete."
[10]: https://discuss.python.org/t/clarifying-the-float-int-complex-special-case/54018?page=4&utm_source=chatgpt.com "Clarifying the float/int/complex special case - Page 4 - Typing"
[11]: https://github.com/python/typing/issues/1351?utm_source=chatgpt.com "Type guard doesn't intersect types like instance check #1351"

## Chapters which are not yet in progress:
3. Design and Methodology 
4. Implementation and Results
5. Analysis and Discussion
6. Conclusion
