# Well-Typed PostgreSQL in Python: The Limits of PEP 827's Type Manipulation

Python's static type system cannot express types produced by metaprogramming, yet dynamically manipulating classes has been a native feature of the language since day one.

PEP 827 (*Type Manipulation*, Draft, targeting Python 3.16) proposes type manipulation facilities to close this gap, but whether they are sufficient in practice was unknown. This thesis answers that question empirically by building **tysql**, a PostgreSQL query builder whose result types are statically inferred from the queries themselves — a capability previously unattainable in Python. On a defined query subset the inferred types are verified against a live PostgreSQL server as an external oracle, and the limits beyond that subset are mapped precisely.

tysql is usable today:

- it statically infers the result type of every supported SQL statement and rejects ill-typed statements with a type error, using the type operators of PEP 827;
- because released type checkers do not support PEP 827 yet, it ships a CLI validator that reports errors in the same places any checker will once PEP 827 lands.

The project is open source: the code lives at <https://github.com/iliyasone/tysql>, the package is published on PyPI as [`tysql`](https://pypi.org/project/tysql/), and the examples of this thesis can be tried in the browser at <https://tysql.vercel.app>.