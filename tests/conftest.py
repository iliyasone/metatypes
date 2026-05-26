"""Shared model fixtures for the pydantic_extension test suite.

Defined at module scope (not as pytest fixtures) so they're importable from
both `test_pydantic_extension.py` and `test_model_dump_kwargs.py`.
"""

from pydantic_extension import BaseModel


class User(BaseModel):
    name: str
    age: int


class Admin(User):
    role: str


class Empty(BaseModel):
    pass
