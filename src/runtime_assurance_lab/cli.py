"""No network calls, cluster permissions, or secrets access."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from .contracts import Intent, Observation
from .evaluate import POLICY_VERSION, evaluate
from .evidence import append, canonical, generate_signer, head, sha, verify, verify_decision_semantics
from .bench import run, FIXED_NOW


# Bound local inputs: the PoC has no streaming parser or service-level load shedding.
MAX_JSON_BYTES = 8 * 1024 * 1024


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_nonfinite(value):
    raise ValueError(f"nonfinite JSON value: {value}")


def read_json(path: Path):
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError(f"JSON input exceeds {MAX_JSON_BYTES} bytes")
    # JSON's default last-key-wins behavior is unacceptable for signed evidence.
    return json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=_reject_duplicate_keys,
                      parse_constant=_reject_nonfinite)


def dump(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False).encode()+b"\n")


def evaluation(intent_path: Path, observation_path: Path, at: datetime):
    spec = read_json(intent_path)
    intent = Intent.parse(spec)
    raw = read_json(observation_path)
    observation = Observation.parse(raw) if raw is not None else None
    finding = evaluate(intent, observation, now=at)
    return spec, raw, finding


def demo(fixtures: Path, output: Path):
    cases = ("clean", "model-drift", "stale", "unverified", "missing", "image-drift", "platform-drift")
    keys = {kind: generate_signer() for kind in ("intent", "observation", "decision")}
    trust = {kind: [keys[kind][1], kind] for kind in keys}
    events: list[dict] = []
    findings = []
    for case in cases:
        spec, obs, finding = evaluation(fixtures/"intent.json", fixtures/f"{case}.json", FIXED_NOW)
        intent_event = append(events, "intent", spec, [], "intent", keys["intent"][0])
        refs = [sha(canonical(intent_event))]
        if obs is not None:
            observation_event = append(events, "observation", obs, [], "observation", keys["observation"][0])
            refs.append(sha(canonical(observation_event)))
        decision = {**finding.to_dict(), "policy_version": POLICY_VERSION,
                    "evaluated_at": FIXED_NOW.isoformat(), "fixture": case}
        append(events, "decision", decision, refs, "decision", keys["decision"][0])
        findings.append(decision)
    checkpoint = {"expected_count": len(events), "expected_head": head(events), "trusted_now": FIXED_NOW.isoformat()}
    success, detail = verify(events, trust, expected_head=checkpoint["expected_head"], expected_count=checkpoint["expected_count"])
    assert success, detail
    semantic_ok, semantic_reason = verify_decision_semantics(events, trusted_now=checkpoint["trusted_now"])
    assert semantic_ok, semantic_reason
    dump(output/"journal.json", events)
    dump(output/"trust-public.json", trust)
    dump(output/"checkpoint.json", checkpoint)
    dump(output/"findings.json", findings)
    return {"cases": len(cases), "events": len(events), "chain_verified": success,
            "verification": detail, "semantic_verification": semantic_reason, "findings": findings,
            "caution": "Public trust and checkpoint created in the same demo; no external anchoring, no real attested runtime."}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Offline AI intent/observation correlation research PoC")
    sub = p.add_subparsers(dest="action", required=True)
    q = sub.add_parser("evaluate", help="Evaluate strict normalized JSON fixtures")
    q.add_argument("--intent", required=True, type=Path)
    q.add_argument("--observation", required=True, type=Path)
    q.add_argument("--now", required=True, help="timezone-aware ISO-8601")
    d = sub.add_parser("demo", help="Generate synthetic signed journal and untrusted demo checkpoint")
    d.add_argument("--fixtures", type=Path, default=Path("fixtures"))
    d.add_argument("--output", type=Path, default=Path("results/demo"))
    v = sub.add_parser("verify", help="Verify journal against separately supplied public keys and checkpoint")
    v.add_argument("--journal", required=True, type=Path)
    v.add_argument("--trust", required=True, type=Path)
    v.add_argument("--checkpoint", required=True, type=Path)
    b = sub.add_parser("benchmark", help="Fixed-seed synthetic comparison against a naive local comparator")
    b.add_argument("--output", type=Path, default=Path("results/benchmark.json"))
    b.add_argument("--repetitions", type=int, default=70)
    b.add_argument("--loops", type=int, default=5)
    args = p.parse_args(argv)
    try:
        if args.action == "evaluate":
            _, _, decision = evaluation(args.intent, args.observation, datetime.fromisoformat(args.now.replace("Z", "+00:00")))
            result = decision.to_dict()
            code = 0 if decision.status == "OK" else 2
        elif args.action == "demo":
            result = demo(args.fixtures, args.output)
            code = 0
        elif args.action == "verify":
            checkpoint = read_json(args.checkpoint)
            events = read_json(args.journal)
            is_ok, reason = verify(events, read_json(args.trust),
                                   expected_head=checkpoint["expected_head"], expected_count=checkpoint["expected_count"])
            if is_ok:
                is_ok, reason = verify_decision_semantics(events, trusted_now=checkpoint["trusted_now"])
            result = {"verified": is_ok, "reason": reason}
            code = 0 if is_ok else 2
        else:
            if args.repetitions <= 0 or args.loops <= 0:
                raise ValueError("benchmark repetitions and loops must be positive")
            result = run(args.repetitions, args.loops)
            dump(args.output, result)
            code = 0
        print(json.dumps(result, sort_keys=True, indent=2))
        return code
    except (ValueError, KeyError, TypeError, OSError, UnicodeError, RecursionError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
