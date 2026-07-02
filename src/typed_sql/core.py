"""Minimal typed-SQL core.

A `Table` subclass declares columns as plain annotations (`id: int`). Two halves
keep static and runtime in agreement:

* static  — `__init_subclass__` returns `UpdateClass[...]`, so the mypy-typemap
  plugin rewrites every annotation `id: int` into `id: Column[Self, "id", int]`,
  carrying owner + name + value-type.
* runtime — the same `__init_subclass__` body materialises each annotation as a
  real `Column` descriptor, so `User.id` exists at runtime with the same info.
"""

from typing import Any, Literal, get_type_hints

import typemap_extensions as t


class Column[Owner, Name, T]:
    """Type of a column reference. Statically `Column[Owner, name, value-type]`;
    at runtime a small descriptor carrying the same triple."""

    def __init__(self, owner: type, name: str, type_: Any) -> None:
        self.owner = owner
        self.name = name
        self.type = type_

    def __repr__(self) -> str:
        tn = getattr(self.type, "__name__", repr(self.type))
        return f"Column({self.owner.__name__}.{self.name}: {tn})"


class SerialPrimaryKey[T]:
    pass


class ForeignKey[Ref, Name]:
    pass


# The INSERT input row, computed at the *type* level from the schema: every
# non-SerialPrimaryKey column becomes a REQUIRED key with its declared type. This is
# the contract that makes `Insert[User]({...})` demand exactly email + age.
#
# Consumed as a positional TypedDict ("values by keys"), NOT as **kwargs.
# `Unpack[TypedDict]` works for HAND-WRITTEN TypedDicts but NOT computed ones:
# generic `Unpack[InsertInput[T]]` is rejected ("must be a TypedDict or a TypeVar
# with TypedDict bound"); concrete `Unpack[InsertInput[User]]` is mis-expanded
# (PK filter dropped + GetArg errors). The gap is precisely PEP 692 x PEP 827.
# (model_dump dodges it by living in RETURN position; Self does not rescue it.)
# Also: overloading a fn with a computed-type param crashes the checker. So the
# one clean route is a positional TypedDict on a NON-overloaded constructor.
type InsertInput[T] = t.NewTypedDict[
    *[
        t.Member[x.name, t.GetArg[x.type, Column, Literal[2]]]
        for x in t.Iter[t.Attrs[T]]
        if not t.IsAssignable[x.type, Column[Any, Any, SerialPrimaryKey[Any]]]
    ]
]


class Statement:
    """Base type for a single SQL statement expressed as a value."""


class CreateTable[T](Statement):
    pass


# Type-only statement modifiers — composed in the statement's subscript:
#   Insert[User, Many]                  multi-row VALUES
#   Insert[User, Default]               DEFAULT VALUES
#   Insert[User, OrIgnore]              INSERT OR IGNORE
#   Insert[User, OrReplace]             INSERT OR REPLACE
#   Insert[User, Returning[Literal["id"]]]   RETURNING id
#   Insert[User, Returning[All]]        RETURNING *
class Many:
    pass


class Default:
    pass


class OrIgnore:
    pass


class OrReplace:
    pass


class All:
    pass


class Returning[*Names]:
    pass


class Insert[T, *Mods](Statement):
    pass


class Table:
    def __init_subclass__[T](
        cls: type[T],
    ) -> t.UpdateClass[
        *[t.Member[x.name, Column[T, x.name, x.type]] for x in t.Iter[t.Attrs[T]]]
    ]:
        # runtime half: turn each annotation into a real Column descriptor
        for name, ann in get_type_hints(cls).items():
            setattr(cls, name, Column(cls, name, ann))
        return None  # type: ignore[return-value]


# Consumers — GOAL surface, intentionally UNIMPLEMENTED (see tests/test_insert.py).
# `sql(<type-level statement>)` returns a template; calling the template fills the
# :name data; `run` executes (typed result), `render` returns the SQL text.
def sql(statement: object) -> Any:
    raise NotImplementedError


def run(statement: object) -> Any:
    raise NotImplementedError


def render(statement: object) -> str:
    raise NotImplementedError
