#!/usr/bin/env python3
"""Format the Python code blocks embedded in Markdown files with ruff.

Ruff does not understand Markdown, so this helper extracts every fenced
```python``` / ```py``` block, pipes its body through `ruff format`
(reusing the project's ruff config via `--stdin-filename`), and writes the
result back into the document.

Usage:
    # rewrite the files in place
    python scripts/format_md_python.py THESIS.md README.md

    # CI mode: don't touch anything, just fail if a block isn't formatted
    python scripts/format_md_python.py --check THESIS.md README.md

Indented code blocks (e.g. inside list items) are de-indented before
formatting and re-indented afterwards, so the surrounding Markdown is left
untouched.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Opening fence: optional indent, ```/~~~, then a python info string.
_OPEN = re.compile(
    r"^(?P<indent>[ \t]*)(?P<fence>```+|~~~+)[ \t]*(?P<lang>python|py)\b.*$"
)


def _format_snippet(code: str, *, source: Path) -> str | None:
    """Run `ruff format` over a single snippet, returning the formatted text.

    Returns ``None`` when the snippet is not parseable Python (e.g. PEP 827
    pseudo-syntax or a ``>>>`` REPL transcript); such blocks are illustrative
    prose and are left untouched.
    """
    proc = subprocess.run(
        ["ruff", "format", "--stdin-filename", f"{source.name}.block.py", "-"],
        input=code,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        if "Failed to parse" in proc.stderr:
            return None
        raise RuntimeError(
            f"ruff failed to format a Python block in {source}:\n{proc.stderr.strip()}"
        )
    return proc.stdout


def _reformat(text: str, *, source: Path) -> str:
    """Return ``text`` with every fenced Python block reformatted by ruff."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        match = _OPEN.match(line.rstrip("\n"))
        if not match:
            out.append(line)
            i += 1
            continue

        indent = match.group("indent")
        fence = match.group("fence")
        # Closing fence: same indent, same fence char, nothing else of substance.
        close = re.compile(
            rf"^{re.escape(indent)}{re.escape(fence[0])}{{{len(fence)},}}[ \t]*$"
        )

        body: list[str] = []
        j = i + 1
        while j < n and not close.match(lines[j].rstrip("\n")):
            body.append(lines[j])
            j += 1

        if j >= n:
            # Unterminated fence — leave the rest of the file as-is.
            out.extend(lines[i:])
            break

        # De-indent, format, re-indent.
        raw = "".join(b[len(indent) :] if b.startswith(indent) else b for b in body)
        formatted = _format_snippet(raw, source=source)
        if formatted is None:
            # Non-Python (pseudo-syntax / REPL transcript) — keep verbatim.
            out.append(line)
            out.extend(body)
            out.append(lines[j])
            i = j + 1
            continue
        reindented = "".join(
            (indent + ln if ln.strip() else ln)
            for ln in formatted.splitlines(keepends=True)
        )

        out.append(line)
        out.append(reindented)
        out.append(lines[j])  # closing fence
        i = j + 1

    return "".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="Markdown files to process")
    parser.add_argument(
        "--check",
        action="store_true",
        help="don't write files; exit non-zero if any block is not formatted",
    )
    args = parser.parse_args(argv)

    needs_format: list[Path] = []
    for path in args.files:
        original = path.read_text(encoding="utf-8")
        updated = _reformat(original, source=path)
        if updated == original:
            continue
        needs_format.append(path)
        if not args.check:
            path.write_text(updated, encoding="utf-8")
            print(f"reformatted Python blocks in {path}")

    if args.check and needs_format:
        joined = ", ".join(str(p) for p in needs_format)
        print(
            f"Python code blocks are not formatted: {joined}\n"
            "Run: uv run python scripts/format_md_python.py "
            + " ".join(str(p) for p in args.files),
            file=sys.stderr,
        )
        return 1

    if not args.check and not needs_format:
        print("all Python code blocks already formatted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
