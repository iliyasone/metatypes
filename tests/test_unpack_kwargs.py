"""PEP 827 "Unpack of TypeVars for kwargs" — does it let us enforce the INSERT
row as kwargs?

Definitive answer (all on the STATIC track; `Unpack`-kwargs is a static-only
feature, so the runtime evaluator is not the party that can be "broken"):

* `Unpack[K]` where K is a TypeVar bound to a TypedDict WORKS — but it *infers*
  K *from* the caller's kwargs (captures whatever is passed). PEP 827 §"Unpack of
  TypeVars for kwargs": `def f[K: BaseTypedDict](**kwargs: Unpack[K]) -> K`.
* That is the OPPOSITE of what INSERT needs: we must *constrain* kwargs to a
  *pre-computed* schema (`InsertInput[T]`), not infer K from them.
* Constraining via the bound — `K: InsertInput[T]` — FAILS: a bound can't
  reference the earlier type param ("T is not defined"), and a computed bound
  isn't a recognized "TypeVar with TypedDict bound".
* The capture-then-validate rescue (infer K, branch on `IsAssignable[K,
  InsertInput[T]]` in the return type) is not expressible: there is no `If`
  combinator (only IsAssignable / IsEquivalent / RaiseError exist).

Conclusion: `Unpack` cannot enforce a computed schema (it captures, not
constrains). The kwargs spelling that DOES enforce is callable synthesis —
`Insert(User)(email=..., age=22)` via `Params`/`Param[name, T, "keyword"]`, which
mypy checks with native field-level errors (to be added as a test once the final
API spelling is chosen).

Run:
    uv run mypy --warn-unused-ignores --show-error-codes \
                --enable-error-code ignore-without-code tests/test_unpack_kwargs.py
"""

from typing import TYPE_CHECKING, TypedDict, Unpack, assert_type

from typed_sql.core import Insert, InsertInput, PrimaryKey, Table


class User(Table):
    id: PrimaryKey[int]
    email: str
    age: int | None


class BaseTypedDict(TypedDict):
    pass


# ── PEP 827 basic form WORKS: Unpack[K] infers K from the kwargs ─────────────


def mypy_test_pep_unpack_typevar_infers() -> None:
    if TYPE_CHECKING:

        def capture[K: BaseTypedDict](**kwargs: Unpack[K]) -> K:
            return kwargs

        x: int = 1
        ys: list[str] = ["a"]
        r = capture(x=x, ys=ys)
        assert_type(r["x"], int)
        assert_type(r["ys"], list[str])


# ── But the schema-enforcing form does NOT exist ────────────────────────────
# K bound to the COMPUTED InsertInput[T]: the bound can't reference T, and the
# computed bound is not a recognized TypedDict bound for Unpack.


def mypy_test_unpack_computed_bound_unsupported() -> None:
    if TYPE_CHECKING:

        def insert_kw[T, K: InsertInput[T]](  # type: ignore[name-defined]
            stmt: type[Insert[T]],
            **kwargs: Unpack[K],  # type: ignore[misc]
        ) -> None: ...
