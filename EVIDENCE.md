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

## 8. User authorization, hardening, and local recheck (2026-11-12)

- User explicitly accepted that `ZX7-Labs/runtime-assurance-lab` is PUBLIC and authorized applying this source; earlier publication prohibition in sections 1/7 is superseded for source commits **only**. Production deployment, license grant, release publishing, spending and secret/real-data access are still not authorized.
- Reinspected local Git history/35 tracked files and remote `main` via GitHub; remote head before publication `59110e2e041784da0d310a7f69217b9a17354f6b` with only `README.md`. Local tracked-file scan for common high-confidence credential patterns produced no matches; this is not a complete secret audit.
- S-003: found ambiguous duplicate-key and nonfinite JSON acceptance plus unbounded CLI file ingestion. Added strict parser (recursive duplicate rejection, nonfinite rejection, invalid UTF-8 rejection, 8 MiB/file), proof verifier invalid trust/anchor rejection and 10,000 event cap. Tests cover malformed JSON/trust/anchor and CLI fail-closed semantics. See `SECURITY_REVIEW.md`.
- Actual commands: `PYTHONPATH=src pytest -q` -> **50 passed, 5.31 s**; `PYTHONPATH=src python -m runtime_assurance_lab.cli demo --fixtures fixtures --output results/demo` -> success; `PYTHONPATH=src python -m runtime_assurance_lab.cli verify --journal results/demo/journal.json --trust results/demo/trust-public.json --checkpoint results/demo/checkpoint.json` -> **DECISIONS_RECOMPUTED**; `python scripts/check_gates.py` -> **7/7 provisional checks pass** using the recorded prior benchmark (no benchmark rerun in this step).
- Limitations unchanged: source claims are synthetic, local benchmark is not real detection latency, public sample checkpoint+public keys have no external trust anchoring, model confidence is not actual model-execution attestation, and no AICR/k8s-aibom live integration has been performed.

## 9. Continued work: M1 offline k8s-aibom v1beta1 adapter (2026-11-12)

**Starting checkpoint:** inspected local `/mnt/data/runtime-assurance-lab` on `main`, initial clean checkout at local commit `ca315d4` (previous synthetic checkpoint `1893beb`). Read `PLAN.md`, `EVIDENCE.md`, contracts, evaluator, evidence verification, tests, and upstream audit. GitHub is already explicitly allowed to be public by the user. This is a **synthetic/offline integration milestone**, not G4 real-cluster approval.

**Primary upstream sources inspected through the connected GitHub integration:** `GoogleCloudPlatform/k8s-aibom` tag `v1.6.2` (tag commit `47bf6418e40eee22905973528b879dc075181b3f`), files `api/v1beta1/{aibom_types.go,aibom_conditions.go,groupversion_info.go}`. Source specifies `aibom.k8saibom.dev/v1beta1` `AIBOM`, `spec.workloadRef`, controller-owned `status.summary`, `status.bomDocument`, `status.lastReconciled`, `status.observedGeneration`, Ready and Stale conditions. The schema does **not** guarantee the independent runtime/signer/recipe proof required by H1. URL and license audit recorded in `UPSTREAM_AUDIT.md`. NVIDIA published AICR workflow/validation still covers infrastructure; no duplicate controller implemented.

**Implementation:** added `src/runtime_assurance_lab/aibom_adapter.py` and CLI `evaluate-aibom`. The adapter parses local, version-pinned AIBOM JSON and performs workload namespace/name/kind/version cross-check, generation/currentness/Ready/Stale check, bounded inline BOM base64+SHA-256+size+CycloneDX 1.6 JSON check. It never fetches external sinks. For healthy-but-unverified data it preserves model identity *claim* only, downgrades `signed=verified` to unverified observation confidence and explicitly omits model/image/platform digests. This ensures the fixture cannot produce `OK`. Generated `fixtures/aibom-v1beta1-synthetic.json` is **handmade**, never exported from a cluster; no live schema or upstream code has been copied.

**Tests and debugging:** first `PYTHONPATH=src pytest -q` run had **1 failed, 69 passed**: synthetic CR workload `lab/one` differed from existing intent `lab/demo` (also model ref). Corrected only the synthetic fixture to match the intended workload and model. Retest -> **70 passed**. Self-review then detected and fixed: (1) unhashable condition names could raise an unintended TypeError; (2) checksum-valid but non-CycloneDX inline bytes were accepted as BOM; (3) even validly signed decision records allowed extraneous unevaluated assurance fields. Added adversarial regression cases. Final run **73 passed** (pytest 7.23s; repeated end run 6.57s). This is implementer self-review, **not** an independent external audit.

Actual commands executed in local checkout:

```sh
PYTHONPATH=src pytest -q
# initial: 1 failed, 69 passed (fixture identity mismatch)
# after fixture fix: 70 passed
# after security-review fixes: 73 passed
python scripts/bench_aibom_adapter.py
# 1,000 pre-parsed synthetic CR conversions; results/aibom_adapter_benchmark.json
PYTHONPATH=src python -m runtime_assurance_lab.cli evaluate-aibom --intent fixtures/intent.json --aibom fixtures/aibom-v1beta1-synthetic.json --now 2026-11-12T03:25:00Z
# -> status UNKNOWN, exit 2 (expected; model/image/platform digest unavailable, model unverified)
PYTHONPATH=src python -m runtime_assurance_lab.cli demo --fixtures fixtures --output /tmp/ral-m1-demo
PYTHONPATH=src python -m runtime_assurance_lab.cli verify --journal /tmp/ral-m1-demo/journal.json --trust /tmp/ral-m1-demo/trust-public.json --checkpoint /tmp/ral-m1-demo/checkpoint.json
# -> {"verified": true, "reason": "DECISIONS_RECOMPUTED"}
python scripts/check_gates.py
# -> seven previous synthetic pilot gates pass; uses the PRIOR baseline benchmark, not a fresh real-world baseline
```

**New adapter baseline:** `results/aibom_adapter_benchmark.json` on this local runtime: 1,000 pre-parsed fixture conversions, median **86.141 µs**, p95 **135.236 µs**, max **623.039 µs**, traced Python heap peak **36,600 bytes**, total CPU **97.079 ms**. These measurements exclude JSON file I/O, authenticating the Kubernetes API, controller delay, cluster RSS and execution verification; not a deployment SLO. Hardware/environment not qualified. Existing synthetic gate thresholds are unchanged; do not compare these new numbers to NVIDIA's controller resource measurements.

**Review findings:** `SECURITY_REVIEW.md` S-004/S-005/S-006. Verifying a hash *inside* an untrusted CR does not authenticate its source or provide freshness. `lastReconciled` does not prove an actual inference run. An external AIBOM sink is not accessed. No keys, kubeconfig, secrets, cloud credentials, network writes, or production workloads were used.

**Remaining blockers/stop criteria:** G4 representative source exports, namespace-restricted permission review, *independently* verified upstream signed model evidence and AICR recipe association, actual v1.6.2 CRD install compatibility, controlled drift injections and direct tool baselines remain blocked by lack of approved cluster/data. Falsify incremental-value hypothesis before expanding infrastructure. Distribution licensing still undecided; public GitHub source commit authorization does not grant production deployment/release/marketing permission.

## 10. Authorized GitHub source checkpoint and exact remote verification (2026-11-12)

- Local clean M1 source commit before remote publication: `d9ecd34` (`Add pinned offline AIBOM adapter and fail-closed evidence review`). Parent is local `ca315d4`; GitHub history has a different parent chain, so identical contents need not have identical commit IDs.
- GitHub connector read the current public `main` head `74c8e8c55a9de754729ce79288868cf03a205af7`. Compared remote `README.md`, `EVIDENCE.md`, `PLAN.md` and `src/runtime_assurance_lab/evidence.py` with the original local checkpoint, exact text matched.
- Through the connected GitHub API, created a tree from **14** modified/new tracked text files with base tree `4e0b29ffcd3e265dc0dc9b070d30cd860f683f8c`; created commit `1727021761a8aff218e50683f859f0392932b9e9` and updated `main` non-force with expected old head lease. Connector returned `success=true`.
- Independently fetched the new remote branch/tree and the complete contents of all 14 changed files: remote head matched `1727021761a8aff218e50683f859f0392932b9e9`, 40 tracked files, **14/14 changed contents exact text equal** to the locally tested M1 snapshot, with **0 mismatches**. No deploy, secret read, release or paid API used.
- This paragraph is a subsequent evidence-only checkpoint; publishing it will create a new remote commit. The source commit above is independently verified regardless of the evidence-only commit ID. GitHub source commit authorization came from the user's explicit public-repository approval.

## 11. M2 CPU-only GitHub Actions test harness — local verification (2026-11-12)

**Checkpoint recovered:** local clean `main` at `e2f76c7` (source `d9ecd34`), GitHub public remote `main` `f0b53b03dcaf012f92b18bf21d96f915fa6ab5e2`. Before changes, `PYTHONPATH=src python3 -m pytest -q` -> **73 passed, 7.07s**; offline `demo` and `verify` -> `{ "verified": true, "reason": "DECISIONS_RECOMPUTED" }`; `python3 scripts/check_gates.py` -> **7/7 previous synthetic checks pass**. Existing GitHub tree had **zero** `.github/workflows/` paths. No live cluster or GPU access.

**Milestone chosen:** G4 (real AICR+Kubernetes comparison) is still blocked by lack of an approved cluster and real evidence. M2 automates existing nonprivileged, CPU-only validations on *free standard public-repository GitHub-hosted runners*; it is NOT a substitute for G4. GitHub official runner/billing docs checked 2026-11-12: https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job and https://docs.github.com/en/billing/concepts/product-billing/github-actions. The official GitHub action tag refs were fetched through the connected GitHub integration: `actions/checkout` v7 -> `3d3c42e5aac5ba805825da76410c181273ba90b1`; `actions/setup-python` v7 -> `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`. Both are **pinned commit SHAs** in the new workflow, not floating tags.

**Files:** `.github/workflows/offline-assurance.yml` (push to `main`, pull requests, manual dispatch, `contents: read`, `persist-credentials: false`, no secrets, standard `ubuntu-24.04`, Python 3.11/3.13, timeout 10min per job); `.github/ci-constraints.txt` (version constraints for local baseline libraries, NOT hashes); `scripts/ci_smoke.py` (six synthetic process-level checks, including expected AIBOM `UNKNOWN` and modified signed journal rejection). Updated `PLAN.md`, `DECISIONS.md`, `README.md`, `SECURITY_REVIEW.md` to separate hosted CI from runtime validation. No new runtime dependencies or deployment paths.

**Commands actually executed:**

```sh
PYTHONPATH=src python3 -m pytest -q
# before: 73 passed, 7.07s
PYTHONPATH=src python3 scripts/ci_smoke.py
# PASS: clean, drift, stale, aibom-unknown, signed-demo, tamper-rejected
PYTHONPATH=src python3 -m pytest -q
# after local implementation: 73 passed, 6.76s
python3 scripts/check_gates.py
# 7/7 historical stored synthetic pilot gates passed; did NOT rerun microbenchmarks
python3 -m venv --system-site-packages /tmp/ral-m2-venv
/tmp/ral-m2-venv/bin/python -m pip install --no-index --no-build-isolation --no-deps -e .
# initial ERROR: BackendUnavailable: Cannot import setuptools.build_meta;
# environment-only problem: base /usr Python venv could not see parent /opt/pyvenv packages.
printf '/opt/pyvenv/lib/python3.13/site-packages\n' > /tmp/ral-m2-venv/lib/python3.13/site-packages/current-python-packages.pth
/tmp/ral-m2-venv/bin/python -m pip install --no-index --no-build-isolation --no-deps -e .
# PASS, fully offline package/editable installation using preinstalled build tools
/tmp/ral-m2-venv/bin/python scripts/ci_smoke.py
# PASS, no PYTHONPATH supplied
/tmp/ral-m2-venv/bin/python -m pytest -q
# 73 passed, 0.83s (shared package dependencies and warm runtime caches)
/tmp/ral-m2-venv/bin/python -m compileall -q src tests scripts
# PASS
python3 scripts/check_gates.py
# 7/7 stored synthetic checks pass
# Local PyYAML BaseLoader parse/inspection of workflow, commit-SHA pin lengths,
# workflow triggers, token scope, timeout and Python matrix -> PASS.
```

**Critical review / limits:** GitHub-hosted Python 3.11 was not available in this container; Python 3.11 and actual GitHub-hosted execution are **not yet verified**, only statically configured. CPU-only GitHub workflow does not test GPUs, k8s-aibom controller installation, AICR runtime exports, Cosign integration, Kubernetes latency, or user/environment secrets. GitHub `pull_request` runs potentially adversarial code with read-only token and no repo secrets; PyPI/setuptools artifacts have pinned versions but not hash locked (supply-chain risk). No secrets were read, no deployment created, no license added, no paid runner selected. Do not claim a hosted CI success until an actual job result is inspected.


## 12. Verified GitHub-hosted CPU-only CI outcome (2026-11-12)

- Authorized public GitHub source commit on `main`: `ac43998a9ebdefb8e99a6bafd6046d5d928c5f59` (non-force update against prior head `f0b53b03dcaf012f92b18bf21d96f915fa6ab5e2`). Fetched branch and eight published file blobs, including the exact local hashes of `.github/workflows/offline-assurance.yml`, `.github/ci-constraints.txt`, and `scripts/ci_smoke.py`. GitHub read/write verification used the connected GitHub API; no production rollout.
- Official GitHub Actions run: https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43155730493 ; head SHA matched `ac43998a9ebdefb8e99a6bafd6046d5d928c5f59`; status **completed**, conclusion **success**. Retrieved both job objects, steps and full job logs.
- **Python 3.11:** 73 pytest cases passed in **1.14s**, separate six-case offline smoke `pass`, historical synthetic gate JSON `passed=true`; build/install/compile/verification steps successful.
- **Python 3.13:** 73 pytest cases passed in **1.07s**, separate six-case offline smoke `pass`, historical synthetic gate JSON `passed=true`; build/install/compile/verification steps successful.
- This proves two hosted CPU Python test environments passed the committed synthetic validation suite. It **does not** provide authentic NVIDIA AICR/k8s-aibom collection, verified model execution, a real cluster/GPU latency benchmark, a tamper-proof external trust anchor, or market validation. G4/G5 remain blocked and no production approval was granted. Hosted test artifacts and logs are public and must only contain synthetic data.
- This section is a subsequent evidence-only source update; its commit creates another public CI run and must be verified separately. No new synthetic benchmark values or deployment claims are introduced.
