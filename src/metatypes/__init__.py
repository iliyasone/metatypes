# type: ignore
"""
Draft surface syntax for the `metatypes` DSL.

Nothing here is meant to be implemented at runtime yet; the plan is:
- the *syntax* or *interface* lives here as type aliases / combinators;
- a type-checker plugin (e.g. mypy) interprets these and evaluates them
  into ordinary PEP 484/544 types.

At runtime these are no-ops; the plugin is the only thing that gives
them semantics.
"""

type Equals[A, B] = ...
"""Proposition that A and B are the same type.
>>> A ≡ B
"""

type AnyNat = ...
"""Type-level natural number (dimension index).

This is a *kind marker* used only at the meta level.
The plugin treats AnyNat as “something that behaves like a non-negative int”
for the purpose of Add / Mul / Len / etc.
"""

type Add[N: AnyNat, M: AnyNat] = ...
"""Type-level addition on dimension-like integers.

Intended laws (enforced by static checkers):
>>> Add[0, N] ≡ N
>>> Add[N, 0] ≡ N
>>> Add[1, 1] ≡ 2
>>> Add[2, 3] ≡ 5
>>> Add[Add[A, B], C] ≡ Add[A, Add[B, C]]
"""

type Mul[N: AnyNat, M: AnyNat] = ...
"""Type-level multiplication on dimension-like integers"""

type Len[X] = ...
"""
Type-level length operator.

Defined only for types whose length is syntactically determined, e.g.:

- fixed-length tuple types:
>>> Len[tuple[]]                      ≡ 0
>>> Len[tuple[T0]]                    ≡ 1
>>> Len[tuple[T0, T1]]                ≡ 2
>>> Len[tuple[T0, ..., Tn-1]]         ≡ n

- length-indexed vectors:
>>> Len[Vector[T, N]]                 ≡ N

- string literals:
>>> Len[""]                           ≡ 0
>>> Len["a"]                          ≡ 1
>>> Len["abc"]                        ≡ 3

For any X where the length is not statically known (e.g. list[int],
Sequence[T], tuple[T, ...]), Len[X] is *undefined*. The plugin should
return AnyNat
"""


# Core combinators
type Intersection[A, B] = ...
"""A & B: values that satisfy (subclass) both A and B."""

type Not[T] = ...
"""Negation type: ~T"""


type If[Cond, Then, Else] = ...
"""Type-level conditional: If[Cond, Then, Else]."""


type GetAttr[T, Name] = ...
"""
Type of attribute `Name` on values of type `T`.

`Name` is intended to be a Literal[str].

Examples:
- GetAttr[User, "email"]           # -> str
- GetAttr[Request, "headers"]      # -> Mapping[str, str]
"""

type HasAttr[T, Name, AttrType] = Equals[GetAttr[T, Name], AttrType]
"""
Constraint: `T` has an attribute `Name` of type `AttrType`.

Example:
- HasAttr[User, "id", int]
- HasAttr[User, "email", str]
"""


def reveal_type(obj: object): ...
