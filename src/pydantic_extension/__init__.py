from typing import Any, Literal, Self, cast

import typemap_extensions as typing
from pydantic import BaseModel as _BaseModel


type ModelDump[T] = typing.NewTypedDict[
    *[
        typing.Member[field.name, field.type]
        for field in typing.Iter[typing.Attrs[T]]
        if typing.IsAssignable[field.definer, _BaseModel]
        and not typing.IsEquivalent[field.definer, _BaseModel]
        and not typing.IsEquivalent[
            typing.Slice[field.name, Literal[0], Literal[2]], Literal["__"]
        ]
    ]
]


class BaseModel(_BaseModel):
    def model_dump(self, **kwargs: Any) -> ModelDump[Self]:  # type: ignore[override]
        return cast(ModelDump[Self], super().model_dump(**kwargs))
