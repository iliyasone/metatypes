# A Meta-Type System for Python: An Expressive Library for Static Typing

Python's static type system cannot express types produced by metaprogramming, yet dynamically manipulating classes has been a native feature since day one.

PEP 827 proposes new type manipulation facilities to fill this gap, but whether they are sufficient for all cases remains unknown. This thesis has addressed that question by developing tysql, a PostgreSQL query builder whose result types can be statically inferred — a capability previously unattainable in Python. The tool is available now: `pip install tysql`.

tysql is usable today:

- It statically infers the result type of every SQL statement and rejects ill-typed statements with a type error, using the type operators from PEP 827.
- It capable of inserting type hints into existing code to infer result types of SQL statements in a pre-PEP 827 world, and it and ships a CLI validator that raises errors in the same places any type checker would once PEP 827 lands.
