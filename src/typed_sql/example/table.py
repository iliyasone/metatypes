from typing import Literal

from typed_sql.core import Insert, PrimaryKey, Table, ForeignKey, sql


class User(Table):
    id: PrimaryKey[int]
    email: str
    age: int | None


class Post(Table):
    id: PrimaryKey[int]
    author: ForeignKey[User, Literal["id"]]
    text: str


class Comment(Table):
    id: PrimaryKey[int]
    author: ForeignKey[User, Literal["id"]]
    post: ForeignKey[Post, Literal["id"]]
    text: str


sql(Insert[User], email="iliyas.dzabbarov@gmail.com", age=22)
sql(Insert[User], id=10, email="iliyas.dzabbarov@gmail.com", age=22)
