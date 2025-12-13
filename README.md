# A Meta-Type System for Python: An Expressive Library for Static Typing

> 🛠️ **Note:** This package is a work in progress. If you'd like to contribute or discuss ideas, feel free to reach out on Telegram [@iliyasone](https://t.me/iliyasone) or by email: [iliyas.dzabbarov@gmail.com](mailto:iliyas.dzabbarov@gmail.com).  
> 🚧 For now, this repository serves as the homepage for my thesis. Later it will become a standalone library and a mypy plugin.

#### Abstarct Aiming
Python's static type system is formally Turing complete, yet its practical expressiveness remains limited. For more than a decade, the Python community has debated the addition of basic constructs like the Intersection type, but these have yet to be accepted. Most modern type checkers, such as Pyright and Ty, do not offer any mechanism for extensibility at the meta-type level. Their position is that libraries should not rely on plugins but should use the standard PEP approach. I can agree with this view to some extent. Mypy does provide a clear way to write plugins, but each plugin is specific to a particular library. This leaves many advanced patterns — such as well-typed SQL in ORMs — either impossible or forced into tool-specific plugins or code generation tools. In this thesis, I want to introduce and develop a meta-type system for Python, packaged as an experimental library, which enables the definition and evaluation of advanced type-level constructs through a unified interface. My aim is not to propose a PEP or to challenge the core language philosophy, but to demonstrate a practical approach to expressive type checking that may be used by community-driven libraries and static analysis tools to declare typing constructs previously unachievable. The library is designed to be fully compatible with the optional, tool-enforced nature of type hints. I believe that a meta-type layer can substantially increase the power and utility of static type checking in Python, without requiring changes to the language itself. These types will be checked by a custom mypy plugin written by me, and I will be seeking recognition by Ty and Pyright.

## 1. Introduction
### 1.1 Background 

Python's type system has expanded from simple optional hints into a mix of nominal types, structural protocols, and checker-specific extensions. Yet many libraries now depend on logic that goes beyond these standard constructs, and they achieve it by embedding custom rules inside type checker plugins. This effectively creates **hidden meta-typing** inside tools like mypy, but it is fragmented, undocumented, and inconsistent across type checkers. Newer checkers such as Ty show that richer type operators—like intersections — are feasible, but Python still lacks a unified user-level way to express type-level computation or constraints. As a result, developers who need expressive static guarantees rely on ad-hoc mechanisms rather than a coherent meta-type system.


### 1.2 Problem Statement

Although Python's type system has become more expressive, it still cannot represent many useful static invariants that appear naturally in real code. There is no unified way to perform type-level computation or to combine constraints through operators such as intersections, refinements, or length-indexed relationships. As a result, even simple specifications that a programmer might reasonably want to express remain impossible, for example typing an intersection of behaviours (`User & Admin`) or describing an operation on length-indexed data (`Vec[T, N] → Vec[T, N+1]`). Current type checkers support such patterns only through ad-hoc plugins or not at all, which prevents developers from writing precise, composable typings for advanced libraries. What is missing is a coherent meta-typing layer that allows these constraints to be expressed directly and checked consistently.


### 1.3 Design Solution
#### 1.3.1 Fixed-Length Vector Operations
Consider the following proposed meta-types: `Add`, `AnyNat`, `Mul`, `Len`, and `Equals` (see their documentation in [`src/metatypes/__init__.py`](https://github.com/iliyasone/metatypes/blob/main/src/metatypes/__init__.py)). With these primitives, it becomes possible to express and statically check the full suite of fixed-length vector operations in Python. The file [`vectors.py`](https://github.com/iliyasone/metatypes/tree/main/examples/vectors.py) is not part of the library itself, but serves as an expressive example. It is intended to type-check correctly out of the box.

[`vectors.py`](https://github.com/iliyasone/metatypes/tree/main/examples/vectors.py)
```python
from metatypes import AnyNat, reveal_type

class Vector[Typ, N]:
    """Vector of length N with elements of type Typ."""

def matmul[Typ, N: AnyNat, K: AnyNat, M: AnyNat](
    a: Vector[Vector[Typ, K], N],       # Matrix (N x K)
    b: Vector[Vector[Typ, M], K],       # Matrix (K x M)
) -> Vector[Vector[Typ, M], N]:         # Matrix (N x M)
    """Matrix multiplication: (N x K) * (K x M) = (N x M)"""

def example():
    ...
    mat_a: Vector[Vector[float, 2], 3]  # 3x2
    mat_b: Vector[Vector[float, 4], 2]  # 2x4
    mat_c = matmul(mat_a, mat_b)  # (3x2) * (2x4) = (3x4)
    reveal_type(mat_c)  # E: Vector[Vector[float, 4], 3]
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



## 2. Literature Review

### 2.1 Preamble

Python's static typing layer is intentionally optional and tool-oriented, which makes portability across type checkers a first-order constraint rather than a convenience. PEP 484 frames type hints as a standard notation primarily for offline static analysis tools, not as a mechanism that changes runtime semantics. ([Python Enhancement Proposals (PEPs)][1]) This design choice creates a recurring tension: libraries and frameworks routinely exploit dynamic patterns that are easy to implement at runtime but hard to specify precisely using only the shared, standardized annotation language.

This chapter investigates why Python's standard static typing fails to express certain value-dependent typing relationships, and uses those limitations to motivate a portable meta-typing mechanism as a common layer.

### 2.2 The standardized typing surface and its philosophy

PEP 484 standardizes the syntax and baseline meaning of type annotations and explicitly prioritizes static analysis by external tools. ([Python Enhancement Proposals (PEPs)][1]) Within that model, nominal typing via classes and generics provides the default way to structure APIs, while leaving runtime behavior unchanged by design. ([Python Enhancement Proposals (PEPs)][1])

PEP 544 extends the ecosystem with structural subtyping via `Protocol`, enabling "static duck typing" when a nominal hierarchy would be unnatural or unavailable. ([Python Enhancement Proposals (PEPs)][2]) PEP 544 only describes structural constraints on existing objects; it provides no mechanism for constructing new types whose structure depends on runtime values. ([Python Enhancement Proposals (PEPs)][2])

PEP 681 introduces `typing.dataclass_transform`, a purely **declarative marker** that communicates a specific, well-known pattern of runtime code generation to type checkers. ([Python Enhancement Proposals (PEPs)][3]) The decorator performs no transformation itself and imposes no runtime semantics; its sole function is to inform static analyzers that a class should be treated *as if* it followed dataclass-like rules for field definition and constructor synthesis. ([Python Enhancement Proposals (PEPs)][3]) By standardizing this signal rather than the transformation logic, PEP 681 illustrates a recurring design choice in Python's typing ecosystem: instead of standardizing type-level computation, it standardizes a fixed declarative signal that multiple checkers can interpret uniformly.


### 2.3 Portability as a constraint and the shape of the expressiveness gap

Because the shared typing language is consumed by multiple checkers with different implementations, any typing guarantee that depends on the internal logic of a single checker does not count as a reliable or standard guarantee in Python's typing ecosystem. ([Python Enhancement Proposals (PEPs)][1])

Most hard Python typing problems are not arbitrary; they share a single cause: the type depends on runtime values, and the standard typing language has no portable way to express that dependency.

### 2.4 Pressure points

#### 2.4.1 A typed ORM-style projection: TypeScript vs Python

What does "select arbitrary columns and get a statically checked record type" look like in a language with built-in type-level object transformations?

TypeScript provides a standard type operator (`Pick`) that constructs a new object type from a base type and a set of keys. ([TypeScript][4]) Const assertions preserve literal key information for inference, which allows a value-level list of keys to drive a precise return type. ([TypeScript][5])

```ts
// TypeScript: value-driven projection with a precise statically computed return type

type UserRow = {
  id: number;
  email: string;
  age: number;
  isAdmin: boolean;
};

function select<RowT, Keys extends readonly (keyof RowT)[]>(
  row: RowT,
  keys: Keys
): Pick<RowT, Keys[number]> {
  const out = {} as Pick<RowT, Keys[number]>;
  for (const k of keys) out[k] = row[k];
  return out;
}

const row: UserRow = { id: 1, email: "a@b.com", age: 30, isAdmin: false };

const projected = select(row, ["id", "email"] as const);
// projected: { id: number; email: string }

projected.id.toFixed(0);
projected.email.toUpperCase();

// ✅ static check pass: 
// @ts-expect-error Property 'age' does not exist
projected.age;
```

**Question:** What is the closest portable Python equivalent?

Python can implement the runtime behavior trivially, but the shared typing language has no way to name the resulting type as a function of the input values. In particular, it cannot state the claim "the result has exactly these keys" when those keys are supplied as a runtime list, even though that claim is well-defined at execution time. ([Python Enhancement Proposals (PEPs)][1])

```py
# Python: runtime projection is easy, but typing usually collapses to imprecision.

from typing import Any

def select(row: dict[str, Any], keys: list[str]) -> dict[str, Any]: 
    out: dict[str, Any] = {} 
    for k in keys:
        out[k] = row[k]
    return out

row = {"id": 1, "email": "a@b.com", "age": 30, "isAdmin": False}

projected = select(row, ["id", "email"])
projected["id"].to_bytes(2, "little") # reveal type: Any
# 🚫 type checker cannot rely on int here

projected["age"] 
# 🚫 not rejected: key-level precision is lost
```

Recovering a precise return type would require the ability to construct a new record type by selecting an arbitrary subset of fields from an existing class or `TypedDict`. Python's standard typing provides no such operation: it cannot express field-level transformations over a class. This limitation is particularly acute for ORM-style APIs, where selecting, projecting, or reshaping model fields is a core operation.

#### 2.4.2 Intersection, negation, and the limits of standardized type algebra

Union types are part of modern Python typing syntax, but intersection and negation are not standardized as user-denotable operators in the core annotation language. ([Jelle Zijlstra][6]) The absence matters because many flow-sensitive narrowing arguments are naturally described using set-theoretic operations, especially when excluding cases. ([Jelle Zijlstra][6])

The typing community has discussed adding intersection and negation in various forms for years, if not decades, with proposals and threads showing both utility and subtle interactions with gradual typing and `Any`. ([GitHub][7]) Zijlstra's analysis makes the set-theoretic perspective explicit and notes that intersections can serve as an internal device for expressing narrowing results even when they are not exposed as part of the standard surface. ([Jelle Zijlstra][6])

Intersection types already exist in Python typing in practice, but not as a standardized, explicitly defined construct. Different checkers approximate intersection-like behavior using their own internal representations and narrowing rules—for example, `ty` and Pyright each implement their own notion of intersections. This results in fragmentation of the effective type system: the same annotated program can admit different inferred guarantees depending on the checker, even though no shared syntax or semantics for intersections has been agreed upon. ([Astral Docs][8])

### 2.5 Tooling-based recovery of precision: plugins and declarative hooks

Mypy's plugin system exists specifically to model patterns that the standard annotation surface cannot express directly, by letting a library supply callbacks that influence how mypy type-checks code using that library. ([Mypy Blog][9]) This mechanism makes it possible to "teach" the checker about decorators, class construction patterns, and domain-specific APIs without changing Python's language specification. ([Mypy Blog][9])

SQLAlchemy's mypy support illustrates both the value and the cost of this approach. The SQLAlchemy documentation describes how PEP 484 annotations interact with ORM mappings and how the plugin/stubs ecosystem historically provided additional precision for declarative patterns. ([SQLAlchemy][10]) At the same time, the SQLAlchemy 2.0 changelog records compatibility breakage between the deprecated plugin and newer mypy versions, and it recommends migrating away from that approach rather than relying on a fragile coupling to mypy internals. ([SQLAlchemy][11]) This is a concrete example of a general failure mode: checker-specific plugins can encode powerful type-level behavior, but they can become maintenance liabilities and interoperability barriers over time.

PEP 681 occupies a middle ground between "do nothing" and "full plugin logic" by standardizing a declarative marker for a common transformation family. ([Python Enhancement Proposals (PEPs)][3]) The existence of `dataclass_transform` suggests that the ecosystem benefits when dynamic code generation patterns are captured as shared, explicit contracts that multiple tools can implement consistently. ([Python Enhancement Proposals (PEPs)][3])

### 2.6 Theoretical substrate: expressiveness exists, ergonomics does not

Roth proves that Python's type-hinting system is formally Turing complete, meaning that arbitrary computation can be encoded into subtyping relationships. This establishes that the limitation of Python typing is not a lack of expressive power in principle, but the absence of a designed, readable, and portable surface for expressing value-dependent type relationships. ([arXiv][12])

### 2.7 Conclusion

The literature converges on a consistent picture: Python's standardized typing surface is intentionally constrained to preserve interoperability, while real-world libraries frequently demand value-driven type relationships that exceed what can be expressed portably. PEP 681 demonstrates that standardization can succeed when the dynamic pattern is captured as a declarative contract, whereas plugin-based solutions demonstrate that checker-specific power can be practical but brittle. ([Python Enhancement Proposals (PEPs)][3]) Roth's Turing-completeness result closes the "is it possible" question at the theoretical level, leaving the engineering question of how to expose a usable, bounded, and tool-portable meta-typing mechanism. ([arXiv][12])

In the remainder of the thesis, these constraints motivate an opt-in design that treats meta-typing as shared infrastructure rather than as per-library bespoke plugins, with explicit limits to keep evaluation predictable and to preserve the multi-checker portability that PEP 484 treats as fundamental. ([Python Enhancement Proposals (PEPs)][1])

[1]: https://peps.python.org/pep-0484/ "PEP 484 – Type Hints - Python Enhancement Proposals"
[2]: https://peps.python.org/pep-0544/ "PEP 544 – Protocols: Structural subtyping (static duck typing)"
[3]: https://peps.python.org/pep-0681/ "PEP 681 – Data Class Transforms"
[4]: https://www.typescriptlang.org/docs/handbook/utility-types.html "Documentation - Utility Types"
[5]: https://www.typescriptlang.org/docs/handbook/2/everyday-types.html "TypeScript: Documentation - Everyday Types"
[6]: https://jellezijlstra.github.io/negation-types.html "Gradual negation types and the Python type system"
[7]: https://github.com/python/typing/issues/213 "Introduce an Intersection · Issue #213 · python/typing"
[8]: https://docs.astral.sh/ty/ "ty"
[9]: https://mypy-lang.blogspot.com/2019/03/extending-mypy-with-plugins.html "Extending mypy with plugins"
[10]: https://docs.sqlalchemy.org/en/latest/orm/extensions/mypy.html "Mypy / Pep-484 Support for ORM Mappings"
[11]: https://www.sqlalchemy.org/changelog/CHANGES_2_0_40 "2.0 Changelog — SQLAlchemy 2.0 Documentation"
[12]: https://arxiv.org/abs/2208.14755 "Python Type Hints are Turing Complete"

## Chapters which are not yet in progress:
3. Design and Methodology 
4. Implementation and Results
5. Analysis and Discussion
6. Conclusion
