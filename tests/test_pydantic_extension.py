"""

mypy_test_<feature>   — checked by mypy extension implementing PEP 827.
                        Body lives inside `if TYPE_CHECKING:` so it
                        never executes at runtime. The `mypy_` prefix
                        means pytest does NOT collect it.

test_<feature>        — checked by pytest at runtime using typemap runtime.
                        Uses typemap.type_eval.eval_typing /
                        eval_call_with_types plus direct introspection
                        on the resulting TypedDict / dict subclass.

Run:
    uv run pytest tests/test_pydantic_extension.py -v
    uv run mypy  --warn-unused-ignores --show-error-codes \\
                 --enable-error-code ignore-without-code \\
                 tests/test_pydantic_extension.py
"""

from typing import TYPE_CHECKING, assert_type, Mapping, is_typeddict
import pytest

from pydantic_extension import BaseModel, ModelDump
from typemap.type_eval import eval_call_with_types, eval_typing

from tests.conftest import Admin, Empty, User


def mypy_test_leaf_dump_fields() -> None:
    if TYPE_CHECKING:
        u = User(name="i3s", age=22)
        dump = u.model_dump()
        assert_type(dump["name"], str)
        assert_type(dump["age"], int)


def test_leaf_dump_fields() -> None:
    td = eval_typing(ModelDump[User])
    assert td.__annotations__["name"] is str
    assert td.__annotations__["age"] is int


# ── Feature: model_dump() returns a dict subclass ───────────────────────────


def mypy_test_model_dump_returns_modeldump() -> None:
    if TYPE_CHECKING:
        u = User(name="i3s", age=22)

        # TypedDict is not dict according to the PEP 589
        assert_type(u.model_dump(), dict)  # type: ignore[assert-type]

        # The only allowed upcasting
        # the closest static analogue to "the result is dict-like".
        m: Mapping[str, object] = u.model_dump()  # noqa: F841


def test_model_dump_returns_dict_subclass() -> None:
    dump_type = eval_typing(ModelDump[User])
    assert is_typeddict(dump_type)
    assert issubclass(dump_type, dict)


# ── Feature: bound-method Self resolution (separate concern) ────────────────
# The eval_call_with_types path goes through Self binding on the bound
# method's return annotation. That path is currently broken in typemap —
# but this is a typemap limitation, not a defect of the ModelDump design.
# We keep this xfail to surface the limitation; remove the mark when the
# upstream Self-binding fix lands.


@pytest.mark.xfail(
    reason=(
        "typemap's eval_call_with_types does not yet substitute Self with "
        "the bound class when resolving a bound method's return "
        "annotation. The class-level form eval_typing(ModelDump[User]) "
        "works fine. AttributeError: __dict__ on typing.Self."
    ),
    strict=True,
    raises=AttributeError,
)
def test_eval_call_with_types_resolves_self() -> None:
    cls = eval_call_with_types(User.model_dump, User)
    assert issubclass(cls, dict)


# ── Feature: inherited fields show up in the dump ───────────────────────────


def mypy_test_inherited_fields_in_dump() -> None:
    if TYPE_CHECKING:
        a = Admin(name="i3s", age=23, role="root")
        a_dump = a.model_dump()
        assert_type(a_dump["name"], str)
        assert_type(a_dump["age"], int)
        assert_type(a_dump["role"], str)


def test_inherited_fields_in_dump() -> None:
    # Class-level form eval_typing(ModelDump[Admin]) works — Admin
    # substitutes for the type parameter T directly, no Self resolution
    # needed. Inherited fields from User come through correctly.
    td = eval_typing(ModelDump[Admin])
    assert td.__annotations__["role"] is str
    assert td.__annotations__["name"] is str
    assert td.__annotations__["age"] is int


# ── Feature: an empty model has no user-facing keys ─────────────────────────


def mypy_test_empty_model_has_no_keys() -> None:
    if TYPE_CHECKING:
        e_dump = Empty().model_dump()
        e_dump["name"]  # type: ignore[misc]


def test_empty_model_has_no_keys() -> None:
    td = eval_typing(ModelDump[Empty])
    assert td.__annotations__ == {}


def mypy_test_unknown_and_mistyped_keys_rejected() -> None:
    if TYPE_CHECKING:
        u = User(name="i3s", age=22)
        dump = u.model_dump()
        dump["ids"]  # type: ignore[misc]
        _: int = dump["name"]  # type: ignore[assignment]


def test_unknown_and_mistyped_keys_rejected() -> None:
    dump_type = eval_typing(ModelDump[User])
    # {"name": str, "age": int}
    assert "ids" not in dump_type.__annotations__
    assert dump_type.__annotations__["name"] is str


# ── Feature: Pydantic internals are filtered out of the dump ────────────────


def mypy_test_pydantic_internals_filtered() -> None:
    if TYPE_CHECKING:
        u = User(name="i3s", age=22)
        dump = u.model_dump()
        dump["__pydantic_fields__"]  # type: ignore[misc]
        dump["__pydantic_extra__"]  # type: ignore[misc]
        dump["__dict__"]  # type: ignore[misc]
        dump["model_config"]  # type: ignore[misc]


def test_pydantic_internals_filtered() -> None:
    dump_type = eval_typing(ModelDump[User])
    assert "__pydantic_fields__" not in dump_type.__annotations__
    assert "__pydantic_extra__" not in dump_type.__annotations__
    assert "__dict__" not in dump_type.__annotations__
    assert "model_config" not in dump_type.__annotations__


# ── Feature: TYPE_CHECKING-only definitions ─────────────────────────────────
# A class defined under `if TYPE_CHECKING:` at module scope is visible to
# mypy but does NOT exist at runtime. The mypy_test_ side demonstrates the
# static visibility; the test_ side demonstrates the runtime invisibility
# by looking up the name in the module globals and finding it absent.

if TYPE_CHECKING:

    class HiddenAtRuntime(BaseModel):
        secret: str


def mypy_test_type_checking_only_class_visible_to_mypy() -> None:
    if TYPE_CHECKING:
        h = HiddenAtRuntime(secret="x")
        assert_type(h.model_dump()["secret"], str)


@pytest.mark.xfail(
    reason=(
        "Runtime cannot see definitions inside `if TYPE_CHECKING:` blocks "
        "— by language design. We mark this xfail (not skip) because it "
        "documents a real limitation we want surfaced in the pytest "
        "report, and we'd flip it the moment the static layer gains a way "
        "to forward TYPE_CHECKING-only definitions to the runtime "
        "evaluator (e.g. via stub injection)."
    ),
    strict=True,
)
def test_type_checking_only_class_visible_to_runtime() -> None:
    # HiddenAtRuntime is defined above under `if TYPE_CHECKING:` — so
    # it's bound only in the static phase, not in the module globals at
    # runtime. We want to feed it to eval_typing(ModelDump[…]), but we
    # cannot, because the name does not resolve.
    assert "HiddenAtRuntime" in globals(), (
        "TYPE_CHECKING-only class was not promoted to the runtime module"
    )
