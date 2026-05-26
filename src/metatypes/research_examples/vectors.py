# type: ignore
from typing import Callable, Literal, TYPE_CHECKING
from metatypes import Add, AnyNat, Mul, Len, Equals, reveal_type


class Vector[Typ, N: AnyNat]:
    """Vector of length N with elements of type Typ."""


def repeat[Typ, N: AnyNat](
    x: Typ,
    n: Literal[N],
) -> Vector[Typ, N]:
    """Create a vector with N copies of x."""


def concat[T, N: AnyNat, M: AnyNat](
    u: Vector[T, N],
    v: Vector[T, M],
) -> Vector[T, Add[N, M]]: ...


def take[Typ, N: AnyNat, M: AnyNat](
    v: Vector[Typ, Add[N, M]],
    n: Literal[N],
) -> Vector[Typ, N]:
    """Take the first N elements from a vector of length N+M."""


def drop[Typ, N: AnyNat, M: AnyNat](
    v: Vector[Typ, Add[N, M]],
    n: Literal[N],
) -> Vector[Typ, M]:
    """Drop the first N elements from a vector of length N+M."""


def is_empty[Typ, N: AnyNat](
    v: Vector[Typ, N],
) -> Equals[N, Literal[0]]:
    """Returns a type-level proof if the vector is empty."""


def transpose[Typ, N: AnyNat, M: AnyNat](
    m: Vector[Vector[Typ, M], N],
) -> Vector[Vector[Typ, N], M]:
    """Transpose a NxM matrix."""


def zip_with[Typ1, Typ2, RTyp, N: AnyNat](
    f: Callable[[Typ1, Typ2], RTyp],
    a: Vector[Typ1, N],
    b: Vector[Typ2, N],
) -> Vector[RTyp, N]:
    """Zip two vectors of the same length."""


def flatten[Typ, N: AnyNat, M: AnyNat](
    m: Vector[Vector[Typ, M], N],
) -> Vector[Typ, Mul[N, M]]:
    """Flatten a NxM matrix into a vector of length N*M."""


def dot[Typ, N: AnyNat](
    a: Vector[Typ, N],
    b: Vector[Typ, N],
) -> Typ:
    """Dot product of two vectors of length N."""


def matmul[Typ, N: AnyNat, K: AnyNat, M: AnyNat](
    a: Vector[Vector[Typ, K], N],
    b: Vector[Vector[Typ, M], K],
) -> Vector[Vector[Typ, M], N]:
    """Matrix multiplication: (N x K) * (K x M) = (N x M)"""


def examples() -> None:
    if TYPE_CHECKING:
        v: Vector[int, 4] = Vector(...)
        w: Vector[int, 5] = Vector(...)
        vw = concat(v, w)
        reveal_type(Len[vw])  # E: Revealed type is `9`

        v2: Vector[str, 0] = Vector(...)
        reveal_type(is_empty(v2))  # E: Equals[0, 0] (True)

        mat: Vector[Vector[float, 3], 2] = Vector(...)
        reveal_type(flatten(mat))  # E: Vector[float, 6]

        s: Literal["metatype"] = "metatype"
        reveal_type(Len[s])  # E: `8``

        v3: Vector[Literal["x"], 3] = Vector(...)
        reveal_type(repeat("x", 3))  # E: Vector[Literal["x"], 3]

        taken = take(vw, 2)
        reveal_type(taken)  # E: Vector[int, 2]

        dropen = drop(vw, 2)
        reveal_type(dropen)  # E: Vector[int, 7]

        mat_a: Vector[Vector[float, 2], 3] = Vector(...)  # 3x2
        mat_b: Vector[Vector[float, 4], 2] = Vector(...)  # 2x4
        mat_c = matmul(mat_a, mat_b)  # (3x2) * (2x4) = (3x4)
        reveal_type(mat_c)  # E: Vector[Vector[float, 4], 3]
