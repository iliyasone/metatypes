## 3. Design and Methodology

### 3.1 System design.

Since the PEP 827 type manipulation was published, the main thesis work was shifted from creating and testing own DSL to evaluating published PEP, trying to run some runtime checks, search it weaknesses, bugs, suggest fixes, and get it work not on toy examples, rather on real production libraries.

The authors of a PEP 827 provided 2 ways to play with their suggested DSL.

First is Typemap runtime repo (link). This is pure runtime library. It is working on the annotations, which in Python exist in runtime.

You may think it is not very useful to have type evaluator dynamically, when the whole goal of the PEP 827, as well as a Metatypes type system research, is to give users and programmers static analyze tools. You are mostly right. In Python type annotations are first class citizens, and, real classes*. They can be dynamically investigated, updated, dispatched. The classic example for this is dependency injection in FastAPI

… well-known dependency injection…

or dynamicly dispatched overloads:

```python
type Json = dict[str, Json] | list[Json] | str | bool | float | int | None

@magic_dispatch.based_on_argument_type
def parseJson(node: Node):
    ...
@magic_dispatch.based_on_argument_type    
def enter_leaft(node: Leaf):
    ...
    
@magic_dispatch.based_on_argument_type
def enter_number(node: Number)
	...
# not the great example to be honest
```

Lets go deeper into the PEP 827 example. Using suggested primitives, it is allowing to manipulate types to create a static API of create, get and update of any Pydantic model.


The famous [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/#heroupdate-the-data-model-to-update-a-hero), demonstrates how you need 3 classes for basic Create Get and Update API operations. Pydantic and types are essential for FastAPI as it is allows many tools (automatically generate documentation, validate request and response body, generate errors etc.)

```python
class HeroBase(SQLModel):
    name: str = Field(index=True)
    age: int | None = Field(default=None, index=True)

class Hero(HeroBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    secret_name: str

class HeroPublic(HeroBase):
    id: int

class HeroCreate(HeroBase):
    secret_name: str

class HeroUpdate(HeroBase):
    name: str | None = None
    age: int | None = None
    secret_name: str | None = None
```

I would argue this is not Pythonic. The Get Create and Update are just boilplate operations over class. It is whole other discussion, should they be one class, uniting the create-update and read logic under one name space. I would argue yes, some may argue no, as the per-class operation probably would more easy would extended, if tommorrow HeroUpdate would require some very complex verification before applying new secret_name. Anyway, this is not a point of today discussion. The point is that this classes absolutelty can be generated in Python today during runtime

```python
class Hero:
    id: int | None = Field(default=None, primary_key=True)

    name: str = Field(index=True)
    age: int | None = Field(default=None, index=True)

    secret_name: str = Field(hidden=True)

```

For example, something like this is plausable in Python today, and was a long time:

```python
HeroPublic = public_model(Hero)
HeroUpdate = update_model(Hero)
HeroCreate = create_model(Hero)
```
The pros of such approach:
:green-flag: all pros of a typed schema, dynamically generated docs, less boilplate code

The cons of such approach:
:red-critical: broken static analysis. Language server is not supports your code. You may made a typo and you never know until the code is crushing in production.

The point is it would be great to take from both worlds?


### 3.2 Assumptions.
The beautify of a Type Manipulation primitives is that they define roles and action. This is almost like a convention.

And we are very slowly going to the Second part of a provided playground of PEP 827 proposal: mypy plugin. This is the piece which is merging the dynamic nature of Python runtime creation with making it statically checkable. 

mypy pluging has nothing to do with runtime. It is just a tool for linting and static checks. The mypy has a long story of a plugins, which would support some advanced typing for some libraries. And now the PEP 827 plugin is a last plugin which mypy would need (probably). All other probably can be express into the PEP 827 primitives.

So we got exactly second side which was missing: static analysis.

While mypy is not the fastest plugin, also it is not providing the language server support (which is also a big thing for modern developers), it is not only good proof of a concept, but actually can be used within real project which may benefit. 

Let me clear this out:
- typemap runtime provide all tools for evaluating types in runtime
- mypy plugin is a working tool for a static analysis
- PEP 827 does not require syntax update. 

All of this 3 allow us actually to use the typemap types even without the PEP 827 acceptance in language. 
Any library or project can use this DSL right now and plugin, and hence increase chances of accepting it into the Python 3.16. Sure, the users without mypy plagin will not get advanced type system checks, but within it they will! And runtime evaluator is just a dependency.

Those combo is allowing advanced type manipulation starting from today.

### 3.3 Problems and simplifications.


#### 3.3.1 Duality of Python Annotations: Static vs Runtime

The main problem which I was running to is a **actual difference** between the static annotations and runtime annotations. This is a moment when Python haters can start clapping.

The `typing.TYPE_CHECKING` is a constant which is `False` in runtime, but `True` during static analysis.
It was introduced to the language by the BDFL at 2016 
https://github.com/python/typing/issues/230

Firstly it was suppose to handle simple issues:
- lazy imports for the heavy libraries
- annotations of self or not declared classes

Example



```python
type Json = dict[str, Json] | list[Json] | str | bool | float | int | None
# I really fucking love this example and wanna put it somewhere on top or something, at the begging as a quick demo with maybe some code example with pattern matching. Maybe comparing 2 languages.
```

... something else there?????????? About the actual usefullness of the typing.TYPE_CHECKING

#### 3.3.2 TypeAliases Are Not Runtime Classes

So, lets focus on the `Create[Hero]`

It is evaluates to:
```python
class Create[__main__.Hero]:
    name: str
    age: int | None = None
    secret_name: str
```

The problem is that this thing is not a runtime class, it is a TypeAlias
So you can not use `Create[Hero]()` to actually construct an object.
but it is not a big problem, as once you have a Create[Hero] TypeAlias, It would be trial how to build a real class from it. Pydantic already have an interface for building models into the runtime. The implementation is in progress (one more thing which we can do at this Thesis)

```python
def create_model[T](model: type[T]) -> type[T]:
    ...
    return pydantic.create_model()
```

#### 3.3.3 Triumvirate of Python Type Systems

Lets break down what I mean.

First, is a duck-typing, also known the protocol typing. This is "if something is behave like a duck it is a duck"-ish thing. The oldest thing, and probably the most "natural" for python (I thin we don't fucking need this sentence)

```python

class Duck(Protocol):
    name: str
    def migrate(self) -> None:
        """Migrate to the South"""
        ...

def prepare_for_winter(duck: Duck):
    print("Duck %s moving to the South" % duck.name)
    duck.migrate()

### Real world

class Database:
    user: str
    password: str
    ip: str
    port: str
    name: str
    
    def migrate(self) -> None:
        ...

prepare_for_winter(Database()) # no static warning!
```

Some may argue that it is not an error, as it is explicitly accepting anything which is a compatable like. Again, it is not a point to the today discussion to argue what is better explicit or implicit interfaces. But I just think it is not very pythonic. It may be in some cases (I am not very belive in this lol after I think 3 sec more)

Type manipulation feature - NewProtocol

2. TypedDict forms - subtyping

Simple enough
`{"name": str, "age": int}` is a subtype of a `{"name": str }`... or no? And they are not suptypes of a Dict generally speaking.

Type manipulation feature - NewTypedDict - 

3. Nominal typing... 

No type manipulation feature..

Suggested like this `NewProtocolWithBases[Bases: tuple[type], *Ms: Member]` but not implemented.

Interesting consequence is that the `Create[Hero]` would not be a Pydantic models! At least on the level of types. But the protocol does not restricts the parent base classes.
(I don't really have a point there. But I really like the idea that the python have 3 type system, almost separate, and thats why we have a lot of cursed things today)
Anyway, it is good to start gradually. TypeScript advanced type manipulation was not also build in one update.


## 4. Implementation and Results

The core example are working now - extension for the pydantic.BaseModel.model_dump() types.

Current progress is that it is actually interference the type of the resulting TypeDict. 

> side note about why exactly model_dump(), and not for example model_validate()

The user.model_validate(object) is working as a kinda type-guard. The essence of a Pydantic is that you have something untyped and after some ✨model_validate✨ you have the typed object (or error is raising). 
So trying to type argument of a model_valudate seems like a violation of a Pydantic 

Some may argue, that it is not making much sense to validate the model_dump dictionaries, which is a very popular usecase is dumping to the some storage. I would disagee!

Very useful example would be to actually unpack the model_dump() (maybe excluding some fields) and putting them as a kw args to another function! (FUCK! WHY I DID NOT COME UP TO THIS EXAMPLE EARLIER??? WE DEFINETLY NEED TO IMPLEMENT THIS!)
