# https://github.com/CarliJoy/intersection_examples/blob/main/legacy_examples/typed_dict.py
from typing import TypedDict
from metatypes import Intersection


class Movie(TypedDict):
    name: str
    year: int


class BookBased(TypedDict):
    based_on: str


def foobar() -> Intersection[Movie, BookBased]:
    return {
        "name": "Name",
        "year": 123,
        "based_on": "Movie",
    }
