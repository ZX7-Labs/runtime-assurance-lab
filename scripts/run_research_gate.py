"""Reproducible offline no-go gate; never licenses a production release."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from runtime_assurance_lab.research_gate import MAX_BYTES, run
from runtime_assurance_lab.json_strict import loads_strict

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=ROOT / "research/upstream_overlap.json")
    parser.add_argument("--comparison", type=Path, default=ROOT / "results/incremental_value_post_gate.json")
    parser.add_argument("--verify-report", type=Path, default=None,
                        help="compare an already committed report against recomputed results")
    parser.add_argument("--output", type=Path, default=None,
                        help="write a fresh report; refuses overwriting an existing file")
    args = parser.parse_args()
    try:
        result = run(args.matrix, args.comparison)
        if args.verify_report is not None:
            if args.verify_report.stat().st_size > MAX_BYTES:
                raise ValueError("research report exceeds file bound")
            recorded = loads_strict(args.verify_report.read_bytes())
            if recorded != result:
                raise ValueError("recorded gap decision differs from independently recomputed report")
        elif args.output is not None:
            with args.output.open("x", encoding="utf-8") as f:
                json.dump(result, f, indent=2, sort_keys=True, ensure_ascii=True)
                f.write("\n")
        print(json.dumps({"decision": result["decision"], "missing_gates": result["missing_independent_gates"],
                          "report_matches": args.verify_report is not None}, sort_keys=True))
    except (ValueError, OSError, RecursionError) as exc:
        print(json.dumps({"decision": "INVALID_EVIDENCE", "error": str(exc)}))
        return 3
    return 0  # Means report generation succeeded; NOT production GO.


if __name__ == "__main__":
    raise SystemExit(main())
