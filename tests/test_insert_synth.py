"""Synthesizing the kwargs signature (PEP 827 callable synthesis) — the working
stand-in for `Unpack[computed-TypedDict]`.

PEP 692 defines `**kwargs: Unpack[TD]` as sugar for explicit keyword params
`(*, k1: t1, ...)`. Here we *construct* those params directly from the schema with
`Params[Param[name, type, "keyword"], ...]`. It works where `Unpack[InsertInput[T]]`
does not, because it lives in RETURN position (construction), not in a parameter
spec (consumption).

VERIFIED by an 8-angle adversarial sweep. STATICALLY it enforces exactly like
`Unpack` / explicit params — required keys, value types, PK dropped, extra keys
rejected, keyword-only — and `reveal_type` confirms the real signature
`def (*, email: str, age: int | None) -> InsertStmt` (non-vacuous).

Two caveats, both encoded below:
 * FK columns synthesize with the `ForeignKey[...]` type, not the storage `int`
   (FK value-type resolution is a separate step).
 * Runtime divergence: `eval_typing(InsertFn[User])` collapses to empty params.
   Same root cause as InsertInput — the Any-laden PK guard
   `IsAssignable[col, Column[Any, Any, SerialPrimaryKey[Any]]]` matches EVERY column at
   runtime. Synthesis is a STATIC contract (enforcement happens in the checker).

Run:
    uv run mypy --warn-unused-ignores --show-error-codes \
                --enable-error-code ignore-without-code tests/test_insert_synth.py
    uv run pytest tests/test_insert_synth.py -v
"""

from typing import TYPE_CHECKING, Any, Callable, Literal, TypedDict, Unpack

import pytest
import typemap_extensions as t
from typemap.type_eval import eval_typing

from typed_sql.core import Column, ForeignKey, SerialPrimaryKey, Statement, Table


class User(Table):
    id: SerialPrimaryKey[int]
    email: str
    age: int | None


class Post(Table):
    id: SerialPrimaryKey[int]
    author: ForeignKey[User, Literal["id"]]


class InsertStmt(Statement):
    pass


# The synthesized signature: one keyword param per non-PK column.
type InsertFn[T] = Callable[
    t.Params[
        *[
            t.Param[x.name, t.GetArg[x.type, Column, Literal[2]], Literal["keyword"]]
            for x in t.Iter[t.Attrs[T]]
            if not t.IsAssignable[x.type, Column[Any, Any, SerialPrimaryKey[Any]]]
        ]
    ],
    InsertStmt,
]


def Insert[T](table: type[T]) -> InsertFn[T]:
    raise NotImplementedError


# ── Feature: the synthesized signature enforces the kwargs ───────────────────


def mypy_test_synth_enforces_kwargs() -> None:
    if TYPE_CHECKING:
        Insert(User)(email="i3s", age=22)  # ok
        Insert(User)(email="i3s")  # type: ignore[call-arg]  # missing age
        Insert(User)(email=123, age=22)  # type: ignore[arg-type]  # wrong type
        Insert(User)(id=1, email="x", age=22)  # type: ignore[call-arg]  # extra PK key
        Insert(User)("x", 22)  # type: ignore[misc]  # keyword-only: no positional


# ── Feature: it is the SAME thing Unpack[TypedDict]/explicit params produce ──


def mypy_test_synth_equivalent_to_unpack() -> None:
    if TYPE_CHECKING:

        class HandRow(TypedDict):
            email: str
            age: int | None

        def hand_unpack(**kwargs: Unpack[HandRow]) -> None: ...
        def hand_explicit(*, email: str, age: int | None) -> None: ...

        # good calls — all three accept
        Insert(User)(email="x", age=22)
        hand_unpack(email="x", age=22)
        hand_explicit(email="x", age=22)

        # bad calls — all three reject identically with [call-arg]
        Insert(User)(email="x")  # type: ignore[call-arg]
        hand_unpack(email="x")  # type: ignore[call-arg]
        hand_explicit(email="x")  # type: ignore[call-arg]


# ── Caveat 1: an FK column synthesizes as ForeignKey[...], not its storage int ──


def mypy_test_synth_fk_column_unresolved() -> None:
    if TYPE_CHECKING:
        # 'author' is typed ForeignKey[User, "id"], so an int is rejected;
        # FK -> storage-type (int) resolution is not done here.
        Insert(Post)(author=1)  # type: ignore[arg-type]


# ── Caveat 2: runtime divergence — the synthesis is STATIC-only ──────────────


@pytest.mark.xfail(
    reason=(
        "Runtime divergence (same root cause as InsertInput). Statically the "
        "synthesized signature is (*, email: str, age: int | None), but "
        "eval_typing(InsertFn[User]) collapses to Callable[Params[()], ...] — "
        "the Any-laden PK guard IsAssignable[col, Column[Any, Any, "
        "SerialPrimaryKey[Any]]] returns True for EVERY column at runtime, so all are "
        "filtered out. Enforcement is static; the runtime evaluator drops all "
        "params. Fix candidate: make Column covariant / a slot-2 guard."
    ),
    strict=True,
)
def test_synth_signature_has_params_at_runtime() -> None:
    ev = eval_typing(InsertFn[User])
    assert "email" in repr(ev), f"runtime synthesis collapsed to empty params: {ev!r}"
