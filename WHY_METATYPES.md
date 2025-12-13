# A Meta-Type System for Python: an Expressive Library for Static Typing

> 🧑‍🔬 **RQ**: Why does Python’s standard static typing fail to express certain value-dependent typing relationships, and how can a portable meta-typing mechanism address these limitation?



We explore how Python’s current static typing works, why it feels limited compared to TypeScript, and how we might design an *opt-in* Turing-complete meta type system as a library plus type-checker integration.

We start from the observation that Python already has *two* static typing styles layered on top of its dynamic runtime:

* **Nominal typing**: classic class-based subtyping and generics, introduced by PEP 484 “Type Hints”.([Python Enhancement Proposals (PEPs)][1])
* **Structural typing**: Protocols and TypedDicts from PEP 544, which formalize “static duck typing”.([Python Enhancement Proposals (PEPs)][2])

At runtime we still have fully dynamic duck typing; the static layer is only for *external* tools like mypy, Pyright, Ty, Pyrefly, IDEs, etc. PEP 484 is explicit about the design philosophy: type hints are optional, they do not change runtime semantics, and Python remains dynamically typed; type checking and performance are delegated to third-party tools.([Python Enhancement Proposals (PEPs)][1])

On top of this, PEP 681 adds `typing.dataclass_transform`, which we read as a good example of the “thin, declarative” philosophy: we do not execute decorators at type-check time, we simply *tell* the checker that some decorator or base class is “dataclass-like”, so it should synthesize a constructor and fields according to a fixed schema.([Python Enhancement Proposals (PEPs)][3])  The decorator itself does not perform type-level computation; the checker just believes an agreed-upon story.

This leads us into the tension we’re interested in. On one side, Python’s official PEPs insist that annotations stay relatively simple and first-order so that multiple checkers can agree on them. On the other side, real-world libraries (ORMs, frameworks with decorators, dataclass-style codegen) want *much* richer static guarantees.

We then zoom in on **intersection types** as a concrete pressure point. The typing community has discussed them for years (e.g. GitHub issue threads on `Intersection[...]` and the more recent PDF draft you found that proposes “user-denotable intersection types in Python’s gradual type system”), but they have never been standardized. Meanwhile, new tools show that they are workable in practice:

* Jelle Zijlstra’s write-up on **negation types** and their interaction with unions and intersections illustrates how an extended type algebra can work in a gradual system.([Jelle Zijlstra][4])
* Astral’s **Ty** checker already supports intersection and negation types and uses them internally for much better narrowing than mypy or Pyright.([Astral Docs][5])

So we see that intersection-like ideas are not philosophically forbidden. The real blockers are complexity, interoperability between checkers, and the desire not to turn the *standard* annotation language into a second, highly complex programming language.

At this point we ask a more radical question: instead of only lobbying for specific features like intersections, can we design an **opt-in meta type system** for Python?

The theoretical foundation is already there. Ori Roth’s work “Python Type Hints are Turing Complete” shows that PEP 484’s subtyping relation is expressive enough to simulate Turing machines, by adapting Grigore’s “subtyping machines” construction for Java generics.([arXiv][6])  There is even a reference implementation that compiles Turing machines into Python type hints that mypy evaluates via its subtyping algorithm. So in a strict sense, Python already *has* a Turing-complete type-level substrate — it is just impossible to use sanely in day-to-day code.

We then propose to explore a *designed* meta layer:

* We introduce the idea of a library we tentatively call **`metatypes`** (we choose this spelling over `meta_types` because it reads as a concept rather than an implementation detail).
* This library exposes *type-level combinators* as ordinary classes/aliases: things like `If[...]`, `Equals[...]`, `Add[...]` on `Literal[int]`, `Intersect[...]`, or refinements like `Len[N]` for length-indexed containers.
* A type checker plugin interprets these combinators as a small meta-language and evaluates them into ordinary PEP 484/544 types.

On the implementation side, we see **mypy plugins** as the most realistic place to start. The mypy docs and blog explicitly position plugins as a way to handle “un-type-able” dynamic patterns: the plugin API lets us intercept classes, functions, decorators, and annotations and replace them with richer internal types, without changing the language spec.([mypy.readthedocs.io][7])  Real libraries already do this: SQLAlchemy’s mypy plugin rewrites declarative ORM mappings so their runtime “magic” becomes visible to the checker, although the SQLAlchemy docs also show how painful and fragile such plugins are in the long run.([docs.sqlalchemy.org][8])

We propose to generalize this pattern:

* Instead of each framework inventing its own ad-hoc plugin, we design a *general* meta-typing DSL in `metatypes`.
* The mypy plugin becomes an interpreter for that DSL: it takes annotations using `metatypes` constructs, runs a bounded meta-evaluation (with depth/step limits to control non-termination), and produces the final types.
* Libraries that want very rich static guarantees (e.g. a typed SQL/ORM mini-DSL, length-indexed vectors, unit-safe numeric types) depend on `metatypes` as a **shared infrastructure**, instead of baking separate plugins.

For a bachelor thesis, we frame this as a concrete experiment rather than an attempt to change Python itself. We envision:

1. A formal but lightweight description of the meta-language (its syntax as Python type expressions, and its semantics as an evaluation relation into PEP 484/544 types).
2. A reference implementation: `metatypes` package plus a mypy plugin implementing that evaluator.
3. One or two serious case studies, such as:

   * a small ORM-like query DSL where we statically type SQL-style expressions in Python code, or
   * a length-indexed sequence library where `Vec[T, N]` and operations like `concat`/`take` have precise length invariants enforced at type-check time.
4. An evaluation discussing expressiveness, ergonomics, error messages, and the inevitable undecidability (using Roth’s work as a backdrop).

We situate this work in the existing ecosystem of experimental tools:

* Ty and Pyrefly, which already go beyond mypy in inference and type algebra.([Astral Docs][5])
* `typing_extensions`, which historically acts as the staging ground for new standard typing features.([DEV Community][9])

We propose that `metatypes` lives in the same world: fully optional, purely static, usable from today in any Python project that opts into the plugin, and a potential source of ideas for future standardization (even if only small fragments like intersection types eventually get pulled into the core spec).

So, to summarize what we are setting up:

* We accept the current design philosophy of PEP 484/544/681: Python remains dynamically typed; annotations are optional and (by default) first-order and simple.([Python Enhancement Proposals (PEPs)][1])
* We recognize that, under the hood, the type system is already Turing-complete and that new checkers like Ty are pushing toward richer algebra (intersections, negations).([arXiv][6])
* We propose to explore, as an opt-in experiment, what Python would look like with a **full meta type system**, implemented today as a `metatypes` library plus a mypy plugin, and demonstrated on concrete examples like typed SQL or length-indexed structures.([mypy.readthedocs.io][7])

From here, we can continue in any of a few directions: we can sketch the core primitives of the `metatypes` DSL, choose a flagship domain (typed SQL vs. length-indexed containers), or design the shape of the mypy plugin API we rely on.

[1]: https://peps.python.org/pep-0484/?utm_source=github.com/iliyasone "PEP 484 – Type Hints"
[2]: https://peps.python.org/pep-0544/?utm_source=github.com/iliyasone "PEP 544 – Protocols: Structural subtyping (static duck typing)"
[3]: https://peps.python.org/pep-0681/?utm_source=github.com/iliyasone "PEP 681 – Data Class Transforms"
[4]: https://jellezijlstra.github.io/negation-types.html?utm_source=github.com/iliyasone "Gradual negation types and the Python type system"
[5]: https://docs.astral.sh/ty/?utm_source=github.com/iliyasone "ty - Astral Docs"
[6]: https://arxiv.org/abs/2208.14755?utm_source=github.com/iliyasone "Python Type Hints are Turing Complete"
[7]: https://mypy.readthedocs.io/en/stable/extending_mypy.html?utm_source=github.com/iliyasone "Extending and integrating mypy - mypy 1.18.2 documentation"
[8]: https://docs.sqlalchemy.org/en/latest/orm/extensions/mypy.html?utm_source=github.com/iliyasone "Mypy / Pep-484 Support for ORM Mappings"
[9]: https://dev.to/meseta/factories-abstract-base-classes-and-python-s-new-protocols-structural-subtyping-20bm?utm_source=github.com/iliyasone "Python's new Protocols (Structural subtyping), Abstract ..."
