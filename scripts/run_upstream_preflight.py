"""Explicit read-only G4 preflight over immutable upstream *public testdata*."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from runtime_assurance_lab.upstream_preflight import (
    PINS, analyze_public_upstream_fixtures, download_public_fixtures,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-public-testdata", action="store_true",
                        help="fetch exactly two pinned publicly accessible upstream files; no secrets")
    parser.add_argument("--list-pins", action="store_true", help="show immutable refs without network")
    opts = parser.parse_args()
    if opts.list_pins and not opts.fetch_public_testdata:
        print(json.dumps({"source_kind": "PUBLIC_TEST_FIXTURES", "pins": [asdict(p) for p in PINS]},
                         sort_keys=True))
        return 0
    if not opts.fetch_public_testdata:
        parser.error("no fetch by default; pass --list-pins or --fetch-public-testdata explicitly")
    try:
        assets = download_public_fixtures()
        print(json.dumps(analyze_public_upstream_fixtures(assets), sort_keys=True))
    except (ValueError, OSError, TimeoutError, RecursionError) as exc:
        print(json.dumps({"decision": "INVALID_UPSTREAM_TESTDATA", "error": str(exc)}, sort_keys=True))
        return 3
    return 0  # Successful *research preflight*, NOT an authorized product GO.


if __name__ == "__main__":
    raise SystemExit(main())
