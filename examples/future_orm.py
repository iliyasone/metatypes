from typing import LiteralString, Self, overload, Any, reveal_type

type Name[T] = ...
"""
Type-level name of a T class. Return LiteralString. 
Equivivalent to runtime T.__name__ 
"""

class ConditionalOn[T]: ...


class ModelAttr[Attr: LiteralString, T]:
    def __eq__(self, v: object) -> ConditionalOn[T]:  # pyright: ignore[reportIncompatibleMethodOverride]
        ...


class Mapped[T]:
    @overload
    def __get__(self, instance: None, owner: Any) -> ModelAttr[Name[Self], T]: ...

    @overload
    def __get__(self, instance: object, owner: Any) -> T: ...

    def __get__(self, instance: Any, owner: Any) -> T | ModelAttr[LiteralString, T]: ...


class BaseTable: ...


# Example


class Table(BaseTable): ...


class User(Table):
    id: Mapped[int]
    email: Mapped[str]


class Post(Table):
    user: Mapped[User]
    title: Mapped[str]
    published: Mapped[bool]
    author_id: Mapped[int]


user = User()
reveal_type(User.id == 1)
reveal_type(user.id)


