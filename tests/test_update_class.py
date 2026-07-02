from typing import TYPE_CHECKING, Any, Literal, Never, assert_type, reveal_type

import typemap_extensions as typing
from typemap.type_eval import eval_typing, eval_call


class CustomField[T]:
    pass


class WrapFields:
    def __init_subclass__[T](
        cls: type[T],
    ) -> typing.UpdateClass[
        *[
            typing.Member[x.name, CustomField[x.type]]
            for x in typing.Iter[typing.Attrs[T]]
        ]
    ]:
        return None  # type: ignore[return-value]


class Point(WrapFields):
    x: int
    y: CustomField[int]


class RegularPoint:
    x: int


type IsCustomField[C, N] = (
    typing.Bool[Literal[True]]
    if typing.IsAssignable[typing.GetMemberType[C, N], CustomField[Any]]
    else typing.RaiseError[Literal["Field is not a CustomField!"]]
)


def test_updated_class_ok():
    assert eval_typing(IsCustomField[Point, Literal["x"]]) == Literal[True]


def mypy_test_before_class_update() -> None:
    if TYPE_CHECKING:
        foo: IsCustomField[Point, Literal["y"]]
        assert_type(foo, Literal[True])
        # not fails because `Point.y` was a Custom field before transformation


def mypy_test_local_scope() -> None:
    type XL = IsCustomField[Point, Literal["x"]]
    xl: XL
    assert_type(xl, Literal[True])  # TODAY: fails — Never; goal state: passes


def mypy_test() -> None:
    if TYPE_CHECKING:
        # Point.x `int` was transformed to `CustomField[int]`, mypy agrees
        assert_type(Point.x, CustomField[int])

        # But inside type manipulators, mypy still evaluate errors are
        # over the before update class schema
        foo: IsCustomField[Point, Literal["x"]]  # error: Field is not a CustomField!

        # And at the same time, the result type is evaluated correctly
        assert_type(foo, Literal[True])  # no fail, as expected.
