"""
Forward-looking spec for typing every model_dump(**kwargs) variant.

This file is **not** currently green. It describes the *aspired* behaviour
for each Pydantic `model_dump` keyword argument under the metatypes layer.
Today, `pydantic_extension.BaseModel.model_dump` accepts `**kwargs: Any`
and always returns `ModelDump[Self]` regardless of arguments. The
implementation that makes each kwarg narrow / rename / drop keys (or
rewrite value types) is the *next* PR.

Convention — same as `test_pydantic_extension.py`:

    mypy_test_<kwarg>     — declares the aspired static return type via
                            `assert_type` inside `if TYPE_CHECKING:`.
                            Mypy sees the assertion fail today; the line
                            is annotated `# type: ignore[assert-type]`
                            so the run still passes. When the
                            implementation lands and the assertion holds,
                            `--warn-unused-ignores` will flag the ignore
                            and force us to remove it.

    test_<kwarg>          — runtime variant. Either xfailed (the kwarg
                            *could* be statically typed once the
                            implementation lands) or skipped (the kwarg
                            is opaque at the type level by nature —
                            context, fallback, etc.).

Run:
    uv run pytest tests/test_model_dump_kwargs.py -v
    uv run mypy  --warn-unused-ignores --show-error-codes \\
                 --enable-error-code ignore-without-code \\
                 tests/test_model_dump_kwargs.py
"""

from datetime import datetime
from typing import TYPE_CHECKING, NotRequired, TypedDict, assert_type

import pytest

from pydantic_extension import BaseModel, ModelDump

from tests.conftest import User


class WithDatetime(BaseModel):
    when: datetime
    label: str


class WithOptional(BaseModel):
    name: str
    nickname: str | None = None


def mypy_test_mode_json() -> None:
    if TYPE_CHECKING:
        w = WithDatetime(when=datetime.now(), label="x")
        dump = w.model_dump(mode="json")
        # Aspired: 'when' becomes str because mode='json' serializes
        # datetimes to ISO strings.
        assert_type(dump["when"], str)  # type: ignore[assert-type]


@pytest.mark.xfail(
    reason=(
        "Aspired: mode='json' should rewrite value types in ModelDump "
        "(datetime → str, UUID → str, etc.). Not yet implemented — "
        "model_dump currently returns ModelDump[Self] regardless of mode."
    ),
    strict=True,
)
def test_mode_json() -> None:
    w = WithDatetime(when=datetime.now(), label="x")
    dump = w.model_dump(mode="json")
    assert isinstance(dump["when"], str)
    # The runtime side actually does this — but the *type* won't reflect
    # it until the static layer learns about `mode='json'`. The xfail is
    # on the type-level claim we want to make, not the value.
    raise AssertionError("static return type for mode='json' not yet narrowed")


# include — narrow keys to a literal set


class _UserIncludeName(TypedDict):
    name: str


def mypy_test_include_set() -> None:
    if TYPE_CHECKING:
        u = User(name="x", age=1)
        dump = u.model_dump(include={"name"})
        # Aspired: only 'name' is in the resulting TypedDict.
        assert_type(dump, _UserIncludeName)  # type: ignore[assert-type]


@pytest.mark.xfail(
    reason=(
        "Aspired: include={'name'} narrows ModelDump's keys to {'name'}. "
        "Not yet implemented in pydantic_extension."
    ),
    strict=True,
)
def test_include_set() -> None:
    u = User(name="x", age=1)
    dump = u.model_dump(include={"name"})
    assert set(dump.keys()) == {"name"}
    raise AssertionError("static narrowing for include={…} not yet implemented")


# ──────────────────────────────────────────────────────────────────────────
# exclude — drop keys from a literal set
# ──────────────────────────────────────────────────────────────────────────


class _UserExcludeAge(TypedDict):
    name: str


def mypy_test_exclude_set() -> None:
    if TYPE_CHECKING:
        u = User(name="x", age=1)
        dump = u.model_dump(exclude={"age"})
        assert_type(dump, _UserExcludeAge)  # type: ignore[assert-type]


@pytest.mark.xfail(
    reason=(
        "Aspired: exclude={'age'} drops 'age' from ModelDump's keys. "
        "Not yet implemented in pydantic_extension."
    ),
    strict=True,
)
def test_exclude_set() -> None:
    u = User(name="x", age=1)
    dump = u.model_dump(exclude={"age"})
    assert set(dump.keys()) == {"name"}
    raise AssertionError("static narrowing for exclude={…} not yet implemented")


# ──────────────────────────────────────────────────────────────────────────
# include — nested IncEx (sub-dict drives nested narrowing)
# ──────────────────────────────────────────────────────────────────────────


class Profile(BaseModel):
    email: str
    phone: str


class WithProfile(BaseModel):
    user: Profile
    note: str


class _ProfileIncludeEmail(TypedDict):
    email: str


class _WithProfileIncludeUserEmail(TypedDict):
    user: _ProfileIncludeEmail


def mypy_test_include_nested() -> None:
    if TYPE_CHECKING:
        w = WithProfile(user=Profile(email="a@b", phone="x"), note="n")
        dump = w.model_dump(include={"user": {"email"}})
        assert_type(dump, _WithProfileIncludeUserEmail)  # type: ignore[assert-type]


@pytest.mark.xfail(
    reason=(
        "Aspired: nested IncEx include={'user': {'email'}} recursively "
        "narrows the nested model's keys. Not yet implemented."
    ),
    strict=True,
)
def test_include_nested() -> None:
    w = WithProfile(user=Profile(email="a@b", phone="x"), note="n")
    dump = w.model_dump(include={"user": {"email"}})
    assert dump == {"user": {"email": "a@b"}}
    raise AssertionError("nested IncEx narrowing not yet implemented")


# ──────────────────────────────────────────────────────────────────────────
# by_alias — rename keys to each field's alias
# ──────────────────────────────────────────────────────────────────────────


def mypy_test_by_alias() -> None:
    if TYPE_CHECKING:
        u = User(name="x", age=1)
        dump = u.model_dump(by_alias=True)
        # Aspired: when fields declare aliases, by_alias=True renames
        # the TypedDict keys to those aliases. (User has no aliases, so
        # the type is unchanged — but the *mechanism* needs implementing.)
        assert_type(dump, ModelDump[User])


@pytest.mark.xfail(
    reason=(
        "Aspired: by_alias=True rewrites ModelDump's keys to each "
        "field's declared alias. Requires field-metadata access in the "
        "type-level transform — not yet implemented."
    ),
    strict=True,
)
def test_by_alias() -> None:
    u = User(name="x", age=1)
    dump = u.model_dump(by_alias=True)
    assert dump == {"name": "x", "age": 1}
    raise AssertionError("by_alias key renaming not yet typed")


# ──────────────────────────────────────────────────────────────────────────
# exclude_unset — keys not explicitly set become NotRequired
# ──────────────────────────────────────────────────────────────────────────


class _WithOptionalUnset(TypedDict):
    name: NotRequired[str]
    nickname: NotRequired[str | None]


def mypy_test_exclude_unset() -> None:
    if TYPE_CHECKING:
        w = WithOptional(name="x")
        dump = w.model_dump(exclude_unset=True)
        assert_type(dump, _WithOptionalUnset)  # type: ignore[assert-type]


@pytest.mark.xfail(
    reason=(
        "Aspired: exclude_unset=True makes every key NotRequired in the "
        "resulting TypedDict. Not yet implemented."
    ),
    strict=True,
)
def test_exclude_unset() -> None:
    w = WithOptional(name="x")
    dump = w.model_dump(exclude_unset=True)
    assert dump == {"name": "x"}
    raise AssertionError("exclude_unset NotRequired-ification not yet typed")


# ──────────────────────────────────────────────────────────────────────────
# exclude_defaults — keys with their declared default become NotRequired
# ──────────────────────────────────────────────────────────────────────────


class _WithOptionalDefaults(TypedDict):
    name: str
    nickname: NotRequired[str | None]


def mypy_test_exclude_defaults() -> None:
    if TYPE_CHECKING:
        w = WithOptional(name="x")
        dump = w.model_dump(exclude_defaults=True)
        # nickname has a default of None, so it becomes NotRequired.
        # name has no default, so it stays Required.
        assert_type(dump, _WithOptionalDefaults)  # type: ignore[assert-type]


@pytest.mark.xfail(
    reason=(
        "Aspired: exclude_defaults=True makes fields with declared "
        "defaults NotRequired in the resulting TypedDict. Requires "
        "default-value introspection — not yet implemented."
    ),
    strict=True,
)
def test_exclude_defaults() -> None:
    w = WithOptional(name="x")
    dump = w.model_dump(exclude_defaults=True)
    assert "nickname" not in dump
    raise AssertionError("exclude_defaults NotRequired-ification not yet typed")


# ──────────────────────────────────────────────────────────────────────────
# exclude_none — Optional[T] keys become NotRequired
# ──────────────────────────────────────────────────────────────────────────


class _WithOptionalExcludeNone(TypedDict):
    name: str
    nickname: NotRequired[str | None]


def mypy_test_exclude_none() -> None:
    if TYPE_CHECKING:
        w = WithOptional(name="x")
        dump = w.model_dump(exclude_none=True)
        assert_type(dump, _WithOptionalExcludeNone)  # type: ignore[assert-type]


@pytest.mark.xfail(
    reason=(
        "Aspired: exclude_none=True makes Optional[T] keys NotRequired "
        "(since they could legitimately be omitted). Not yet implemented."
    ),
    strict=True,
)
def test_exclude_none() -> None:
    w = WithOptional(name="x")
    dump = w.model_dump(exclude_none=True)
    assert "nickname" not in dump
    raise AssertionError("exclude_none NotRequired-ification not yet typed")


# ──────────────────────────────────────────────────────────────────────────
# exclude_computed_fields — drop @computed_field keys
# ──────────────────────────────────────────────────────────────────────────

# We'd need a model with @computed_field to demonstrate this; the static
# claim is "any field declared as a computed_field disappears from the
# TypedDict when exclude_computed_fields=True". Below we set up the shape
# of the claim, but skip a concrete model — we'll add one when the
# implementation pass touches this kwarg.


def mypy_test_exclude_computed_fields() -> None:
    if TYPE_CHECKING:
        u = User(name="x", age=1)
        dump = u.model_dump(exclude_computed_fields=True)
        # User has no @computed_field, so the type is unchanged — but
        # the mechanism (filter on field.kind == 'computed') still needs
        # implementing for models that do have computed fields.
        assert_type(dump, ModelDump[User])


@pytest.mark.xfail(
    reason=(
        "Aspired: exclude_computed_fields=True drops @computed_field "
        "keys from the resulting TypedDict. Requires computed-field "
        "introspection — not yet implemented."
    ),
    strict=True,
)
def test_exclude_computed_fields() -> None:
    u = User(name="x", age=1)
    u.model_dump(exclude_computed_fields=True)
    raise AssertionError("exclude_computed_fields filter not yet typed")


# ──────────────────────────────────────────────────────────────────────────
# round_trip — internal serialization tweak
# ──────────────────────────────────────────────────────────────────────────


def mypy_test_round_trip() -> None:
    if TYPE_CHECKING:
        u = User(name="x", age=1)
        dump = u.model_dump(round_trip=True)
        # round_trip doesn't change keys; for Json[T]-style fields it may
        # affect value types. User has none, so the type is unchanged.
        assert_type(dump, ModelDump[User])


@pytest.mark.xfail(
    reason=(
        "Aspired: round_trip=True preserves keys but may rewrite value "
        "types for Json[T]-style fields. Not yet implemented."
    ),
    strict=True,
)
def test_round_trip() -> None:
    u = User(name="x", age=1)
    u.model_dump(round_trip=True)
    raise AssertionError("round_trip value-type rewrite not yet typed")


# ──────────────────────────────────────────────────────────────────────────
# Opaque kwargs — cannot be statically reflected by nature.
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.skip(
    reason=(
        "context= is an opaque user value passed through to "
        "@field_serializer hooks. Its effect on the output is arbitrary "
        "user-defined logic — cannot be statically reflected."
    )
)
def test_context() -> None: ...


@pytest.mark.skip(
    reason=(
        "fallback= is an arbitrary Callable[[Any], Any] applied to "
        "unserializable values. Its return type is opaque — cannot be "
        "statically reflected."
    )
)
def test_fallback() -> None: ...


@pytest.mark.skip(
    reason=(
        "warnings= controls runtime warning policy ('none'/'warn'/'error'). "
        "It has no effect on the returned dict or its type."
    )
)
def test_warnings() -> None: ...


@pytest.mark.skip(
    reason=(
        "serialize_as_any=True switches to duck-typing on runtime values, "
        "deliberately bypassing the declared field types. Defeats static "
        "narrowing by design — cannot be reflected."
    )
)
def test_serialize_as_any() -> None: ...


@pytest.mark.skip(
    reason=(
        "polymorphic_serialization=True dispatches on the runtime type of "
        "each nested model. Depends on runtime values — cannot be "
        "statically reflected."
    )
)
def test_polymorphic_serialization() -> None: ...
