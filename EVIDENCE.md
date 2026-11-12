# Evidence ledger — local checkpoint, 2026-11-12

State classification: **local synthetic PoC / NOT deployed / NOT production-ready / NOT market validated**. This file records observed results rather than assumed external capabilities.

## 1. Inspection

- GitHub connection: `list_repositories`, `get_repo`, `fetch(/contents)`, `fetch_file(README.md)` inspected `ZX7-Labs/runtime-assurance-lab`; branch `main`, GitHub says **PUBLIC**, initial content just `README.md` containing `# runtime-assurance-lab`. No remote writes made. Public visibility conflicts with user request, so local scaffold is necessary.
- Local `/mnt/data` initially empty; no mounted `runtime-assurance-lab`. Python **3.13.5**, Git **2.47.3**, Go and Node present, `pytest` **9.0.2**, `cryptography` **46.0.4**; `kubectl`, Docker, Cosign, OPA not on PATH. The local proof-of-concept does not contact clusters, registries, GitHub APIs, secrets, or external vendors.
- Official-source verification: NVIDIA Nov 11 2026 AICR/k8s-aibom integration (reported AICR v1.2.0 and k8s-aibom v1.6.2), Google upstream, Sigstore, OPA/Gatekeeper, Kyverno, PyCA. See `UPSTREAM_AUDIT.md`; provenance claims in this repo are subordinate to those primary sources.

## 2. Design

- Compared Kubernetes reconciler (A) vs event-sourced signed evidence graph (B) in `PLAN.md`. Chose limited offline B to avoid duplicate inventory/signing/policy controllers and cluster privileges. Explicit schemas for intent, observation, and verdict; three ephemeral signer roles; proof chain plus causal parent links; independent semantic decision recomputation.
- Licensing: no repository-wide release/open-source license selected. Upstream project licenses recorded and attributed in `UPSTREAM_AUDIT.md`; no third-party code imported, only PyCA cryptographic API usage. A full dependency and distribution audit remains outstanding.

## 3. Implementation inventory

- `src/runtime_assurance_lab/{contracts,evaluate,evidence,bench,cli}.py`, `pyproject.toml`; synthetic inputs in `fixtures/`, test files under `tests/`, provisional gate script under `scripts/`.
- CLI supports `evaluate`, `demo`, `verify`, `benchmark` on local JSON only. Expected results: clean `OK`, identity and platform deviations `DRIFT`, stale `STALE`, absent/unverified/future `UNKNOWN`; non-OK returns nonzero.
- `demo` signs 7 case tracks (20 total events), stores `results/demo/{journal,trust-public,checkpoint,findings}.json`. This is not a secure external trust root; demo signer keys are generated ephemerally, and private keys are not written.

## 4. Commands actually executed and results

```sh
# Repository/runtime inspection (separate GitHub connection + local shell)
python3 --version       # Python 3.13.5
git --version           # git 2.47.3

# Locally, inside /mnt/data/runtime-assurance-lab
PYTHONPATH=src python3 -m runtime_assurance_lab.cli demo --output results/demo
PYTHONPATH=src python3 -m runtime_assurance_lab.cli verify --journal results/demo/journal.json --trust results/demo/trust-public.json --checkpoint results/demo/checkpoint.json
# -> {"verified": true, "reason": "DECISIONS_RECOMPUTED"}

PYTHONPATH=src pytest -q
# first pass: 36 passed, 3.91s
# after critical review + two security fixes and regression tests: 39 passed, 4.44s

PYTHONPATH=src python3 -m runtime_assurance_lab.cli benchmark --output results/benchmark.json --repetitions 70 --loops 5
python3 scripts/check_gates.py
# -> passed=true, all 7 provisional sanity gates passed
python3 -m compileall -q src tests scripts
# -> no compile errors
python3 -m pip check
# -> reports pre-existing unrelated conflict: moviepy 2.2.1 requires pillow <12, installed pillow 12.3.0
```

## 5. Benchmarks (`results/benchmark.json`, latest complete pass)

- Dataset: 700 deterministic labeled *synthetic* cases (70 fully clean, 630 intentionally deviating/uncertain), 10 scenario kinds. Positive means **needs attention**, including `DRIFT`, `STALE`, `UNKNOWN`; this is NOT a real-world malicious-drift detection recall estimate.
- Deliberately naive local comparator: **TP 140, FN 490, TN 70, FP 0; recall 22.22%, FPR 0%**.
- Proposed evaluator: **TP 630, FN 0, TN 70, FP 0; recall 100%, FPR 0%**.
- In-process evaluation, 3,500 calls each: naive p95 **2.444 μs**, CPU **13.125 ms**, traced Python heap peak **113,868 B**; proposed p95 **20.430 μs**, CPU **64.428 ms**, peak **118,490 B**. Context-switch, Python runtime, tracemalloc, and measurement order affect these microbenchmarks; the heap figure is NOT Kubernetes pod RSS. Proposed is ~8.36× naive p95 and ~4.91× total CPU time, with 4,622 B larger measured trace peak.
- 180-event signed chain: append/sign **9.715 ms total** (~53.97 μs/event); verify **23.518 ms** (~130.66 μs/event), single-process local keys.
- In-memory **synthetic event-to-verdict** path (incl signing + cryptographic + semantic verification), 50 cases: p50 **715.751 μs**, p95 **1,178.571 μs**, p99 **1,585.659 μs**. Excludes Kubernetes watch/polling delay, registry access, disk IO and delivery queues; **not live end-to-end detection latency**.
- Upstream NVIDIA independently reports k8s-aibom controller ~2.2 mCPU and 28–34 MiB steady state (specific qualified environment). NOT retested here, and **not apples-to-apples** with Python heap/process CPU.
- `results/acceptance.json`: all seven post-baseline provisional synthetic gates passed. These thresholds are initial sanity bounds set from baseline data, not statistically validated SLAs or no-go evidence against real tools.

## 6. Adversarial review and fixes

- Initial weaknesses found: **S-001** signed false assurance decisions passed cryptographic validation; **S-002** malformed list elements in causal refs could raise exceptions.
- Fixes: `verify_decision_semantics` re-evaluates every signed verdict from signed parents, trusted UTC time, pinned policy version, and checks complete one-to-one consumption. Check ref type before hash sets. Separate regression confirms a valid-signature but false `OK` fails independent recomputation. See `SECURITY_REVIEW.md`.
- Attack tests: payload mutation, signature tamper, reorder, omission/truncation, signer-role spoofing, invalid causal edges, workload misbinding, unknown trust root/signer, duplicate refs, invalid reference types, signed false verdict, clock replay. No claim of formal verification or independent external security audit.

## 7. Findings, blockers, falsification, next steps

- No live AICR/k8s-aibom fixture extraction or version-pinned CRD integration was authorized or available; only an explicitly normalized synthetic data contract exists. The system cannot prove Kubernetes workload execution or Sigstore signer identity. Production deployment, market validation, secrets, remote publishing, cloud spend, open-source licensing remain out of scope.
- Privacy blocker: connected GitHub repo is **PUBLIC**. Do not push this work until explicitly resolved; no visibility changes attempted.
- Critical unresolved security assumptions: independent tamper-proof trust root and journal head; key rotation, source-specific attestation validation, trusted UTC, replay/rollback defense, retention/availability; safe RBAC limited to required namespace and resource metadata; cross-plane consistency; realistic coverage.
- Next authorized phase (requires environment and privacy decision): collect **redacted** actual AICR recipe/snapshot and corresponding signed/verified AIBOM resource at pinned versions with read-only permission, resolve mapping, test blinded drift injections, instrument actual event-to-alert latency, node/controller resource footprint, and direct functionality overlap with AICR + k8s-aibom + Sigstore + OPA/Kyverno. Stop or contribute upstream if equivalent coverage already exists or incremental accuracy does not survive controls.
- No claim of production readiness, market demand, maintained license permission beyond documented upstream labels, or completed real-cluster verification.
