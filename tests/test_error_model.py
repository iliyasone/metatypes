"""Error model + the chosen `sql(Insert[User])(...)` spelling.

Three facts, each proven below:
 1. `sql(Insert[User])(...)` enforces the synthesized kwargs (the user's spelling).
 2. Returning `Never` is SILENTLY ABSORBED — it cannot signal an ill-typed
    statement (bottom type: assignable to anything, has every attribute).
 3. `RaiseError[msg]` DOES surface a diagnostic when its type is evaluated.

So error-as-type must be backed by RaiseError (or native arg errors), NOT Never.

Run:
    uv run mypy --warn-unused-ignores --show-error-codes \
                --enable-error-code ignore-without-code tests/test_error_model.py
"""

from typing import TYPE_CHECKING, Any, Callable, Literal, Never, assert_type

import pytest
import typemap_extensions as t
from typemap.type_eval import eval_typing

from typed_sql.core import Column, Insert, PrimaryKey, Statement, Table


class User(Table):
    id: PrimaryKey[int]
    email: str
    age: int | None


class InsertStmt(Statement):
    pass


type InsertFn[T] = Callable[
    t.Params[
        *[
            t.Param[x.name, t.GetArg[x.type, Column, Literal[2]], Literal["keyword"]]
            for x in t.Iter[t.Attrs[T]]
            if not t.IsAssignable[x.type, Column[Any, Any, PrimaryKey[Any]]]
        ]
    ],
    InsertStmt,
]


def sql[T](statement: type[Insert[T]]) -> InsertFn[T]:
    raise NotImplementedError


def returns_never() -> Never:
    raise NotImplementedError


# ── 1. The chosen spelling: sql(Insert[User])(email=..., age=...) ────────────


def mypy_test_sql_insert_spelling() -> None:
    if TYPE_CHECKING:
        sql(Insert[User])(email="iliyas.dzabbarov@gmail.com", age=22)  # ok
        sql(Insert[User])(email="x")  # type: ignore[call-arg]  # missing age
        sql(Insert[User])(email=123, age=22)  # type: ignore[arg-type]  # wrong type


# ── 2. Never is silently absorbed — useless as an error signal ───────────────


def mypy_test_never_is_silently_absorbed() -> None:
    if TYPE_CHECKING:
        a: Never = returns_never()
        assert_type(a, Never)
        b: int = a  # Never -> int: NO error (bottom type)
        a.nonexistent_method()  # Never has EVERY attribute: NO error
        _ = b


# ── 3. RaiseError surfaces a real diagnostic when evaluated ──────────────────


def mypy_test_raise_error_surfaces() -> None:
    if TYPE_CHECKING:
        bad: t.RaiseError[Literal["sql: ill-typed expression"]]  # type: ignore[misc]
        _ = bad


# ── 4. Conditional RaiseError (PEP ternary) — the validity-gate primitive ─────
# `RaiseError[...] if Cond else T`. Surfaces as `error: <msg>` + then becomes Never
# (that residual Never is why bare Never alone is silent). Runtime: it RAISES.

type Guard[T] = t.RaiseError[Literal["T must not be str"]] if t.IsAssignable[T, str] else T


def make_int() -> Guard[int]:  # concrete good branch -> int, no fire
    raise NotImplementedError


def make_str() -> Guard[str]:  # type: ignore[misc]  # concrete bad branch -> RaiseError fires
    raise NotImplementedError


def mypy_test_conditional_raise_error_concrete() -> None:
    if TYPE_CHECKING:
        assert_type(make_int(), int)


def test_conditional_raise_error_runtime() -> None:
    assert eval_typing(Guard[int]) is int
    with pytest.raises(Exception, match="T must not be str"):
        eval_typing(Guard[str])


# NOTE (observed at module level, not enshrined here because it's context-
# dependent): a conditional RaiseError placed in a *generic* function's
# return/param can be evaluated at definition with T unbound and mis-fire. Keep
# the validity gate in the CONCRETE type the user writes (e.g. Insert[User,
# Default]), not in sql()'s generic signature.
