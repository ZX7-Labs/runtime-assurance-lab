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

## 17. M6 — fail-closed source-forgery containment, independent-pin prototype (2026-11-12)

**Resume:** Re-read local `PLAN.md`, `EVIDENCE.md`, `SECURITY_REVIEW.md`, evaluator, contracts, cryptographic evidence journal, AICR/AIBOM adapters, raw cross-plane receipt, benchmark and tests. Local head before work `5c739ee68285a22edab1e419856cf5fc65d0c9fd`, branch `main`. `PUBLISH_PROBE.md` was already untracked and was left untouched; it is not a deliverable. Last verified GitHub head before work `c23a7ea8b7060f381631f53a0cca252ff640d8d1`; prior hosted CI had Python 3.11/3.13 `127 passed` each. No cluster, GPU, Docker, authentic upstream signed evidence, independent security reviewer or authorized credentials available. Baseline local `PYTHONPATH=src python3 -m pytest -q`: **127 passed in 13.74 s**.

**Attack reproduction before the fix (RED / known M5 S-018):** parsed `fixtures/intent.json` and `fixtures/clean.json`, created a complete normalized observation claiming `model_confidence="verified"` (the attacker can hide different actual runtime state), called `evaluate(..., now=2026-11-12T03:25:00Z)` and observed `{'workload':'lab/demo','status':'OK','rules':[]}`. Root cause: no independent source-origin/key/attestation gate; the `verified` label is input data. Signed hash-chain journal and replay receipts were not a source-authenticity verification mechanism.

**Alternatives:** Compared (A) bounded source-bound offline verifier with independently pinned root/intent and external monotonic checkpoint, versus (B) real Sigstore/DSSE and independently anchored transparency checkpoint under authorized upstream identity policy. See `PLAN.md` M6. Selected A for **offline containment only**; B needs external trust/cluster evidence and remains G4. No new dependency, hosted CA, Kubernetes controller, deployment or signing service.

**Implementation:**

- `src/runtime_assurance_lab/evaluate.py`: untrusted public evaluator fails closed as `UNKNOWN/SOURCE_AUTHENTICITY_UNVERIFIED` instead of claiming `OK` or authenticated `DRIFT`; old comparison retained as **internal claim-only research** helper; freshness/missing/unknown semantics preserved. Breaking policy identifier bumped to `ral-intent-observation-v2-provenance-gate`.
- New `src/runtime_assurance_lab/source_auth.py`: strict bounded schema and JSON; independently supplied exact intent SHA-256, authority manifest SHA-256, current clock and monotonic `(expected_sequence, expected_prev_head)`; allowlisted source/key/workload binding, Ed25519 signature over domain-separated envelope, SHA-256 of **original observation bytes**, signed timestamp and external clock constraints; no genesis reuse for noninitial sequence; only verified signer emits signed-source `OK/DRIFT` and a **proposed** next checkpoint. Does not persist/publish an external anchor.
- `src/runtime_assurance_lab/cli.py`: added `evaluate-authenticated` requiring every authority/intent pin and checkpoint argument; untrusted `evaluate`, `evaluate-aibom`, `correlate-offline`, local journal and receipt remain non-assurance sources. Exit 0 only for verified-source matching synthetic assertion, 2 for indeterminate/drift, 3 for invalid inputs.
- `tests/test_source_auth.py`: synthetic positive signed source, source/key/scope/time/canonicalization attacks, altered raw bytes/signature/authority, forged key replacement, false `verified`, stale/future, replay, rollback, forked head, gap, invalid genesis, missing root/checkpoint, CLI boundary, and the **residual authorized-but-dishonest signer** limitation. Fixed test-only Ed25519 private-key seed is PUBLIC and not a credential.
- `scripts/ci_smoke.py`: added independently supplied synthetic pinned-positive, replay rejection and modified authority/hash denial to process-level CI smoke. `scripts/bench_source_auth.py` measures local preloaded verification time, with no API or upstream trust. `scripts/bench_incremental_value.py` keeps old historical 600-case claim-only same-input comparator but uses the fail-closed **public** evaluator for the separate forgery probe. `src/runtime_assurance_lab/bench.py` labels old measurements as claim-only; older `results/incremental_value.json` is **not overwritten**, preserving the RED historical M5 proof. New `results/incremental_value_post_gate.json` documents after-state. `results/demo/*.json` regenerated for v2 demo semantics. Docs updated without changing the completed M1–M5 historical status.

**Actual test/debug/retest record:**

```sh
PYTHONPATH=src python3 -m pytest -q
# BEFORE changes: 127 passed in 13.74s
# After initial M6 code and test migration: 2 failed, 147 passed (attack-test expected reasons for wrong source/workload were inaccurate)
# Fixed expected reason: 149 passed in 14.80s
# Added deeper signed-source/adversarial tests: 1 failed, 27 passed in targeted file (incorrect test regex for naïve clock)
# Fixed test regex: 28 passed in targeted file; 156 passed in full suite
# Added valid-policy v2 and authorized-signer residual: 157 passed in full suite
# Genesis/sequence consistency hardening: 2 targeted failures (old replay regression sent an invalid operator checkpoint)
# Corrected replay test and CI smoke to pass non-genesis independent checkpoint.
PYTHONPATH=src python3 -m pytest -q
# FINAL LOCAL: 158 passed in 14.40s
PYTHONPATH=src python3 scripts/ci_smoke.py
# PASS 12 named process-level scenarios, including authenticated-positive, replay and self-attested-root rejection
python3 scripts/check_gates.py
# PASS seven STORED historical synthetic gates (old claim-only numbers, NOT current trust-gate qualification)
PYTHONPATH=src python3 -m runtime_assurance_lab.cli verify --journal results/demo/journal.json --trust results/demo/trust-public.json --checkpoint results/demo/checkpoint.json
# -> {"verified":true,"reason":"DECISIONS_RECOMPUTED"} on regenerated v2 synthetic journal (self-generated demo trust, NOT independent root)
PYTHONPATH=src python3 scripts/bench_source_auth.py --samples 500 --output results/source_auth_benchmark.json
# 500 preloaded repeated valid signed-source checks; p50=367.459us; p95=529.328us; p99=609.245us
# process CPU 194.488ms; traced Python heap peak 57,224 bytes. Same synthetic input/checkpoint is deliberately reused
# for microbenchmark only; no cross-run durable replay protection, source/cluster/GPU I/O or inference delay.
PYTHONPATH=src python3 scripts/bench_incremental_value.py --trials 50 --output results/incremental_value_post_gate.json
# 600 historical claim-only cases: same-input comparator 0 disagreements; 200/200 synthetic observable drift;
# 200/350 latent drift; separate untrusted forged-source probe now status UNKNOWN, security_gate_passed=true (scoped).
```

**Trust-boundary finding:** a pinned Ed25519 key authenticates a *source assertion* if and only if its authority manifest was independently pinned; it **does not** prove actual model/GPU execution or independently validate Sigstore model identity. A compromised authorized signer or a caller who can alter both roots and inputs can still create matching signed assertions. `next_checkpoint` is returned but must be durably and atomically persisted outside the attacker-controlled channel for practical rollback prevention. The CLI's `--now` argument is not a trusted time service. No cross-language canonicalization interoperability, TUF/Sigstore bundle verification, key revocation/rotation policy, production RBAC, resource isolation, third-party adversarial review or live G4 measurements. Self-critical test coverage is **not independent review**.

**Next executable action:** publish this tested local v2 source on the authorized public repository via non-force conditional ref update; verify exact remote tree and hosted Python 3.11 + 3.13 CI logs. Afterward, external G4 requires approved real signed source artifacts, durable independent trust roots/checkpoint store and a scoped read-only cluster for end-to-end metrics. G5 remains blocked by unmet real-world customer/licensing evidence. No production deployment or secrets accessed.

## 18. M6 public source and hosted verification checkpoint (2026-11-12)

- Source snapshot local commit: `2fdc2731a098d8d40ddaf3e2533c7372a2b9f5ea` (`Gate source-authenticated assurance on independent pins and replay anchors`). Compared GitHub pre-update `main` `c23a7ea8b7060f381631f53a0cca252ff640d8d1` to the locally tracked 62 files; all unchanged source hashes matched and there were no remote-only files.
- Created remote tree `3e16d41303b2505861ac86bdd28b20ef43a23fb5` from 23 changed/new text files and old remote tree. Independently fetched the new Git tree and compared **all 62/62 Git blob SHA-1 values** to the tested local snapshot; **0 mismatches and 0 extras**. Created remote commit `16fc4f4cca166912939b03fd3128b17bd076e8d0`, parent old `main`; `update_ref(force=false, expected_sha=old_main)` returned `success=true`. Re-read new branch: commit/tree matched. Local and remote Git commit IDs differ due to independent ancestry, but tracked bytes match. `PUBLISH_PROBE.md` was pre-existing/untracked and not published. No secrets or release/deployment artifacts were added.
- GitHub Actions run [43167150345](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43167150345) for this exact commit returned `status=completed, conclusion=success`. Independently fetched hosted job logs: **Python 3.11: 158 passed in 2.05s**, **Python 3.13: 158 passed in 2.39s**. Both jobs completed compilation, 12 synthetic smoke scenarios (including signed-positive, replay rejection and counterfeit-authority rejection), and **7/7 STORED historical** acceptance checks. Hosted run wall-time was approximately 18 seconds, but actual runner CPU/RAM usage was NOT measured. No GPU/cluster integration or independently protected signing roots.
- Before publishing, `git diff --cached --check` passed. Scan of staged additions for common high-confidence secret-token/private-key indicators found no matches; **not** a full secret review. Locally `python3 -m compileall -q src tests scripts` passed, and Python 3.13 pytest **158 passed in 15.13s**. Process smoke and stored gates passed. `python3 -m pip check` reported only an existing unrelated environment conflict: moviepy 2.2.1 requires Pillow <12, installed Pillow 12.3.0. No new dependencies installed or spend incurred.
- Verified current official NVIDIA AICR documentation describes offline artifact/bundle verification with separately controlled Sigstore trust roots and `--require-creator` identity restrictions: https://docs.nvidia.com/aicr/latest/user-guide/artifact-verification/ . This reinforces next-stage reuse of upstream verification; no actual AICR bundle or upstream signer was tested. Sigstore's own public verification design separates signature integrity, expected identity and independent root/trust decisions; neither is supplied by the PoC.
- **Disposition:** M6 is an **offline security containment milestone**, not closure of the G4 runtime-attestation security assurance gap. It prevents untrusted or unverifiable source payloads from returning positive authenticated status via the public CLI. A compromised authorized signer can still make a false matching assertion, and a caller with control over root/pin/monotonic checkpoint can self-attest. External independent adversarial reviewer was unavailable; self-review and tests alone are not sign-off. G4 real signed upstream AICR/AIBOM source exports, independently protected monotonic state, key/identity policy, trusted clock, cluster/GPU instrumentation and direct upstream comparison remain BLOCKED pending authorization and authentic evidence. G5 licensing/product validation remains blocked.
- **Next executable action:** in an authorized, independently administered validation environment, take a redacted real upstream AICR signed bundle plus actual k8s-aibom v1.6.2 AIBOM export; use AICR's existing offline verifier with pinned creator identity and trusted root; bind to a read-only scoped workload and persist the monotonic checkpoint independently; then run a controlled source-forgery/drift comparison. Stop if upstream composition achieves equivalent coverage or if trust cannot be independently established. Do not deploy this synthetic envelope.

## 19. Evidence-only checkpoint correction (2026-11-12)

An asynchronous local document export/synchronization replaced the working copy of `PLAN.md` with the pre-M6 text after the source commit had been created. The first evidence-only local commit `d8b3473` therefore accidentally removed the M6 design section from `PLAN.md` while adding remote CI results. Detected via `git show --stat` (`PLAN.md` 29 deletions), restored the **complete M6 architecture/trust-boundary section** from tested local source commit `2fdc273`, and appended the hosted verification and upstream reference. `README.md`, `DECISIONS.md` and `SECURITY_REVIEW.md` working copies were also found reverted to pre-M6 text; restored those three files from the tested HEAD snapshot (no other user changes were present in their exact diffs). This checkpoint intentionally preserves M1–M5 and M6 review content instead of silently publishing a truncated plan.

## 20. Remote documentation integrity discrepancy found during final audit (2026-11-12)

The first M6 source publish `16fc4f4` correctly committed the new implementation, tests, scripts, and synthetic results and passed hosted Python 3.11/3.13 CI. A subsequent **Git-committed HEAD-to-remote** audit (not just comparison against a staging manifest) found three documentation blob SHA mismatches: `DECISIONS.md`, `README.md`, `SECURITY_REVIEW.md`. The cause was mutable local working-copy content reverting after the tested local commit but before the first JSON transport was assembled: the first published tree matched the transport payload, **not the immutable committed version** for those three files. Previous shorthand "62/62 matches" referred to the transport payload and must NOT be interpreted as a match to the committed documentation. Code and test hashes did match. Separately, the evidence-only commit `d8b3473` had lost `PLAN.md` M6 text, detected and locally corrected at `c703615`. The correction process now reads **all file contents from `git show HEAD:<path>`**, not from mutable working files, and will verify the complete remote tree against **all** committed Git hashes. All affected records and the failure cause are preserved; no claim of verified published documentation should be made until that comparison succeeds.

## 21. Corrected M6 committed-tree publication verified (2026-11-12)

- Compared current committed local Git tree to GitHub `main` at `16fc4f4`; the exact discrepancy set was five documentation blobs (`DECISIONS.md`, `EVIDENCE.md`, `PLAN.md`, `README.md`, `SECURITY_REVIEW.md`). The other 57 code/test/fixture/benchmark/workflow hashes already matched. Rebuilt transport **from `git show HEAD:path` / `git ls-tree HEAD`**, not from mutable working files. The source was local commit `d3eaa5558d03f069beda0c5c451b9c52d7aceb2c`, which restores the M6 architecture and documents the synchronization issue.
- Created remote tree `235071bfd7644c0de44e3fe328b62770b107110b`; independently fetched and verified **62/62 immutable committed Git blob SHAs equal**, **zero extras/mismatches**. Published GitHub commit `55484bd8cbe3e6318fea6869cb8c716dc79fc67f` by `update_ref(force=false, expected_sha=16fc4f4...)`, returned `success=true`. Re-read `main` and confirmed new commit/tree.
- Fetched GitHub Actions run [43167932209](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43167932209), matching `head_sha=55484bd8...`, `status=completed`, `conclusion=success`. Individually retrieved hosted job logs: Python **3.11: 158 passed in 2.20s**, Python **3.13: 158 passed in 2.82s**; both include successful 12-case offline smoke and 7/7 stored pilot gates. No deployment, paid runner, production secrets, independent security review or GPU/cluster resource test.
- **Final correction status:** M6 source-forgery fail-closed *offline control* and its M1–M5 preserved histories are now published together with full M6 docs. The earlier publication mismatch and repair are explicitly recorded in sections 19–21; neither a tested source assertion nor a hosted CPU CI run proves actual GPU execution. G4/G5 remain blocked as stated. The remaining next action is authorized, independently trusted real AICR/AIBOM evidence and secure monotonic state to test the actual runtime boundary.

## 22. M7 — offline transactional checkpoint harness, local verification (2026-11-12)

**Resumption:** The working `/mnt/data/runtime-assurance-lab` directory contained exported documentation only and had no `.git`; recovered the full 62-file source from the previously verified `runtime-assurance-lab-m6-verified.zip` into a separate working directory, leaving the original documents untouched. GitHub connector independently reported `main=7543b98aeb6de3b246d7c605c5aaeac8a32f2c3f`, 62 tracked files; the recovered `PLAN.md` blob `b63e031c093853b3eca644e824c51cb25cea7111` and `EVIDENCE.md` blob `17746514edbb082f6f7cc0bbffdb1f5e3b08d1fe` matched GitHub. M1–M6 records were preserved. Local baseline: `PYTHONPATH=src python -m pytest -q` -> **158 passed in 23.40s**. The original Git ancestor history is not embedded in the zip, so the recovered research checkout has a separate new local Git baseline, while content identity is grounded in remote Git blobs.

**Milestone choice and comparison:** G4 authentic AICR/AIBOM, cluster, independently administered monotonic store and key policies remain blocked. The next offline-falsifiable gap was M6's operator-supplied checkpoint progress not being transactionally stored. Compared A) operator-pinned local SQLite transactions vs B) externally administered CAS/transparency checkpoint service; implemented A as a **local simulation only**, not a trusted key root. See `PLAN.md` and `SECURITY_REVIEW.md` S-022–S-024.

**Files created:** `src/runtime_assurance_lab/checkpoint_store.py`, `tests/test_checkpoint_store.py`, `scripts/bench_checkpoint_store.py`, `results/checkpoint_store_benchmark.json`. **Files modified:** `src/runtime_assurance_lab/cli.py`, `scripts/ci_smoke.py`, `AGENTS.md`, `DECISIONS.md`, `PLAN.md`, `README.md`, `SECURITY_REVIEW.md`, `EVIDENCE.md`. No third-party source code or new package dependency was added. Changes are offline and CPU-only.

**Observed implement → fail → fix → retest sequence:**

```text
Initial recovered M6 baseline: 158 passed in 23.40s.
Initial M7 target: 1 failed, 12 passed — corrupt SQLite state triggered an uncaught genesis/sequence ValueError.
Fix: convert malformed state to UNKNOWN/CHECKPOINT_STATE_INVALID; explicitly close connections.
Retest M7 target: 13 passed.
One combined full-test-plus-smoke invocation timed out after pytest had passed its intermediate progress; no passing smoke result was inferred.
Independent full pytest retry: 171 passed in 21.59s.
After simulated SQLite commit failure, negative-control rollback and permission cases: 17 targeted tests passed.
After broken-database CLI error handling: 18 targeted tests passed.
Final full local pytest: 176 passed in 22.33s.
PYTHONPATH=src python scripts/ci_smoke.py -> PASS 14 named synthetic subprocess scenarios (run separately).
python scripts/check_gates.py -> passed=true, 7/7 HISTORICAL stored synthetic pilot gates; not M7 performance or G4 evidence.
python -m compileall -q src tests scripts -> PASS.
python -m pip check -> existing unrelated moviepy/Pillow dependency conflict; not fixed via repo changes.
git diff --check -> PASS.
```

**Adversarial and recovery tests:** valid synthetic detached signer + pins, second sequence/restart, replay using old source or old state pin, forged signature no checkpoint burn, incorrect intent/trust pins, tampered checkpoint fields and dropped database schema, nonexistent DB, symlink, concurrent same-sequence write attempts (exactly one committed), signed `DRIFT` advancing sequence without `OK`, simulated commit failure, and restored old DB with a *separately retained new pin* rejected. Crucially a **negative-control** test restores BOTH DB and the operator's external pin and observes accepted replay: this demonstrates the remaining high-severity trust gap, not a security pass. A trusted clock/source's physical runtime assertions and authentic upstream identities were NOT exercised.

**Local processing baseline:** `PYTHONPATH=src python scripts/bench_checkpoint_store.py --samples 100 --output results/checkpoint_store_benchmark.json`. Repeated sequential signed synthetic events, ephemeral signer, SQLite `BEGIN IMMEDIATE`, synchronous FULL local commit. Median **3,989.220 µs**, p95 **5,004.478 µs**, p99 **6,496.049 µs**, max **8,410.260 µs**; process CPU **175.245 ms**; Python traced heap peak **54,731 bytes**. This adds local disk transactions to cryptography, so do NOT compare its time directly with the earlier in-memory signing-only measurement. Excludes any Kubernetes polling, network, GPU, externally anchored trust, and realistic crash recovery.

**Unresolved findings:** operator's state hash, trust and intent pins MUST be held separately; if attacker can roll back the DB AND external pin, replay succeeds. SQLite cannot create independent truth. Crash between DB commit and external pin protection may cause an availability dead-end with no safe automatic rebootstrap. No production multi-process/distributed durability SLA, independent security auditor, key revocation/rotation, trusted-time service, real model-execution attestation, source-specific Sigstore/AICR verification, customer value or G4 test environment. The stateless M6 `evaluate-authenticated` command remains available and must not be treated as durable replay enforcement. No external spending, secrets, production deployment or release.

**Publication next:** publish the tested immutable Git object contents to the previously authorized public `ZX7-Labs/runtime-assurance-lab` without force, validate all remote blob hashes, then verify Python 3.11 and 3.13 GitHub-hosted CI and append exact run IDs/statuses in this ledger. G4/G5 remain blocked, with next real action being authorized independently anchored monotonic service plus authentic AICR/AIBOM evidence and scoped cluster read-only validation.

## 23. M7 source publication + hosted CI verification (2026-11-12)

- Immutable local source commit `edc0a6cff43a167246e01e4bdecc0301bdfe7537` (12 changed/new text files over recovered M6 ZIP, 66 final tracked). GitHub prepublication `main=7543b98aeb6de3b246d7c605c5aaeac8a32f2c3f`, tree `ed93d649293181084e2815314ca0061d07543323`; verified **all unchanged file blobs** matched that base and no unrelated remote extras existed. The upload manifest used `git show HEAD:path` raw UTF-8 bytes, NOT mutable working files; a first manifest-generation attempt failed because Python tool and container users differ in Git safe-directory ownership. Retried with `git -c safe.directory=...` and no `.strip()` on source file bytes. This preserved exact Git blob identity.
- GitHub new tree `d865d7bccc3916553e6301c1298a4be466e31797`, independently fetched: **66/66 file blob hashes matched** the local immutable snapshot, **0 mismatches, 0 extras**, not truncated. Created remote commit `b43eba546d258dab19539b05093238dcfbb1b6a5` with parent expected old main; non-force `update_ref(expected_sha=old)` returned `success=true`; fetched `main` and verified commit/tree.
- Exact published source GitHub Actions run [43184485606](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43184485606) reached `completed / success` on head `b43eba...`. Independently fetched two hosted job logs: **Python 3.11: 176 passed in 2.91s**, **Python 3.13: 176 passed in 3.49s**. Both job steps including Python compilation, 14-case `offline_smoke=pass` (with stateful consumption and replay rejection), and checks of seven **stored historical** synthetic pilot gates completed successfully. Runner CPU/RSS and real Kubernetes/GPU usage were **not** measured.
- M7 remains an **offline checkpoint-state simulation only**. Even a matching Ed25519 signature with a monotonic SQLite sequence is not an independently verified running model. Rollback succeeds if both local DB and external pin are compromised, explicitly demonstrated by the negative-control test. No independent adversarial security reviewer or upstream authenticated evidence was available, so G4 and G5 retain their prior blockers. No new network/cluster deployment, secret handling, paid runner or open-source license action.
- **Next executable action:** obtain authorization for an independently administered monotonic state/identity service and redacted authentic NVIDIA AICR and Google k8s-aibom evidence; verify upstream signers via existing mechanisms, enforce scoped read-only access, collect live drift/latency/resource/control-comparator measurements. Without it, only bounded offline security experiments may continue; do not imply production assurance. This evidence-only update is a new commit and must have its own remote hash and hosted CI verified after publication.

## 24. M8 upstream overlap and investment STOP checkpoint — local verification (2026-11-12)

**Intent:** User explicitly directed research-first continuation and requested that this product **not** be built merely for the sake of building. Recovered the existing 66-file M7 source from `runtime-assurance-lab-m7-verified.zip` in `/mnt/data/runtime-assurance-m8-work/runtime-assurance-lab` (no Git data was packaged in the zip). Checked the matching `PLAN.md`, `EVIDENCE.md` and `checkpoint_store.py` Git blob SHA-1 values against GitHub `main=bd8ed9ef06d4b5807ccd81df1ca64c8539cb6b7c`; all three exact hashes matched. No prior research milestone or live capability was invented. The other 63 blob hashes remain for final remote tree equality verification during publishing.

**Primary-source desk audit:** Inspected public pinned Google `k8s-aibom v1.6.2` README and upstream sources, NVIDIA `aicr v1.2.0` plus the official artifact verification and CLI reference, and Sigstore bundle/policy documentation. Source versions and links appear in `research/upstream_overlap.json`, `UPSTREAM_AUDIT.md`, and `PLAN.md` M8. NVIDIA's artifact/evidence verifier already supports closed-world inventory digests, Sigstore signatures, identity and creator restrictions, and signed recipe/snapshot/validator/BOM evidence. Its CLI documents that it does **not** replay inline constraints against the bundled snapshot; this is a *possible integration investigation*, not customer value. Google's controller already inventories Kubernetes AI workloads and offers verified signature confidence under trust roots and signer policies. Existing Sigstore/policy solutions already address signatures and trusted policy inputs. **No actual upstream binaries, live Kubernetes, authenticated source bundles or GPUs were run in this milestone.** Upstream source/doc review does not guarantee every provider capability, support tier or measured outcome.

**Decision and implementation:** Evaluated A) add new runtime controller/signing/rollback feature vs B) freeze new product features, preserve M1–M7, and enforce a repeatable falsification decision. Selected **B**. M5's *historical, claim-only synthetic* 600-case same-input independent reference comparator had **0 disagreements**, not an advantage over existing upstream software. Added `research/upstream_overlap.json`, `src/runtime_assurance_lab/research_gate.py`, `scripts/run_research_gate.py`, `tests/test_research_gate.py`, and `results/research_gate.json`; extended existing CPU GitHub Actions matrix to independently recompute the report. Updated `PLAN.md`, `EVIDENCE.md`, `DECISIONS.md`, `README.md`, `UPSTREAM_AUDIT.md`, `AGENTS.md`. No new runtime product behavior, signing protocol, dependency, cloud API, secrets or privileged service. `PAUSE_PRODUCT_BUILD` is a research **no-go until evidence**, not proof that the product can never provide value. No product launch/distribution approval.

**Actual commands/results in this local environment:**

```text
# Baseline recovered M7 source, with PYTHONPATH correctly available to subprocess tests:
PYTHONPATH=src python -m pytest -q -> 176 passed in 25.36s.
# One combined baseline command timed out after pytest; smoke was NOT inferred from it.
# Initial new gate tests:
PYTHONPATH=src python -m pytest -q tests/test_research_gate.py -> 20 passed in 4.66s.
# Added report duplicate-key, size-limit and spoofed-GO regressions:
PYTHONPATH=src python -m pytest -q tests/test_research_gate.py -> 23 passed in 8.05s.
# Complete modified source tree:
PYTHONPATH=src python -m pytest -q -> 199 passed in 30.32s.
PYTHONPATH=src python scripts/ci_smoke.py -> offline_smoke=pass, 14 named existing synthetic subprocess cases.
python scripts/check_gates.py -> passed=true, 7/7 STORED/HISTORICAL synthetic pilot gates (not a new M8 performance benchmark).
PYTHONPATH=src python scripts/run_research_gate.py --verify-report results/research_gate.json
  -> decision=PAUSE_PRODUCT_BUILD, report_matches=true, 4 missing independent gates.
python -m compileall -q src tests scripts -> PASS.
python3.11 --version -> not installed in the local shell; Python 3.11 must be verified on GitHub-hosted CI after publication.
python -m pip check -> pre-existing unrelated conflict moviepy 2.2.1 vs Pillow 12.3.0.
```

**Adversarial research-decision checks:** Reject missing/duplicated sources, missing citations, duplicate hypothesis identifiers, fabricated `PROVEN` hypothesis, contradictory historical input, fake claims of upstream binary execution/product differentiation, forged `OK` source probe, forged recorded GO decision, missing/duplicate-key/oversized report, and overwriting an existing report. Adding a caller's `product_go=true` does not make a research report an authorization. Input files and documentation remain **user-supplied claims**, not independently signed evidence. The script is a bounded reproducible research control and intentionally cannot auto-approve production from synthetic inputs.

**Resource use and investment:** Research gate uses standard Python library and existing project dependency; no additional packages, GPUs, cloud resources or paid runners; gate's own CPU/RSS not benchmarked. Existing historical M5/M7 resource numbers are unchanged and not reused as live measurements.

**Disposition/stop criterion:** `results/research_gate.json` says **`PAUSE_PRODUCT_BUILD`**. Four missing externally established conditions: authentic upstream evidence; independently anchored provenance/monotonic state; representative real AICR + k8s-aibom + Sigstore/policy comparison with controlled drift; customer-backed demonstrable value. If upstream tool composition proves equivalent performance/functionality, **stop the standalone system** and consider a small upstream contribution rather than duplicate products. G4 live testing and G5 commercialization still blocked. Next executable non-development action: obtain authorized redacted signed upstream artifacts and an independently operated test environment with pre-registered comparison protocol. Do not add another product subsystem in the meantime.

**Publication:** Local M8 documentation, code and tests are ready for an immutable Git snapshot; GitHub publication, exact all-file blob comparison and hosted Python 3.11/3.13 job results will be recorded in a subsequent evidence-only checkpoint. No production approval is implied by a green hosted CI run.


## 25. M8 public publication and GitHub-hosted validation (2026-11-12)

- **Starting GitHub checkpoint:** `bd8ed9ef06d4b5807ccd81df1ca64c8539cb6b7c` (M7). Re-verified the complete baseline against the connected GitHub API: **66/66 original Git blob SHA-1 hashes matched**, no remote-only files. Local M8 snapshot `dda5d90910ef18d3a59c03f541e26413c1ae8a0b` changed/added exactly 12 paths; no runtime subsystem, cluster controller, GPU dependency, paid runner, source credential, release or license was introduced.
- **Independent local rerun in the working environment:** `PYTHONPATH=src python -m pytest -q --durations=8` -> **199 passed in 34.00s**. An earlier foreground pytest command hit the execution wrapper's timeout after partial output; it is **not** counted as a complete pass. Separately executed `PYTHONPATH=src python scripts/ci_smoke.py` -> `offline_smoke=pass`, 14 named synthetic subprocess scenarios; `python scripts/check_gates.py` -> seven **stored/historical** synthetic pilot gates passed; `PYTHONPATH=src python scripts/run_research_gate.py --verify-report results/research_gate.json` -> `PAUSE_PRODUCT_BUILD` and `report_matches=true`; `python -m compileall -q src tests scripts` -> passed. Worktree remained clean.
- **Publication:** created an atomic GitHub Git tree `d4279c7c80247da820288716a43f188158428f90` on the existing remote base tree, compared **71/71** resulting tree-file Git SHA-1 blobs to the exact immutable local snapshot with **zero mismatches/extras**, and published GitHub `main` commit `87fb6031f19cf6c03f766b1022e6a1ae195ea50d` using non-force `update_ref` with an expected old-head lease. Re-read `main` and verified the commit/tree.
- **Hosted CI source commit:** [GitHub Actions 43227942102](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43227942102), exact head `87fb6031...`, completed **success**. Individually retrieved the hosted logs: **Python 3.11: 199 passed in 3.82s** and **Python 3.13: 199 passed in 3.32s**. Both matrix jobs passed module compilation, synthetic smoke, historical acceptance-report check, and independent research NO-GO report recomputation. Hosted CI proves reproducibility of the offline policy/report, **not** real upstream parity, independently measured customer value, protected source trust roots or GPU execution.
- **Investment conclusion:** `PAUSE_PRODUCT_BUILD` remains in force. All four independent gates are missing (authentic upstream evidence, external provenance/monotonic state, representative real controlled comparison, customer value validation). Synthetic M5 same-input comparator parity is **not** an NVIDIA/Google software head-to-head. Do not reinterpret green CI as a GO or resume standalone product development on the basis of these checks.
- **Remaining next action:** arrange authorized, redacted authentic signed AICR/AIBOM evidence and an independent upstream comparison/customer discovery protocol; if equivalent coverage is confirmed, stop the standalone product or propose a focused upstream contribution. This evidence-only update is a subsequent commit and needs its own remote tree equality and CI confirmation.

## 26. M9: major upstream-public-testdata falsification workstream (2026-11-12)

**Investment rule:** User requested larger integrated work blocks and explicitly instructed **not to build a redundant product**. The prior M8 NO-GO remains authoritative: `PAUSE_PRODUCT_BUILD`. M9 is a pre-G4 evidence/benchmark protocol, **not a new runtime service**. No prior M1–M8 evidence overwritten. G4/G5 stay BLOCKED.

**Upstream verification using connected GitHub, not locally run binaries:** GitHub's release API returned latest NVIDIA AICR v1.2.0 (published 2026-11-02) and Google k8s-aibom v1.6.2 (published 2026-10-22) as of this review. Git tag dereferencing and full upstream Git tree inspection established the exact immutable source paths/commits and 40-hex Git blob identities:

- Google `GoogleCloudPlatform/k8s-aibom@47bf6418e40eee22905973528b879dc075181b3f`, `internal/bom/testdata/golden/vllm-deployment-output.json`, blob SHA-1 `b708db2f5a67c2210d29e712a7dd4f8f59487635`, expected 6,387 bytes. Public first-party *golden BOM* is CycloneDX 1.6 for an inference Deployment. It includes a container image SHA-256 claim, two model component claims with locators and one distinct model identity. No live controller, signatures or external trust evidence.
- NVIDIA `NVIDIA/aicr@935e0746dc54da890a23c1ecca998244b3a25de7` (annotated v1.2.0 tag dereferenced), `pkg/operator/aicrjob/testdata/v1.1.2/recipe-h100-eks-ubuntu-training.json`, blob SHA-1 `7aefe761a870efcc7e74971b8a9d23b093f2918e`, expected 105,200 bytes. JSON `RecipeResult` / `aicr.run/v1` has 15 component refs and `training` criteria. `v1.1.2` names the checked-in fixture subdirectory, **not the upstream repository commit version**. Does not refer to Google's inference Deployment.

**Implemented work:** New bounded research-only module `src/runtime_assurance_lab/upstream_preflight.py`; explicit opt-in CLI `scripts/run_upstream_preflight.py`; independent, fully constructed local controls in `tests/test_upstream_preflight.py`; isolated read-only public-asset job in `.github/workflows/offline-assurance.yml`; substantial preregistration `research/g4_independent_validation_protocol.md`; updated `README.md`, `PLAN.md`, `DECISIONS.md`, `UPSTREAM_AUDIT.md` and this evidence ledger. Network reads restricted to two pinned public raw GitHub URLs with no redirects and 256 KiB cap; Git blob hashes checked, then strict JSON parsed. SHA-1 here identifies upstream published bytes, **not independently trusted signatures**. No local network allowed in this sandbox; official source assets will be *downloaded and actually parsed* only by the segregated hosted CI research job. Existing local tests mock fixed assets and source fetches without pretending to run upstream binaries.

**Substantive independent negative control:** Google upstream golden BOM already contains image-digest and model-source evidence, while RAL's summary-only AIBOM adapter does not promote the untrusted image digest. An AIBOM CR is constructed *locally* to probe adaptation; its `Ready` status is synthetic, not upstream-derived. NVIDIA's sample is a training recipe and Google's sample is an inference inventory: no authenticated workload join, no evidence of incremental detection or execution. The valid preflight outcome remains `PAUSE_PRODUCT_BUILD`. The G4 protocol fixes competitor parity, independent custody, randomized/blinded labels, negative evidence classes, end-to-end metrics and hard stop/kill rules before any live study.

**Actual local tests/debugging:**

```text
PYTHONPATH=src python -m pytest -q tests/test_upstream_preflight.py --disable-warnings --maxfail=1
# FIRST: 1 failure (test wrongly prohibited 'v1.' in a legitimate testdata subdirectory; fixed assertion to require exact pinned commit segment)
PYTHONPATH=src python -m pytest -q tests/test_upstream_preflight.py --disable-warnings --maxfail=2
# SECOND: 1 failure (two fake source pins had identical test URLs; fixed synthetic source names; not production source logic)
PYTHONPATH=src python -m pytest -q tests/test_upstream_preflight.py
# 27 passed in 3.22s
PYTHONPATH=src pytest -q --disable-warnings --durations=5
# timed out in the invocation wrapper partway through; NOT counted as pass
# Full verbose background run, process exit checked by its completed result file:
PYTHONPATH=src python -m pytest -vv --disable-warnings
# FINAL: 226 passed in 37.22s; exit code 0
PYTHONPATH=src python scripts/ci_smoke.py
# offline_smoke=pass, all 14 existing process-level checks
python scripts/check_gates.py
# passed=true, all 7 STORED/HISTORICAL synthetic pilot gates; not live benchmark
PYTHONPATH=src python scripts/run_research_gate.py --verify-report results/research_gate.json
# PAUSE_PRODUCT_BUILD, report_matches=true, four independent gates still missing
PYTHONPATH=src python scripts/run_upstream_preflight.py --list-pins
# two pinned upstream public source paths listed without network
python -m compileall -q src tests scripts
# completed without error
```

**Adversarial controls:** 27 new targeted tests cover exact-byte mutation even for semantically equivalent JSON, malformed/oversized/duplicate-key/nonfinite fixtures, schema/version invalidation, missing/extra provider data, missing/conflicting workload coordinates, malformed image hashes, suspicious model claims, recipe-version mismatch, duplicated components, missing trusted cross-plane binding, spoofed HTTP redirect/non-200 responses and source tampering. Positive control is synthetic and explicitly never authorizes authenticated runtime `OK`. The no-network CLI default is tested.

**Resource and scope:** No new Python package dependency, secrets, deployment, GPU, Kubernetes or production data. Local tests exercised fake constructed data; GitHub public network fetch is opt-in and isolated from existing offline matrix. No independent real signed AICR/k8s-aibom exports, actual provider binaries, resource measurements or customer validation. Git-hosted source parity job must pass before this milestone is called **hosted preflight verified**.

**Next actions:** Commit exact immutable local tree; publish using non-force expected GitHub head lease; verify all committed Git blob identities; inspect both Python versions plus public fixture fetch job; capture SHA-256 of actually fetched source data and reported overlap results in subsequent `EVIDENCE.md` checkpoint. If public test fixtures fail or change, preserve failure and audit against upstream before modifying pins. Do not update M8 NO-GO to GO based on public fixture checks alone.

## 27. M9 actual first public-data hosted job uncovered an adapter defect; correction and retest

**First published source:** GitHub commit `04a6dda6acb3aed936816109b4bf1174bc47a39b`; an atomic non-force update to former `main` `4a06b423db8e344f0184673fee2c27494a24e2a7`. Independently fetched the resulting tree `f28f43011acb307a76415fb9a953b0388d273338` and verified **75/75** tracked Git blob SHA identities match the immutable local M9 source snapshot with **no extras/mismatches**. Full test job run [43232685292](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43232685292): Python 3.11 and 3.13 **SUCCESS**, new upstream-public-fixture job **FAILED**. No premature claim of full hosted success.

**Actual upstream failure discovered:** The research job successfully fetched/verified both fixed upstream files, but `src/runtime_assurance_lab/aicr_adapter.py:pin_recipe` rejected NVIDIA's official RecipeResult with `componentRefs.source must be nonempty bounded string`. Inspected immutable AICR v1.2.0 public fixture directly through GitHub: two `Helm` components (`dra-node-labeler`, `nodewright-customizations`) have `source=""` and valid nonempty `manifestFiles`. Official upstream `RecipeResult.schema.json` lists `source` as a *required string*, but does **not** constrain it to nonempty; the prototype imposed an incompatible extra rule. This is concrete test-driven upstream compatibility correction, NOT product differentiation.

**Fix:** allow blank `source` only when that component supplies a bounded, nonempty list of local manifest-file paths; preserve rejection of missing/non-string source and empty, malformed or oversized manifest lists; label `AICR_LOCAL_MANIFEST_SOURCE_UNATTESTED` in limitations. No source fetch or file opening is introduced by the parser; no assurance promotion to `OK`. New positive official-shape regression plus seven negative controls in `tests/test_aicr_adapter.py`. Before M9 original local tests passed **199**; M9 first local all-suite **226 passed in 37.22s**; after correction, targeted AICR+upstream preflight suite **55 passed in 4.30s**. Full corrected-suite result and final hosted run will be appended in the next checkpoint after execution.

**Research decision unchanged:** Google and NVIDIA first-party fixtures remain distinct, synthetic, non-attested research inputs. Existing upstream tooling has genuine inventory/model/image evidence; our component-adapter mismatch is a liability, not novelty. M8 `PAUSE_PRODUCT_BUILD` remains in force. Authentic runtime/GPU evidence, independent source custody and fair head-to-head G4 remain blocked.

## 28. M9 interrupted publication recovered and independently verified (2026-11-12)

At user-requested continuation, read `PLAN.md` and `EVIDENCE.md`, inspected immutable local M9 repair commit `9be3b7f571a1fd67c4be1102841627a2b3f8bdfc` and GitHub `main`. M9 repair had **already** been published at `72dbb7323512035a55795184de270522179c470e`; avoid duplicate publication. Re-read all 75 remote Git blob SHA identities against the immutable M9 patch manifest: **75/75 matched, no extras/mismatches**. GitHub Actions run [43233446938](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43233446938) returned `completed/success` with **three successful jobs**. Downloaded actual hosted job logs: Python 3.11 **234 passed in 3.16s**, Python 3.13 **234 passed in 4.34s**, and public upstream fixture fetch/research job **success**; both Python jobs passed smoke and no-go gate. The third job actually fetched both pinned first-party public source files and validated hashes. **No live model/GPU execution and no original upstream binary invocation.** `PAUSE_PRODUCT_BUILD` remains authoritative. M9 repair is not outstanding.

## 29. M10 — offline, operator-controlled G4 evidence intake without product expansion (2026-11-12)

**Research/architecture decision:** NVIDIA AICR's own v1.2.0 artifact verification supports closed-world inventory/Sigstore/creator policy and minimized recipe-evidence bundles; Google k8s-aibom has its own runtime BOM, model confidence/source locators and `kubectl aibom verify` checks. Official Kubernetes RBAC allows namespace-scoped `get` restricted by `resourceNames`. See `research/g4_operator_handoff.md` and `UPSTREAM_AUDIT.md`. Compared adding another collector/signer (duplicate, not justified) to a bounded operator handoff for a future blinded G4 trial (selected). No product-runtime subsystem or automatic production data collector built.

**Implementation:** `src/runtime_assurance_lab/g4_handoff.py` with `scripts/run_g4_handoff.py` require untrusted but bounded raw intent/AICR RecipeResult/AIBOM CR JSON plus three independently *supplied* exact SHA-256 byte pins. They reuse strict JSON parser, version-pinned AICR adapter and AIBOM adapter, and reject digest or schema problems and contradictory workload/model/category claims. No attached signature, source-provided `verified` flag or user-provided pin can grant an authenticated result. Report intentionally omits names/values and always states `g4_authorized=false`, `authentic_upstream_provenance_verified=false` and `decision=PAUSE_PRODUCT_BUILD`. CLI returns **2 for matching but unauthenticated** and **3 for invalid/unreadable** inputs, never 0. Inputs read via size-bounded regular-file check that rejects final-path symlinks and FIFOs; `--output` only creates new `0600` reports. Report hashes are operational metadata and may require restricted handling.

**Test/fixture scope:** `tests/test_g4_handoff.py` covers raw pin tampering across all three inputs, canonical reformat mutation, oversized and blank inputs, duplicate keys, exponent overflow, nonfinite JSON, wrong schema, model/workload/category conflicts, missing Ready condition, self-asserted verified model and attacker-mutated pins, repeat handoff, CLI nonzero exit, source and destination symlink attacks, FIFO nonhang, no secret-name echo, exclusive report output. `results/g4_handoff_synthetic.json` is a reproducible synthetic structural record, **not** real G4 proof. `scripts/ci_smoke.py` adds two process-level cases (matching synthetic no-go and spoofed external pin refusal). `scripts/bench_g4_handoff.py` measures only preloaded synthetic parser/integrity checks, not upstream verifier time or workload detection.

**First target debugging:** first targeted run **2 failed / 26 passed** (test expected literal pretty-printed report to equal compact stdout; second test incorrectly expected a structurally valid but changed operator-supplied model name to be invalid rather than unauthenticated). Corrected test assertions, preserving both security invariants; targeted **28 passed**. Added explicit model-identity/category conflicts and 3 more filesystem/replay checks, then targeted **35 passed**. First full-suite combined shell call exceeded invocation timeout partway through and was **not** counted. Reran full pytest through a waited-for process with an explicit recorded exit code: **266 passed in 43.40s, exit 0** at the intermediate 32-case checkpoint; complete final result below reflects subsequent 3 tests.

**Microbenchmark (not a release gate):** `PYTHONPATH=src python scripts/bench_g4_handoff.py --samples 200 --output results/g4_handoff_benchmark.json` on synthetic preloaded fixture bytes: p50 **551.186 μs**, p95 **1,350.730 μs**, max **3,546.625 μs**; process CPU **135.917 ms** for 200 repeated inspections, traced Python heap peak **49,154 bytes**. Excludes file reads, cryptographic trust roots, upstream validation, Kubernetes, GPU, network, disk persistence or real detection delay. Comparing to old isolated microbenchmarks would be misleading.

**STOP/NO-GO remains unchanged:** No authentic signed AICR/AIBOM pair from the SAME verified workload, independent trust root, externally held monotonic checkpoint/time, instrumented cluster, independent blinded comparison or customer validation. A successful handoff **cannot** unblock G4/G5 or justify a standalone product. Next dependent action is obtaining a separately authorized and protected real evidence handoff, then applying vendor-native verifier under the preregistered G4 comparator protocol. No production data, credentials, secrets, cloud spend or cluster access used.

**Final local M10 verification and resource record (after the last new tests):**

```text
PYTHONPATH=src python -m pytest -q
# FINAL 269 passed in 51.64s; exit=0 (captured completed process, not truncated timed-out call)
PYTHONPATH=src python -m pytest -q tests/test_g4_handoff.py
# 35 passed in 11.41s
PYTHONPATH=src python scripts/ci_smoke.py
# offline_smoke=pass; 16 named process-level synthetic scenarios
python scripts/check_gates.py
# passed=true, 7/7 STORED historical synthetic gates (no benchmark rerun)
PYTHONPATH=src python scripts/run_research_gate.py --verify-report results/research_gate.json
# PAUSE_PRODUCT_BUILD; report_matches=true; four independent research gates still missing
python -m compileall -q src tests scripts
# passed
```

The combined shell invocation containing a trailing `python -m pip check` timed out **after** it had printed smoke/gate/research/compile successes; do not infer any completed `pip check` outcome from that invocation. No Python 3.11 local runtime was available; both versions are to be checked on hosted GitHub CI. External independent adversarial review was not available; tests are self-review only. The README, plan, and security review explicitly preserve M1–M9 and the M8 NO-GO. Do not publish actual private exports with this research source commit.

**Local dependency environment check:** A separate `timeout 8s python -m pip check` completed and reported the existing unrelated environment conflict `moviepy 2.2.1 requires pillow<12.0,>=9.2.0; installed Pillow 12.3.0` (no new dependency was installed by M10). Thus the global environment `pip check` is **not clean**, and this is not treated as a runtime-assurance-lab test failure. `git diff --check` passed.

## 30. M10 published source verified on GitHub and real hosted CPU CI (2026-11-12)

- Immutable local source commit `40b411098d9db24d31b32deb0712318b2e891604`: **15 changed/new text files**, **82 total tracked files** (no third-party/vendor payloads copied; repository remains public and unlicensed). Source commit publication used GitHub `main` old head `72dbb7323512035a55795184de270522179c470e` and a conditional non-force ref update, yielding remote source commit **`8b8b0a1e3bf4dc95c015df320cf2cc845d4c8cd8`**. Compared immutable local `HEAD:<path>` blob hashes to the newly created GitHub tree `d0f1e53fdd7645b684dc4e860ec2193f2bca97ec`: **82/82 Git blob SHA matches, zero extras/mismatches**. The source code was not sent from a mutable working tree.
- Actual hosted GitHub Actions run [43238958517](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43238958517), exact source head `8b8b0a1e...`: `status=completed`, `conclusion=success`. Downloaded per-job logs: **Python 3.11: 269 passed in 3.75s**; **Python 3.13: 269 passed in 4.10s**. Both CPU-only jobs also passed compilation, **16 named process smoke checks**, **7/7 historical stored synthetic acceptance gates**, and the recorded `PAUSE_PRODUCT_BUILD` research-report check. The isolated public-NVIDIA/Google-fixture preflight job completed successfully; its own report confirms `upstream_binaries_executed=false`, `cross_plane_link_verified=false` and **no authenticated runtime assurance**. No NVIDIA/Google binary was invoked in the research job and no cluster was contacted.
- **Resource use:** source verification benchmark above is a local synthetic preloaded microbenchmark; actual GitHub job CPU/RSS was not collected. Hosted workflow operated on standard GitHub CPU runners, no GPU, paid services, production credentials or Kubernetes RBAC use. The old `pip check` warning stems from an unrelated pre-existing `moviepy`/`pillow` global environment conflict.
- **Security caution:** 35 new adversarial/unit tests plus 16 smoke checks establish only a fail-closed local preflight contract. They do **not** independently verify source signatures, producer keys, actual inference execution, protected intent/checkpoints or trustworthy source time. Source SHA-256 comparison is not signer authentication and a locally constructed structural record is not a real AIBOM CR. The tool has no `GO`/trusted-switch path. No independent external security reviewer was available. User's investment constraint remains: **DO NOT expand the product** while value over upstream composition remains unverified.
- This paragraph is an evidence-only follow-up commit; the published source was verified separately. Next permitted action, **not executable without operator-authorized evidence**: obtain a legally shareable, minimally redacted same-workload signed AICR bundle/RecipeResult and AIBOM CR; use vendor-native signature verification with independently pinned creator/root/time and externally controlled checkpoint, then execute blinded equal-input G4 head-to-head under `research/g4_independent_validation_protocol.md`. Otherwise continue `PAUSE_PRODUCT_BUILD` and avoid new product features. G4/G5 blocked.

## 31. G4 environment discovery and new real-vendor CPU baseline (2026-11-12)

**Operator request:** finish as much of G4 as is verifiable, without inventing a live cluster or ignoring the explicit M8 investment stop. The M10 GitHub `main` `b8d53b97f858b1149ff28fccaf4e702dee6f42af` matched the local code/docs checkpoint. Examined `PLAN.md`, `EVIDENCE.md`, current workflow, G4 preregistration and original native-upstream repository tags.

**Environment:** local Python 3.13.5, Go 1.23.2; no `kubectl`, Docker, Podman, kind, cosign, Helm, NVIDIA GPU devices or visible Kubernetes credentials. The local runtime cannot resolve public HTTPS hosts. Local code cannot execute G4's actual Kubernetes/GPU workload or download vendor release assets. Standard GitHub-hosted runners *can* run public vendor binaries without requiring user credentials or paid GPU service.

**Independent version/resource check:** NVIDIA AICR `v1.2.0` release metadata lists `aicr_1.2.0_linux_amd64.tar.gz`, SHA-256 `3ff6935fd7988373903a2a30f1c24a74a5f8a9052a310615db19fcfec4cfe9a2` (~27.8MB). Google `k8s-aibom v1.6.2` release lists `kubectl-aibom_v1.6.2_linux_amd64.tar.gz`, SHA-256 `5a7f7e98e55d59ce3f7e5fa9ce385b544775ddefd32bcdf20b6e9fc234b2a7c0` (~8.5MB) and `kubectl-aibom_v1.6.2.provenance.intoto.jsonl`, SHA-256 `a90db7b45bd48ae6663d48494287b11a6b6bd0339a338de3a2eca891209a62f8`. These hashes were fetched from exact official GitHub release asset metadata, not generated by this prototype. Google documents independently checking release provenance with `gh attestation verify`.

**Important upstream overlap:** NVIDIA AICR already offers `aicr verify` for closed-world deployment bundles, `aicr evidence verify` for signed recipe-evidence bundles, and signer/issuer constraints. Google k8s-aibom has `verified` model confidence constrained by operator roots/signers and native `kubectl aibom verify`/`find` commands; its NVIDIA AICR qualification already exists. A separate inventory/signature verification product has no demonstrated incremental benefit. Only one bounded **actual vendor binary** CPU baseline was approved. See `research/g4_vendor_native_baseline.md` and `UPSTREAM_AUDIT.md`. Source authenticity of a vendor release is still not a runtime execution witness.

**Implementation:** `scripts/g4_vendor_native_baseline.py`, `tests/test_g4_vendor_native_baseline.py` and path-scoped `.github/workflows/native-upstream-baseline.yml`; strict HTTPS, SHA-256/size caps, symlink and extraction guardrails, independent Google GitHub attestation and actual NVIDIA catalog verifier invocation, `PAUSE_PRODUCT_BUILD` output. The Google CLI help is only a smoke invocation, not a BOM verification; AICR release tar checksum pin alone is not a publisher-signature proof. No new product dependency or runtime feature. This stage **cannot** satisfy G4 or G5.

**Verification:** new targeted adversarial tests **12 passed** locally. Initial full pytest invocation exceeded the command runner's execution timeout, with no reported assertion failures before termination; a second verbose run showed progress through 61% and a known FIFO/rejection subprocess, but it too did not finish within the invocation window. Those attempts are NOT counted as passes. The full suite and hosted tests must be reported from their completed exit codes, not inferred. The next research step is the version-pinned native vendor job; a successful vendor release trust check must not be presented as a cross-plane workload or GPU test.


### M11 first vendor-native hosted failure and compatibility correction

Initial GitHub workflow run [43243414648](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43243414648) **FAILED**, as designed, at the native NVIDIA command: `aicr recipe verify-catalog` (exit 2) reports usage `aicr recipe verify-catalog <bundle-path>`. This was a test-harness invocation error, not an upstream signature failure or evidence of product value. The ordinary GitHub offline suite on the same source commit [43243414753](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43243414753) passed all three jobs (Python 3.11/3.13 and pinned upstream public fixtures). Do not conceal the failure or describe the incomplete vendor baseline as successful.

Confirmed the pinned v1.2.0 CLI reference requires the separately downloaded `recipe-catalog.sigstore.json` release asset. GitHub release metadata gives its SHA-256 `80744565b8d79da72afc0720dc551e9664eb91e1d94da90c1fad1ba65d8802cc`. Corrected the harness to checksum-pin the fourth asset and pass its local pathname to the vendor binary. Retest and hosted verification are recorded separately; these fixes do not alter `PAUSE_PRODUCT_BUILD` or unblock the missing live GPU/workload source evidence.

## 32. First successful actual upstream-native verification on GitHub (2026-11-12)

The corrected source commit `57d41f3b9a2a7c525d6d19a6ab558aac69d3ae12` passed real GitHub-hosted [vendor-native CPU run 43244660419](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43244660419), `status=completed`, `conclusion=success`. The decoded job log was inspected and returned explicit `VENDOR_NATIVE_CPU_BASELINE_PASS__G4_STILL_BLOCKED`. Four release assets from the exact NVIDIA AICR v1.2.0 / Google k8s-aibom v1.6.2 releases matched individually pinned SHA-256 checks before extraction/execution. The actual published tools and independent attestation verifier reported exit 0:

- Google `gh attestation verify <kubectl-aibom-linux-archive> --owner GoogleCloudPlatform --bundle <release-provenance.jsonl>`: **PASS** (publisher provenance for CLI archive only).
- NVIDIA released Linux `aicr recipe verify-catalog <recipe-catalog.sigstore.json>`: **PASS** (vendor's Sigstore check for its embedded recipe catalogue, not runtime model/cluster).
- Google released `kubectl-aibom --help`: **PASS** (binary invoked, no Kubernetes API, no BOM or model verification).

The output recorded `actual_kubernetes_cluster_connected=false`, `gpu_execution_verified=false`, `same_workload_upstream_evidence=false`, `cross_plane_link_verified=false`, `g4_completed=false`, `g5_completed=false` and `decision=PAUSE_PRODUCT_BUILD`. This status is an **honest negative finding**, not a product delivery failure. Vendor binary SHA pins and its native verification do not by themselves authenticate a deployment, model execution, independent operator intent, or an actual AIBOM CR. The NVIDIA release binary itself was not independently publisher-attested; its catalogue verifier ran with an independently release-pinned Sigstore catalogue bundle. The successful job made public HTTPS downloads only; no cluster credentials, GPU, paid runner or service were used. `results/g4_vendor_native_cpu.json` records the successful hosted observations and citation to the logs, with the source type narrowed to reflect partial—not comprehensive—signed release metadata. Original signed log remains the authoritative execution record.

For the earlier failed first attempt see section 31: native AICR command was initially invoked without its required signed catalogue bundle; we fixed it, added a test checking the exact command contract and reran. The initial failure is preserved rather than erased.

**Scope and investment stop:** M1–M10 remain verified historical research work. The bounded native upstream release experiment is now complete, not G4. Without an independently trusted *same-workload* AICR evidence bundle and Google AIBOM export, a read-only authorized multi-class/multi-topology Kubernetes/GPU experiment, blinded labels and customer value observations, the preregistered G4/G5 gates are **not executable or complete**. In particular, Google CLI help proves no AIBOM verification; NVIDIA catalog verification is not `aicr evidence verify` on real model evidence. No extra product features should be started. Preserve `PAUSE_PRODUCT_BUILD`. A next externally dependent action is to obtain a trustworthy redacted same-workload evidence pair and independent trust/clock/checkpoint authority; if those cannot be provided, **stop standalone product development** rather than continue on synthetic features.

The source-type description in the recorded result was intentionally narrowed before final evidence publication. The adjusted script and result are separately checked in the complete Python CI suite; final hosted CI SHA/results are appended after GitHub publication. No historical benchmark is reinterpreted as GPU detection latency.

## 33. Final M11 native-G4 CPU research checkout and hosted CI (2026-11-12)

The following observations were verified from GitHub-hosted execution logs for the **source/report commit** `20155a3de5e7058fd4f505b45350069569bcf0f4`:

- [GitHub Actions offline assurance 43245586941](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43245586941): `completed/success`, Python **3.11: 283 passed in 4.30s**, Python **3.13: 283 passed in 4.82s**. Both passed offline process smoke, stored 7/7 historical synthetic gates, and the `PAUSE_PRODUCT_BUILD` research gate. The third job downloading/checking pinned public NVIDIA/Google **repository test fixtures** also passed; it did not execute a cluster or source authentication service.
- [Vendor-native run 43245586438](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43245586438): `completed/success`. From actual job output: four release assets passed exact SHA-256 checks; Google `gh attestation verify --owner GoogleCloudPlatform` **exit 0**, NVIDIA `aicr recipe verify-catalog <release-pinned-sigstore-bundle>` **exit 0**, Google `kubectl-aibom --help` **exit 0**; `VENDOR_NATIVE_CPU_BASELINE_PASS__G4_STILL_BLOCKED`. This invokes genuine published vendor executables. It does not invoke `kubectl aibom verify` against a cluster or NVIDIA `aicr evidence verify` against a matching real workload bundle, and it cannot imply genuine runtime model execution.
- Before publication, immutable local source commit `f51b3787b14ee6c8662ddd4eb8df3caabcc2db0f` was packaged into two bounded JSON transport chunks from Git committed bytes, and remote Git tree `5b917ec095539e1973eb23097537b9f0d6dff964` was independently fetched and checked against **87/87 exact committed Git object hashes, zero mismatches, zero extras**. GitHub `main` was moved by conditional non-force update to source/report commit `20155a3...`. No cluster, secrets, GPU, paid runner, production deployment or license grant used.
- **Local verification:** the final new pinned-native/provenance tests passed **14/14**, and Python compileall, `git diff --check`, 7/7 historical stored gates and the `PAUSE_PRODUCT_BUILD` report recomputation passed. Attempts to execute the complete legacy local suite exceeded the local command runner's time limit; they were not called passes. Both independent GitHub-hosted complete suites reported completed exit 0, 283 tests per version.
- Resource disclosure: downloads limited to four GitHub-hosted release assets (NVIDIA AICR archive ~27.8MB, Google CLI archive ~8.5MB, two Sigstore/attestation JSON files ~10–11KB each) plus the program's read-only Python checks. GitHub Actions job runner CPU/RSS and any Kubernetes/GPU runtime resource use were not measured; only standard CPU runner success was observed. No customer behavior, financial case or production feasibility was validated.

**STOP/NO-GO remains:** Existing NVIDIA AICR and Google k8s-aibom already cover substantial signing, recipe and runtime inventory work. The verified public vendor release checks cannot decide whether there is a commercially meaningful distinct cross-plane detection product. **Do not build further product features without the preregistered G4 real same-workload, separately authenticated, blinded, equal-input comparison and credible user demand.** The current research investment decision remains `PAUSE_PRODUCT_BUILD`; G4 and G5 are not completed. Next executable step depends on an external owner providing an authorized redacted authentic same-workload AICR evidence bundle and k8s-aibom CR, independent trust/clock/checkpoint and scoped cluster test access. If that is unavailable, discontinue standalone product expansion instead of pretending to complete G4 from public test assets.

The final evidence-only GitHub commit and hosted follow-up, if created, will be verified independently; this section describes the already verified source/report SHA and test runs, not a future unobserved result.

## 34. Open-source community readiness audit (2026-11-12; verification pending)

- Repo owner explicitly requested a permissively licensed, contributor-ready public repository, removal of nonessential clutter, and launch-appropriate README. Existing repo was public but lacked a license. Independently verified NVIDIA AICR and Google k8s-aibom are **Apache-2.0**. Selected the same OSI-approved license for original owner-licensable code, with unmodified standard LICENSE and an explicit NOTICE. PyCA `cryptography` runtime dependency declares `Apache-2.0 OR BSD-3-Clause`, pytest and setuptools test/build dependencies declare MIT in locally installed package metadata; all remain under **their own** licenses and are NOT vendored. No formal whole-transitive-chain legal opinion was obtained.
- Cleanup rule: remove only reproducible *self-signed synthetic demo outputs* `results/demo/{checkpoint,findings,journal,trust-public}.json`; preserve fixtures and all benchmark/negative-control/security logs and audits. The demo is regenerated with `ral demo --fixtures fixtures --output <temporary-directory>`. Exclude future demo outputs in `.gitignore`. Do not erase history in `EVIDENCE.md`.
- Public surface: concise README with explicit `PAUSE_PRODUCT_BUILD`, tested quickstart, truthful trust-boundary diagram and contributor paths; Apache-2.0 metadata in `pyproject.toml`; LICENSE, NOTICE, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, docs/ARCHITECTURE, docs/ROADMAP, GitHub issue forms and PR template. `AGENTS.md` licensing statement and previous D-006 superseded explicitly in DECISIONS. No CI privileges, GPU, release or deployment change.
- **Verification and publication results:** append exact local commands, hosted Python matrix / source-tree hashes / metadata evidence below once independently completed; this section does NOT pre-claim success.
- **Remaining blockers:** source code open source ≠ production-ready. Independently attested same-workload evidence, upstream equal-input G4 comparison, issuer/root/checkpoint custody, external security review, true runtime measurement, customer interest and market differentiation are unproven. Research investment gate stays `PAUSE_PRODUCT_BUILD`. Do not promise contributor participation or production support.

## 35. Published Apache-2.0 community checkpoint verified (2026-11-12)

- **Exact published source:** remote public `ZX7-Labs/runtime-assurance-lab` main commit `a4866e40e28c6e72deab071f2d43dae8a8dd457c`, derived by conditional non-force advancement from `da7a6e8545491c8fb6ea4300f970608f4ffce5fd`. GitHub remote tree `74fa7190aa28dff8879aec7d666901733e2393f2` independently compared with immutable local Git commit `06acc8c772f531490ab2f4811c311c3f1a62f116`: **96/96 tracked file Git blob SHA-1 matches, 0 extras/mismatches**. Four generated demo files removed from tracking; they can be regenerated with `ral demo` and are ignored. No research results, tests or security findings removed.
- GitHub REST repository metadata returned **`license.spdx_id=Apache-2.0`** after commit publication. Root LICENSE is complete Apache License Version 2.0; NOTICE identifies the independent project; `pyproject.toml` declares PEP 639 `license = "Apache-2.0"`, with `license-files = ["LICENSE", "NOTICE"]`. This applies only to original code the owner has rights to license; third-party dependencies and upstream code keep their own terms. **No legal audit or vendor endorsement.**
- Hosted [GitHub Actions run 43251628196](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43251628196) on this exact source SHA: `completed/success`, with **Python 3.11: 299 passed in 3.74s**, **Python 3.13: 299 passed in 4.31s**. Both jobs passed module compilation, 16 synthetic subprocess smoke checks, 7/7 *stored historical* research acceptance gates and the `PAUSE_PRODUCT_BUILD` report check; the third pinned-public-NVIDIA/Google-fixture CI job passed. No GPU, cluster, issuer-root custody or live data.
- **Local verification:** 299 tests all passed in three nonoverlapping pytest groups (`115 in 25.18s`, `99 in 21.83s`, `85 in 13.93s`); `16` new community metadata tests. `python scripts/ci_smoke.py` passed 16 scenarios; `python scripts/check_gates.py` reported 7/7 historical stored passes; `python scripts/run_research_gate.py --verify-report results/research_gate.json` returned `PAUSE_PRODUCT_BUILD` and exact report match; `python -m compileall -q src tests scripts` passed. `ral demo` and `ral verify` were rerun from synthetic fixtures in a temp directory with `{"verified":true,"reason":"DECISIONS_RECOMPUTED"}`. GitHub issue-form YAML parsed and required fields were checked, and local documentation links resolved. `git diff --check` and a limited high-confidence added-secret-pattern scan found no errors/matches (not an exhaustive audit).
- **Local environment caveat:** a monolithic local pytest and an optional local `pip wheel --no-build-isolation` attempt timed out. Full pytest was then successfully covered by disjoint groups, and the exact source passed complete hosted 3.11/3.13 suites plus editable package installation; **a distribution wheel build has not been independently verified**. No PyPI package or GitHub Release was created.
- **Actual contributor entrypoints:** [#1 reproducibility](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/1), [#2 upstream overlap](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/2), [#3 safe threat-model review](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/3). No one has agreed to maintain or fund the project; participation is not guaranteed.
- **Research investment decision unchanged:** `PAUSE_PRODUCT_BUILD`. This publication makes the code legally reusable and contributions possible, but does not establish production readiness, live-G4 or G5 evidence, operational resource use, customers, or a novel capability. Future work should obtain independent same-workload G4 evidence and credible users, otherwise prefer focused upstream contributions.

## Open-source independent-review recruitment checkpoint (2026-11-12)

**Scope:** contributor discovery, reproducibility, and evidence collection only. No runtime implementation, security policy, signed-source trust, GPU/cluster access, or product GO decision changed. This work is **not** independent review or proof of market demand.

- Re-read public GitHub `main` at `daf5a87ada4ad5ac754f4c63ae82697e6c3a8d2f`, the Apache-2.0 README, CONTRIBUTING.md, governance/security documents and three existing issues. The local source base was the previously verified 96-file open-source ZIP.
- Marked [#1](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/1) `good first issue` / `documentation`, [#2](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/2) `help wanted` / `question`, and [#3](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/3) `help wanted`. The GitHub API reported the applied label lists.
- Opened [#4](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/4), a distinct **privacy-safe independent G4 research partner** coordination issue (not a data-upload portal); no real evidence or credentials are requested publicly.
- Added `research/INDEPENDENT_REVIEW_CHALLENGE.md` with four lanes (portability, fair same-input upstream falsification, responsible security review, potential real G4 operators), a CPU-only quickstart, reproducibility and acceptance rubric, security/reporting boundaries and explicit commercial stop criteria. Linked it from `README.md`, `CONTRIBUTING.md`, and `docs/ROADMAP.md`. Added two documentation contract tests to `tests/test_community_metadata.py`. No external contractor, adopter, reviewer or actual operator has been verified yet.

**Local commands and verified results:**

```sh
PYTHONPATH=src python -m pytest -q
# 301 passed in 32.32s (Python 3.13, CPU-only; 299 earlier + 2 new doc tests)
python -m pytest -q tests/test_community_metadata.py
# 18 passed in 0.08s
PYTHONPATH=src python scripts/ci_smoke.py
# offline_smoke=pass, 16 named synthetic subprocess scenarios
python scripts/check_gates.py
# passed=true, 7/7 STORED historical synthetic gates, NOT new real measurements
python scripts/run_research_gate.py --verify-report results/research_gate.json
# initial shell without installed package or PYTHONPATH: ModuleNotFoundError (environment invocation error)
PYTHONPATH=src python scripts/run_research_gate.py --verify-report results/research_gate.json
# decision=PAUSE_PRODUCT_BUILD, report_matches=true
python -m compileall -q src tests scripts
# success, exit 0
# Verified relative links in four contributor-facing docs: 36 checked, 0 missing.
```

**G4/G5 unchanged:** No independent source/authenticated same-workload AICR/AIBOM evidence, protected trust roots, authorized Kubernetes/GPU testing, external security sign-off or customer proof. An issue invitation is not adoption; a CI green check is not a real workload attestation. Publishing this change must be followed by a whole-tree Git blob comparison and hosted Python 3.11/3.13 CI results before calling it a verified public checkpoint.
