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

# Core combinators
type Intersection[A, B] = ...
"""A & B: values that satisfy (subclass) both A and B."""

type Not[T] = ...
"""Negation type: ~T"""


type If[Cond, Then, Else] = ...
"""Type-level conditional: If[Cond, Then, Else]."""

type Equals[A, B] = ...
"""Proposition that A and B are the same type."""

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

__all__ = [
    "Intersection",
    "Not",
    "IfEquals",
    "GetAttr",
    "HasAttr",
]
