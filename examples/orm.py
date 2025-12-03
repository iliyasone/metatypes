# type: ignore
from metatypes import Intersection, Row, Select, Join


class Table: ...


class User(Table):
    id: int
    email: str


class Post(Table):
    id: int
    title: str
    published: bool
    author_id: int


rows = select(
    Join[User, Post].on(User.id == Post.author_id),
    where=Post.published == True,
    columns=[User.email, Post.title],
)

# WIP....
