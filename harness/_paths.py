"""Paths at the runner boundary. These checks never execute a tool."""
from __future__ import annotations

import pathlib
import re


def relative(value: str) -> pathlib.PurePosixPath:
    if (not isinstance(value, str) or not value or value.startswith(("/", "~"))
            or re.match(r"^[A-Za-z]:", value) or "\\" in value
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError("path must be a nonempty relative POSIX path")
    path = pathlib.PurePosixPath(value)
    if not path.parts or any(p in ("..", ".git") for p in path.parts):
        raise ValueError("path must stay in its allowed root; '..' and '.git' are forbidden")
    return path


def confined(root: pathlib.Path, value: str) -> pathlib.Path:
    """Check lexical traversal and the resolved target, including missing leaves."""
    path = root / relative(value)
    try:
        path.resolve().relative_to(root.resolve())
    except (ValueError, OSError, RuntimeError) as exc:
        raise ValueError(f"path escapes allowed root: {value}") from exc
    # A symlink into repository metadata is also forbidden, even inside root.
    if ".git" in path.resolve().relative_to(root.resolve()).parts:
        raise ValueError("repository metadata is not an input")
    return path


def destination(root: pathlib.Path, value: str) -> pathlib.Path:
    """Runner-owned output locations must not contain preexisting symlinks."""
    path = confined(root, value)
    current = path
    while True:
        if current.is_symlink():
            raise ValueError(f"staging destination is a symlink: {current}")
        if current == root:
            break
        current = current.parent
    return path


if __name__ == "__main__":
    import sys
    # Used after an upstream checkout, before its Dockerfile is read or built.
    confined(pathlib.Path(sys.argv[1]), sys.argv[2])
