"""Bounded offline operator handoff preflight; never authenticates or approves G4."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat

from runtime_assurance_lab.g4_handoff import MAX_RAW_BYTES, inspect_handoff


def read_regular_file(path: Path) -> bytes:
    """Read a bounded regular file; reject a symlink at the final path.

    This is not a hardened sandbox against hostile ancestor directories or
    concurrent filesystem mutation; run in an isolated operator environment.
    """
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        item = os.fstat(fd)
        if not stat.S_ISREG(item.st_mode) or not 0 < item.st_size <= MAX_RAW_BYTES:
            raise ValueError("source is not a bounded regular file")
        with os.fdopen(fd, "rb", closefd=False) as file:
            data = file.read(MAX_RAW_BYTES + 1)
        if not 0 < len(data) <= MAX_RAW_BYTES:
            raise ValueError("source exceeds byte limit")
        # If the underlying file mutates during read, refuse this snapshot.
        item_after = os.fstat(fd)
        if (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns) != (
                item_after.st_dev, item_after.st_ino, item_after.st_size, item_after.st_mtime_ns):
            raise ValueError("source modified during read")
        return data
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("intent", "recipe", "aibom"):
        parser.add_argument("--" + name, required=True, type=Path)
        parser.add_argument("--expected-" + name + "-sha256", required=True)
    parser.add_argument("--output", type=Path, help="new report file only; mode 0600")
    opts = parser.parse_args(argv)
    try:
        report = inspect_handoff(
            intent_bytes=read_regular_file(opts.intent),
            recipe_bytes=read_regular_file(opts.recipe),
            aibom_bytes=read_regular_file(opts.aibom),
            expected_intent_sha256=opts.expected_intent_sha256,
            expected_recipe_sha256=opts.expected_recipe_sha256,
            expected_aibom_sha256=opts.expected_aibom_sha256,
        )
        if opts.output is not None:
            fd = os.open(opts.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(report, out, sort_keys=True, indent=2)
                out.write("\n")
        print(json.dumps(report, sort_keys=True))
        # Deliberately nonzero: integrity-only handoff is NOT G4 approval.
        return 2
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError) as exc:
        # Never reflect upstream source text or filesystem paths in errors.
        # Validation failures are intentionally classified, not echoed.
        print(json.dumps({"schema": "ral-g4-untrusted-handoff/v1",
                          "decision": "INVALID_OR_UNTRUSTED_HANDOFF",
                          "g4_authorized": False, "error_type": type(exc).__name__},
                         sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
