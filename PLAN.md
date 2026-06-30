# Well-Typed PostgreSQL in Python: The Limits of PEP 827's Type Manipulation

- START: Python type system is not expressive enough, yet powerful
- PROOF lacking feature
- COMPARE the feature in other languages (rust / typescript)
-- code-gen at compile time (PrismaORM, sqlx)
-- true type-manipulations

- EXPLAIN the history of Python Types
- SHOW the complications: 3 type systems (is it even needed)

## Methodology    
- Type manipulation is native for Python
- STATICLY INFERING TYPES IS NEW
- Runtime types vs Static time types
- THAT IS WHY: testing setup: compare run-time and static-time

## Theoretical results
- problems of ORM
- examples of the subset POSTgres which are typed
- examples of errors handled
- examples of nested relation/lazy loadings, where the traditional ORM is not being able to deduct the type, but our tysql is.

- examples of what can't be typed: dynamic SQL (strings inside postgreSQL) 
- examples of what can't be typed: dynamic SQL (repeated column names)
- 
## Result
- tysql use without the PEP accpetance, tools-only (or mypy with plugin)
- maybe `tysql` as a cli tool which would generate types if you don't have a plugin. maybe added to any project since Python 3.14 (or even 3.12/3.11 not sure)
-  tysql is ready to use in any project today.

## Discussion and debates
- why some people hate types in PEP 827
- what neeed to be done to accept PEP 827