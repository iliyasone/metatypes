"""GOAL spec for INSERT — type-only statements; `id` optional (SQLite semantics).

This file describes the TARGET API. It is EXPECTED TO FAIL until core implements
it — deliberately NOT marked xfail. A failing assertion here = a goal not yet met.

Conventions:
 * Statement shape lives entirely in the TYPE: `Insert[User]`, `Insert[User, Many]`,
   `Insert[User, Returning[Literal["id"]]]`, ... — never methods on `sql`.
 * `stmt = sql(Insert[User])`; `run(stmt(email=..., age=...))` / `render(...)`.
 * Static negatives use `# type: ignore[code]`: when the goal is met the error
   fires and the ignore is "used"; until then `--warn-unused-ignores` flags the
   unused ignore — that IS the signal the enforcement is missing.

Run:
    uv run mypy --warn-unused-ignores --show-error-codes \
                --enable-error-code ignore-without-code tests/test_insert.py
    uv run pytest tests/test_insert.py -v
"""

from typing import TYPE_CHECKING, Literal, assert_type

from typed_sql.core import (
    All,
    Default,
    Insert,
    Many,
    OrIgnore,
    PrimaryKey,
    Returning,
    Table,
    render,
    run,
    sql,
)


class User(Table):
    id: PrimaryKey[int]
    email: str
    age: int | None


# ── single row: id optional, age nullable, run() -> None (no RETURNING) ──────


def mypy_test_insert_single_row() -> None:
    if TYPE_CHECKING:
        stmt = sql(Insert[User])
        assert_type(run(stmt(email="a@b.c", age=22)), None)  # id omitted -> auto
        assert_type(run(stmt(id=10, email="a@b.c", age=22)), None)  # id optional, given
        run(stmt(email="a@b.c", age=None))  # age nullable


def mypy_test_insert_rejects_bad_rows() -> None:
    if TYPE_CHECKING:
        stmt = sql(Insert[User])
        stmt(email="a@b.c")  # type: ignore[call-arg]  # missing required 'age'
        stmt(email=123, age=22)  # type: ignore[arg-type]  # 'email' wants str
        stmt(email="a@b.c", age=22, nope=1)  # type: ignore[call-arg]  # unknown column
        stmt(email=None, age=22)  # type: ignore[arg-type]  # 'email' is NOT NULL


# ── RETURNING flips run()'s result from None to a typed row ──────────────────


def mypy_test_insert_returning_id() -> None:
    if TYPE_CHECKING:
        rows = run(sql(Insert[User, Returning[Literal["id"]]])(email="a@b.c", age=22))
        assert_type(rows[0]["id"], int)


def mypy_test_insert_returning_all() -> None:
    if TYPE_CHECKING:
        rows = run(sql(Insert[User, Returning[All]])(email="a@b.c", age=22))
        assert_type(rows[0]["email"], str)
        assert_type(rows[0]["age"], int | None)


# ── multiplicity / defaults / conflict are TYPES, not methods ────────────────


def mypy_test_insert_many() -> None:
    if TYPE_CHECKING:
        stmt = sql(Insert[User, Many])
        run(stmt([{"email": "a@b.c", "age": 22}, {"email": "d@e.f", "age": 30}]))


def mypy_test_insert_default_values_invalid_for_user() -> None:
    if TYPE_CHECKING:
        # DEFAULT VALUES is invalid here: 'email' is NOT NULL with no default.
        sql(Insert[User, Default])()  # type: ignore[misc]


def mypy_test_insert_or_ignore() -> None:
    if TYPE_CHECKING:
        run(sql(Insert[User, OrIgnore])(email="a@b.c", age=22))


# ── runtime: render emits named-parameter SQL ───────────────────────────────


def test_insert_render_named_params() -> None:
    text = render(sql(Insert[User])(email="a@b.c", age=22))
    assert text == "INSERT INTO User (email, age) VALUES (:email, :age)"
