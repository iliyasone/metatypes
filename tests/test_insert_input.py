"""Can a COMPUTED TypedDict (`InsertInput[T]`) be consumed via PEP 692 `Unpack`?

Answer: NO on the static track (mypy-typemap). The form you'd actually write,
`def f[T](..., **kwargs: Unpack[InsertInput[T]])`, is rejected. The COMPUTATION
itself is fine — `InsertInput[User]` evaluates to the right TypedDict — so the
gap is specifically PEP 692 (Unpack) x PEP 827 (computed TypedDict).

Who is broken: the static checker. `Unpack`-kwargs validation is a static-only
feature; the runtime evaluator just computes the TypedDict and has no kwargs
contract to enforce.

The working alternative is a positional TypedDict parameter (below).

Run:
    uv run pytest tests/test_insert_input.py -v
    uv run mypy --warn-unused-ignores --show-error-codes \
                --enable-error-code ignore-without-code tests/test_insert_input.py
"""

from typing import TYPE_CHECKING, Unpack, assert_type

import pytest
from typemap.type_eval import eval_typing

from typed_sql.core import InsertInput, PrimaryKey, Table


class User(Table):
    id: PrimaryKey[int]
    email: str
    age: int | None


# ── Feature: InsertInput[T] computes the non-PK input row ───────────────────


def mypy_test_insert_input_computes_row() -> None:
    if TYPE_CHECKING:
        row: InsertInput[User] = {"email": "i3s", "age": 22}
        assert_type(row["email"], str)
        assert_type(row["age"], int | None)


@pytest.mark.xfail(
    reason=(
        "Dual-track divergence in the PK filter. The static-clean guard "
        "`IsAssignable[x.type, Column[Any, Any, PrimaryKey[Any]]]` is too "
        "permissive at runtime: typemap's IsAssignable treats the Any "
        "owner/name slots as matching EVERY column (id AND email both True), "
        "so all columns are filtered out -> empty TypedDict. The "
        "runtime-correct guard `IsAssignable[GetArg[x.type, Column, 2], "
        "PrimaryKey[Any]]` trips finding #4 (file-level GetArg errors) on the "
        "static track. No formulation is clean on both tracks yet "
        "(candidate: make Column covariant). InsertInput is STATIC-only today."
    ),
    strict=True,
)
def test_insert_input_computes_row() -> None:
    td = eval_typing(InsertInput[User])
    assert td.__annotations__ == {"email": str, "age": int | None}
    assert td.__required_keys__ == frozenset({"email", "age"})
    assert "id" not in td.__annotations__  # PrimaryKey dropped


# ── Feature: a POSITIONAL TypedDict parameter consumes it (THE WORKING WAY) ──


def mypy_test_positional_param_enforces() -> None:
    if TYPE_CHECKING:

        def insert_row[T](table: type[T], values: InsertInput[T]) -> None: ...

        insert_row(User, {"email": "i3s", "age": 22})  # ok
        insert_row(User, {"email": "i3s"})  # type: ignore[typeddict-item]
        insert_row(User, {"email": 1, "age": 22})  # type: ignore[typeddict-item]
        insert_row(User, {"id": 1, "email": "x", "age": 22})  # type: ignore[typeddict-item]


# ── Feature: PEP 692 Unpack CANNOT consume the computed TypedDict ────────────
# "Unpack item in ** parameter must be a TypedDict or a TypeVar with TypedDict
# bound" — a parameterized computed alias is neither.


def mypy_test_unpack_of_computed_typeddict_rejected() -> None:
    if TYPE_CHECKING:

        def insert_kw[T](
            table: type[T],
            **values: Unpack[InsertInput[T]],  # type: ignore[misc]
        ) -> None: ...
