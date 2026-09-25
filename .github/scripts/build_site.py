#!/usr/bin/env python3
"""Build the exact static artifact that GitHub Pages may publish."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path, PurePosixPath


DEV_ONLY = {
    ".gitignore",
    "README.md",
}
DEV_PREFIXES = (".github/",)


def tracked_files(repo: Path) -> list[PurePosixPath]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    paths = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = PurePosixPath(raw.decode("utf-8"))
        name = relative.as_posix()
        if name in DEV_ONLY or name.startswith(DEV_PREFIXES):
            continue
        paths.append(relative)
    return sorted(paths, key=lambda path: path.as_posix())


def publish_inputs(repo: Path, includes: list[str]) -> list[PurePosixPath]:
    """Resolve a bounded public file list before replacing the generated artifact."""
    inputs = set(tracked_files(repo))
    for name in includes:
        relative = PurePosixPath(name)
        if (not relative.parts or relative.is_absolute() or ".." in relative.parts
                or any(part.startswith(".") for part in relative.parts)
                or relative.parts[0] == "_site"):
            raise SystemExit(f"Invalid public preview input: {name}")
        inputs.add(relative)
    for relative in inputs:
        source = repo / relative
        if (not source.is_file() or source.is_symlink()
                or not source.resolve().is_relative_to(repo)):
            raise SystemExit(f"Publish input must be a regular file inside the repo: {relative}")
    return sorted(inputs, key=lambda path: path.as_posix())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("_site"))
    parser.add_argument(
        "--include", action="append", default=[], metavar="RELATIVE_FILE",
        help="Explicit public file to include in a local preview before it is tracked",
    )
    args = parser.parse_args()

    repo = args.root.resolve()
    output = args.output
    if not output.is_absolute():
        output = repo / output
    output = output.resolve()

    if output.parent != repo or output.name != "_site":
        raise SystemExit("Refusing to replace anything except <repo>/_site")

    inputs = publish_inputs(repo, args.include)

    if output.exists():
        shutil.rmtree(output)
    output.mkdir()

    copied = 0
    total_bytes = 0
    for relative in inputs:
        source = repo / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"Publish input must be a regular file: {relative}")
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1
        total_bytes += source.stat().st_size

    print(f"Built _site: {copied} files, {total_bytes / 1024 / 1024:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
