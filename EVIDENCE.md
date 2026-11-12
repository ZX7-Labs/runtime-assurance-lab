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

## 13. M3 offline AICR RecipeResult byte pin + AIBOM correlation (2026-11-12)

**Starting verified checkpoint:** GitHub public `main` `1f12a699b381246b9ead803e8a9c56240653c4f7` (M2 hosted CI, Python 3.11/3.13 success previously recorded), local `main` `2983e1a`. On first inspection local `EVIDENCE.md` had a pre-existing, uncommitted deletion of section 12; that diff was saved as `/mnt/data/runtime-assurance-starting-evidence-diff.patch` and the documented verified section was restored from local committed `HEAD` before appending M3. No code changes existed initially. Inspect commands: `git status --short --branch`, `git log -5 --oneline`, `git diff -- EVIDENCE.md`, and read `PLAN.md`, `EVIDENCE.md`, source and tests. No Docker/kubectl/GPU on PATH. Starting controls: `PYTHONPATH=src python -m pytest -q` -> **73 passed, 7.26s**, `PYTHONPATH=src python scripts/ci_smoke.py` -> six synthetic checks pass, `python scripts/check_gates.py` -> **7/7 stored synthetic gates pass**.

**Why M3, not real G4:** AICR/cluster deployment, source attestation, real workload captures and GPU timing remain unavailable/unauthorized. M3 is bounded offline interoperability preparation, not a claim that synthetic source correlation establishes deployment truth. It adds no controller, admission policy, remote network access, secret acquisition, or spend.

**Upstream tag evidence:** Read NVIDIA `NVIDIA/aicr` **v1.2.0** tag using connected GitHub API. At that tag `api/aicr/v1/schemas/RecipeResult.schema.json` specifies required `apiVersion`, `kind`, `criteria`, `componentRefs`, `deploymentOrder`, `metadata`; `pkg/recipe/metadata.go` defines `RecipeResultKind`, and `pkg/header/header.go` maps stable recipe artifacts to `aicr.run/v1`. Official AICR CLI docs show JSON recipe export (`aicr recipe --format json`); no AICR binary ran here. Tag source and links in `UPSTREAM_AUDIT.md`. No upstream source code or schema copied. Schema subset is tested but the full schema is **not implemented**.

**Implementation:** `src/runtime_assurance_lab/aicr_adapter.py` performs bounded 8 MiB exact-byte SHA-256 check against (1) a separately supplied expected digest and (2) normalized intent's `platform_recipe_digest`; parses a subset of `RecipeResult v1` while rejecting duplicate component identities, malformed fields, mixed versions and unknown intent category. Shared `json_strict.py` rejects duplicate object keys, nonfinite constants, exponent overflow (`1e999`) and invalid UTF-8, reused by CLI, AICR and inline AIBOM parsing. `cli.py` adds `correlate-offline` and bounded local reads. Synthetic recipe and matching intent fixtures only. `scripts/ci_smoke.py` adds cross-plane `UNKNOWN` check, in addition to original six; `tests/test_aicr_adapter.py` and regressions test forged/tampered bytes, invalid version/type, malformed JSON, workload observation gaps and parser overflow. `PLAN.md`, `DECISIONS.md`, `SECURITY_REVIEW.md`, `README.md`, and source audit updated.

**Debugging and tests actually run:** After a parser consolidation, first pytest: **94 passed, 1 failed** because a newly written overflow regression lacked `pytest` import; second pytest: **94 passed, 1 failed** because it also lacked `read_json` import. Fixed the test imports only, then reran:

```sh
PYTHONPATH=src python -m pytest -q
# -> 95 passed, 7.98s (after fixing regression-test imports)
PYTHONPATH=src python scripts/ci_smoke.py
# -> 7 synthetic checks pass including aicr-aibom-unknown
PYTHONPATH=src python scripts/bench_aicr_recipe.py > results/aicr_recipe_benchmark.json
python scripts/check_gates.py
# -> 7/7 PREVIOUS stored synthetic gates pass; no new end-to-end baseline
python -m compileall -q src scripts tests
# -> success
```

**New measured synthetic overhead** (latest `results/aicr_recipe_benchmark.json`): 1,000 **preloaded** synthetic RecipeResult byte-pin+JSON conversions, median **55.431 µs**, p95 **71.002 µs**, max **308.153 µs**, process CPU **60.276 ms** total, peak `tracemalloc` Python allocations **50,640 bytes**. Excludes I/O, actual AICR snapshot/validation, source authentication, Sigstore verification, Kubernetes polling, GPU runtime and alerts. Not a real detector latency or release SLO.

**Contrarian review:** A malicious actor who controls recipe, pin and intent can forge a matching pair. A matching recipe digest is not a verified AICR qualification or proof the recipe was applied. The AIBOM CR itself is not source-authenticated, and model/image digests are absent. The combined fixture intentionally returns `UNKNOWN` (exit 2), never `OK`. Regressions reject tampered exact bytes with invalid-input exit 3, but **do not** authenticate publisher, intent signer, independent trust root, or runtime model identity. This is implementer self-review only. See S-008–S-010. G4/G5 are still blocked; stop if authorized real-data tests show no incremental detection benefit above upstream.

**Publication:** GitHub update will be recorded only after exact remote file and CI run outcomes are observed; do not interpret this local checkpoint as a hosted CI result.

**Additional final CLI checks (local):**

```sh
PYTHONPATH=src python -m runtime_assurance_lab.cli correlate-offline --intent fixtures/intent-aicr-synthetic.json --recipe fixtures/aicr-recipe-result-synthetic.json --expected-recipe-sha256 sha256:a44787410b9f5f8e7c60df82007639c11b90bacff731cf75ad9ad0681305febb --aibom fixtures/aibom-v1beta1-synthetic.json --now 2026-11-12T03:25:00Z
# -> UNKNOWN, four missing/unverified fields, exit 2 (expected)
PYTHONPATH=src python -m runtime_assurance_lab.cli verify --journal results/demo/journal.json --trust results/demo/trust-public.json --checkpoint results/demo/checkpoint.json
# -> {"verified": true, "reason": "DECISIONS_RECOMPUTED"}, exit 0
# Note: demo checkpoint and public trust material are co-located, not externally secured.
```

## 14. M4 offline raw-source correlation receipt + independent replay (2026-11-12)

**Resume/inspection:** read `PLAN.md`, `EVIDENCE.md`, `DECISIONS.md`, `README.md`, `SECURITY_REVIEW.md`, AICR/AIBOM adapters, policy, signed evidence verification, CI and tests. Local `main` began clean at `e1ef781` (M3 implemented and locally committed); connected GitHub `main` was still `1f12a699b381246b9ead803e8a9c56240653c4f7` (M2 hosted CI checkpoint). M3 source had **not** yet been published during this inspection; do not claim hosted M3/M4 success from old CI. No local Kubernetes, Docker or GPU integration was performed. Existing G4/G5 remain blocked for lack of authentic, authorized, redacted exports and independent origin/attestation proof.

**Design/hypothesis:** M3 `correlate-offline` returned a decision but not a replayable raw-source report; an auditor could not re-derive its component count, adapter limitations, and exact source bytes without an explicit receipt. M4 adds a small, **unsigned** receipt (not a bespoke Sigstore implementation) with exact SHA-256 for intent/AICR RecipeResult/AIBOM raw JSON bytes, upstream version tags, policy version, explicitly supplied clock, a partially observed decision and reasons/limitations. A separate verifier takes the raw source files and independently supplied pin+UTC time, reconstructs the report and requires exact JSON-type-sensitive equality. Missing model/image evidence still evaluates `UNKNOWN`. Receipt create uses an exclusive file open and cannot overwrite existing evidence. Neither digest nor replay authenticates the *source* or proves inference execution; a party controlling the inputs can create a consistent forgery. This is a narrow offline prep milestone, NOT G4.

**Implementation:** new `src/runtime_assurance_lab/crossplane_receipt.py` with bounded, deterministic `make_receipt`/`replay_receipt`; CLI subcommands `receipt-offline --output` and `replay-offline --receipt` (source paths/pin/clock supplied separately), common `read_bytes`; new adversarial `tests/test_crossplane_receipt.py`; `scripts/ci_smoke.py` now includes receipt replay and fake-OK rejection; local preloaded measurement script `scripts/bench_crossplane_receipt.py`, output `results/crossplane_receipt_benchmark.json`. Docs in `PLAN.md`, `DECISIONS.md`, `SECURITY_REVIEW.md`, `README.md` updated. `receipt-offline` exits zero for **successful file creation**, even if decision is `UNKNOWN`; a replay success response explicitly disclaims attestation.

**Debug/falsification evidence:** first complete post-feature test run: **115 passed, 1 failed** because changed recipe bytes triggered an exception in replay rather than a structured negative reply. Converted malformed-source/incorrect-pin cases to `verified_replay=false`, `SOURCE_OR_PIN_INVALID`. Retest: **116 passed**. Contrarian review then constructed `component_count: true` against expected integer `1`; Python dict equality incorrectly returned true for this forged receipt. Added a regression that failed, then switched to canonical **JSON-byte equality**, respecting bool/int/float distinction; suite became **117 passed**. Added exclusive-file creation guard and overwrite regression, now **118 passed**. This is implementer-led adversarial review; independent external security assessment remains undone.

**Actual commands and results:**

```sh
PYTHONPATH=src python -m pytest -q
# first new suite: 115 passed, 1 failed (invalid-source replay exception expectation)
# after structured replay error: 116 passed
PYTHONPATH=src python -m pytest -q tests/test_crossplane_receipt.py -k json_type_confusion
# intentionally RED: 1 failed; forged bool true passed ordinary equality
PYTHONPATH=src python -m pytest -q tests/test_crossplane_receipt.py
# after canonical JSON comparison: 22 passed
PYTHONPATH=src python -m pytest -q
# after canonical comparison: 117 passed
PYTHONPATH=src python -m pytest -q
# final suite after exclusive file guard: 118 passed
PYTHONPATH=src python scripts/ci_smoke.py
# PASS: 8 synthetic process-level cases incl replay and forged-OK rejection
PYTHONPATH=src python scripts/bench_crossplane_receipt.py > results/crossplane_receipt_benchmark.json
# 1,000 preloaded synthetic receipt builds + 1,000 replays;
# build median 303.335us, p95 512.853us; replay median 450.947us, p95 715.821us;
# combined process CPU 905.546ms, Python tracemalloc peak 134,781 bytes.
python scripts/check_gates.py
# PASS: 7/7 HISTORICAL stored synthetic pilot checks (not refreshed benchmark)
python -m compileall -q src tests scripts
# PASS
```

**Limits/remaining steps:** local Python microbench excludes file I/O, Kubernetes, AICR runtime validation, Sigstore signatures, GPU inference, real source-authenticated clocks, alert delay and pod CPU/RSS. Report cannot be trusted if raw sources and external pin come from one adversary. No real cluster work, secrets, access tokens, production release, paid services or deployment. Replay receipts are **unsigned**; future provenance should rely on established upstream mechanisms. G4 remains the testable product-differentiation gate and still lacks authorized input/cluster access. M3+M4 remote publication/CI must be separately checked and appended **after** confirmed.

## 15. M5 synthetic falsification controls: distinguish latent drift from detection (2026-11-12)

**Resume and state:** Inspected `PLAN.md`, `EVIDENCE.md`, contracts, evaluation policy, prior benchmarks, CI smoke and source adapters. Local `main` was clean at `eb69aa2` (`Add replayable raw-source cross-plane receipt with adversarial checks`); connected GitHub `main` was still `1f12a699b381246b9ead803e8a9c56240653c4f7` (last independently hosted-verified M2). **M3/M4 were only local** at the start of this work; prior interruption did NOT publish them. Baseline `PYTHONPATH=src python3 -m pytest -q` gave **118 passed in 13.34s**. The original eight process-level smoke checks and 7/7 stored historical synthetic pilot gates also passed. No network access from the local container (`git ls-remote` failed DNS resolution for github.com). GitHub connector *read* was available. No cluster/GPU or source-attested inputs available; G4/G5 remain blocked.

**Question and choice:** The prior 100% synthetic *needs-attention* recall conflates `DRIFT`, `STALE` and `UNKNOWN`; its deliberately weak two-string naive baseline does not establish any advantage over available industry tools. To bound that claim without introducing another collector/controller, created `scripts/bench_incremental_value.py` and tests `tests/test_incremental_value.py`. An independent same-input reference policy implements the entire documented v1 decision rule separately and serves as a **negative control**, not as a substitute for NVIDIA, Google, Sigstore or Kyverno. Deterministic synthetic scenarios provide ground truth *by construction*, including hidden drift behind absent/stale/future records. Each trial repeats scenario kinds with different workload IDs (not independent population sampling). No source artifacts or third-party code copied.

**Implementation and review:** Dataset is 12 conditions × 50 identity variants = 600 constructed cases. A synthetic `fully_observable` condition means a fresh and complete *claimed* observation with `model_confidence=verified`, **not a cryptographically authenticated source**. The verifier maintains non-`OK` for missing/expired/unverified/incomplete evidence. M5 compares the exact status, not just `status != OK`. Also added a separate adversarial *source forgery probe*: counterfeit complete fields and an untrusted `verified` flag matching intent while actual hidden runtime has drift. The evaluator returns **`OK` for this attacker-controlled assertion**. This is an intentionally documented **known security limitation**; `security_gate_passed=false`, not a success. It is omitted from the 600-case policy-visible matrix, so the zero incomplete-evidence unsafe-OK rate does **not** generalize to forged complete claims. The independent same-input reference cannot solve source provenance either. See `SECURITY_REVIEW.md` S-015–S-018 and D-017–D-018.

**Actual commands and results (no remote publishing in this segment):**

```sh
PYTHONPATH=src python3 -m pytest -q tests/test_incremental_value.py
# 9 passed (before and after adding forged-source probe)
PYTHONPATH=src python3 -m pytest -q
# 127 passed (after M5 was introduced)
PYTHONPATH=src python3 scripts/bench_incremental_value.py --output results/incremental_value.json
# 600 cases, report written; 50 repetitions of 12 deterministic scenarios
PYTHONPATH=src python3 scripts/ci_smoke.py
# nine process-level synthetic smoke cases pass, including negative-control probe
python3 scripts/check_gates.py
# all seven STORED earlier synthetic gates still pass; not a fresh G4 baseline
python3 -m compileall -q src tests scripts
# success
```

**Measured output**, `results/incremental_value.json`: 350 constructed latent-drift cases, 200 policy-visible drift cases and 200 drift verdicts; visible-condition recall **100%**, total latent-drift recall **57.14%**; 0 `DRIFT` on 250 clean cases; 0 unsupported `OK` among 350 synthetically incomplete observations; independently coded same-input reference disagreed on **0/600**. The naive comparator produced 450 unsafe `OK` classifications across drift OR missing/non-current evidence, demonstrating its weakness, **not** product superiority. The separate forgery probe returned **unsafe `OK`** when attacker supplied false-but-complete fields. Preloaded local p95 processing times are recorded in JSON, measured with `perf_counter_ns` and ordered rounds without I/O, `tracemalloc`, pods, collectors, source attestation, GPU or live notification delay. They are **not comparable** to the older traced-heap p95 nor to a Kubernetes SLO. These are deterministic fixture results, not statistical recall estimates for real applications.

**Falsification/checkpoint:** No new source-authenticated runtime detection, novelty or market value proven; fair input parity supports the *null* interpretation on this synthetic policy. G4 must compare equivalent real tools using authorized, redacted exports with pinned provenance, drift injection and actual end-to-end processing/overhead. If upstream composition gives equivalent signal at acceptable cost, stop or contribute upstream. **Remote M3/M4/M5 publication and hosted CI for these changes are not established in this entry.** Public visibility/source publishing is authorized but this local container has no direct git network; do not label any local pass as hosted CI.

## 16. M3–M5 public source publication + hosted CI (2026-11-12)

**Authorization and scope:** The user previously authorized public GitHub source commits; this did NOT authorize production, secrets, upstream real data, special GPU runners or spending. Local Git directly could not resolve github.com, so the approved connected GitHub integration was used. No new dependencies, deployment, release or paid services.

**Atomic source transfer:** The independently inspected connected repository `ZX7-Labs/runtime-assurance-lab` `main` still pointed at M2 commit `1f12a699b381246b9ead803e8a9c56240653c4f7`, tree `05ff3f4678714a5c9f5bef89863215bfd1f1ed88`. The tested local main was `20b6dc0327d708c7ff3a991cf934b51932f3cd84`. Before publishing, compared all unchanged local Git blob hashes to the remote tree. Found a pre-existing `AGENTS.md` divergence; included that file with the 25 M3–M5 changed files, rather than silently preserving a different operating contract. Inspected all 26 exact text payloads and created GitHub tree `39fc6a7716cffbfa0f3cdf86c943f71a0c1878fa` using the remote M2 tree as base. **Independently fetched the created tree** and verified **all 57/57 tracked blob SHAs exactly match the tested local snapshot**, 0 extra files and 0 mismatches. Created remote commit `eefecedb98aae3a02b3a824640b8d47bea232f58`, parent M2, then advanced `main` with `force=false` and an exact expected old-head lease; connector returned `success=true`. Fetched `main` again: matching new commit and tree. No history rewrite. Git commit SHA differs from local due to a different parent, but verified tree bytes are identical.

**Hosted CI, actual observed result:** Connected GitHub workflow run [43162008548](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43162008548), `head_sha=eefecedb98aae3a02b3a824640b8d47bea232f58`, status **completed**, conclusion **success**. Independently queried its jobs: **Python 3.11** and **Python 3.13** both completed **success**, including installation, unit/integration/adversarial/synthetic performance tests, module compilation, 9 offline process smoke scenarios, and stored historical synthetic gate validation. The same 127-test suite was already run locally. CI is CPU-only synthetic validation, NOT GPU/Kubernetes runtime or cryptographic source authenticity.

**Unchanged limitations:** The source-forgery probe still demonstrates an unsafe `OK` on counterfeit complete observations, so production assurance is blocked even though CI is green. The 100% condition-visible synthetic drift recall and 57.14% latent drift recall do NOT prove real-world detection accuracy. Same-input negative-control parity rules out claiming algorithmic novelty from the constructed fixture study. G4 authentic origin and representative tool comparisons, third-party review, real Kubernetes/GPU metrics, and G5 market/license choices remain unresolved. No release readiness or commercialization evidence established.
