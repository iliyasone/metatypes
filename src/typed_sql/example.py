


# ── static track (mypy-typemap) ───────────────────────────────────────────
if TYPE_CHECKING:

    def _static() -> None:
        reveal_type(User.id)  # want: Column[User, "id", int]
        reveal_type(User.email)  # want: Column[User, "email", str]
        reveal_type(User.age)  # want: Column[User, "age", str | None]
        reveal_type(Post.author)


# ── runtime track ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    # print("User.id    ->", User.id)
    # print("User.email ->", User.email)
    # print("User.age   ->", User.age)
    print(eval_typing(Post.author))
