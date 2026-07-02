from typing import Literal

from typed_sql.core import ForeignKey, SerialPrimaryKey, Table


class User(Table):
    id: SerialPrimaryKey[int]
    email: str
    age: int | None


class Post(Table):
    id: SerialPrimaryKey[int]
    author: ForeignKey[User, Literal["id"]]
    text: str


class Comment(Table):
    id: SerialPrimaryKey[int]
    author: ForeignKey[User, Literal["id"]]
    post: ForeignKey[Post, Literal["id"]]
    text: str

