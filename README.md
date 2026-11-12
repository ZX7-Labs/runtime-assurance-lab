# runtime-assurance-lab

Publicly accessible, unlicensed research checkpoint for correlated AI deployment-intent/runtime-observation drift, with signed **synthetic** evidence lineage. Not a Kubernetes controller, not a Sigstore replacement, and not production-ready.

## Run without network, GPU, Docker, Kubernetes or secret access

Requires Python >=3.11 and local `cryptography>=42,<48` (tested 46.0.4); tests use pytest 9.0.2. In the provided runtime these are already installed. No automatic downloads are performed.

```sh
cd runtime-assurance-lab
PYTHONPATH=src python -m runtime_assurance_lab.cli demo --fixtures fixtures --output results/demo
PYTHONPATH=src python -m runtime_assurance_lab.cli verify --journal results/demo/journal.json --trust results/demo/trust-public.json --checkpoint results/demo/checkpoint.json
PYTHONPATH=src python -m runtime_assurance_lab.cli evaluate --intent fixtures/intent.json --observation fixtures/clean.json --now 2026-11-12T03:25:00Z
PYTHONPATH=src python -m runtime_assurance_lab.cli evaluate-aibom --intent fixtures/intent.json --aibom fixtures/aibom-v1beta1-synthetic.json --now 2026-11-12T03:25:00Z
PYTHONPATH=src python -m runtime_assurance_lab.cli correlate-offline --intent fixtures/intent-aicr-synthetic.json --recipe fixtures/aicr-recipe-result-synthetic.json --expected-recipe-sha256 sha256:a44787410b9f5f8e7c60df82007639c11b90bacff731cf75ad9ad0681305febb --aibom fixtures/aibom-v1beta1-synthetic.json --now 2026-11-12T03:25:00Z
PYTHONPATH=src python scripts/bench_aicr_recipe.py
# Write a new reproducible offline receipt (exit 0 means written, NOT assurance OK):
PYTHONPATH=src python -m runtime_assurance_lab.cli receipt-offline --intent fixtures/intent-aicr-synthetic.json --recipe fixtures/aicr-recipe-result-synthetic.json --expected-recipe-sha256 sha256:a44787410b9f5f8e7c60df82007639c11b90bacff731cf75ad9ad0681305febb --aibom fixtures/aibom-v1beta1-synthetic.json --now 2026-11-12T03:25:00Z --output /tmp/ral-receipt.json
# Replay independently from the original files + separately supplied pin and clock:
PYTHONPATH=src python -m runtime_assurance_lab.cli replay-offline --intent fixtures/intent-aicr-synthetic.json --recipe fixtures/aicr-recipe-result-synthetic.json --expected-recipe-sha256 sha256:a44787410b9f5f8e7c60df82007639c11b90bacff731cf75ad9ad0681305febb --aibom fixtures/aibom-v1beta1-synthetic.json --now 2026-11-12T03:25:00Z --receipt /tmp/ral-receipt.json
PYTHONPATH=src python scripts/bench_crossplane_receipt.py
PYTHONPATH=src python scripts/bench_incremental_value.py --output /tmp/ral-claim-only-control.json
PYTHONPATH=src python scripts/bench_source_auth.py --output /tmp/ral-source-auth-benchmark.json
PYTHONPATH=src python -m runtime_assurance_lab.cli benchmark --output results/benchmark.json
PYTHONPATH=src pytest -q
```

`evaluate-aibom` is an offline, **version-pinned** Google k8s-aibom `v1.6.2` AIBOM/v1beta1 JSON adapter, with a **synthetic** CR sample. It performs no Kubernetes API calls, rejects inconsistent input, leaves unavailable digests null and intentionally returns `UNKNOWN`/exit 2 for the sample. The AIBOM summary alone is not a cryptographically trusted runtime attestation.

`correlate-offline` binds exact bytes of a **synthetic** NVIDIA AICR `v1.2.0` resolved `RecipeResult` JSON file to the caller's claimed SHA-256 and normalized intent, then compares a **synthetic** Google AIBOM v1beta1 record. The example deliberately returns `UNKNOWN`/exit 2: neither the pin nor CR is independently authenticated, and no GPU deployment or model execution is verified. It does not parse YAML, fetch records, run AICR, or use Kubernetes. Run with a separately established trusted pin only in a future authorized integration.

`receipt-offline` reports its independently replayable **synthetic** receipt with source byte SHA-256, policy, unknown decision and explicit limitations; it refuses to overwrite any existing file. `replay-offline` re-evaluates raw inputs, externally supplied clock and recipe pin, returning `verified_replay=true` only for an exact replay. Neither operation signs, authenticates or externally anchors source evidence. They are not live NVIDIA/Google integrations or a substitute for Sigstore verification.

`bench_incremental_value.py` is a **historical claim-only offline falsification/negative-control experiment**. It uses labeled synthetic hidden-drift conditions and a separately coded **same-input** reference comparator. The study reports 100% observable-condition drift recall but lower latent-drift recall when evidence is missing/stale/future, and zero incremental signal versus the same-input reference policy. `results/incremental_value.json` preserves the original M5 **unsafe `OK`** forgery finding. The post-gate run (`results/incremental_value_post_gate.json`) tests the fail-closed public entrypoint and reports `UNKNOWN`; historic visible/latent drift numbers apply only to *claimed* observation data, not authenticated detections. This is **not an upstream benchmark or market validation**; the weak naive comparator is intentionally not competitive.

`evaluate` is now *untrusted by default*: a complete synthetic match or mismatch returns `UNKNOWN/SOURCE_AUTHENTICITY_UNVERIFIED` (exit 2), not `OK` or authenticated `DRIFT`. The policy version is `ral-intent-observation-v2-provenance-gate`; prior recorded policy-v1 verdicts are historical. `evaluate-authenticated` returns exit 0 on synthetically authentic, scoped signed-source agreement only after verifying exact observation bytes, external intent/authority digest pins, signature, source/workload identity, clock, sequence and previous-head anchor. A successful result includes a proposed `next_checkpoint` that an independently operated durable store must atomically protect. Without that independent checkpoint and trust-root custody, **even the signed example is not production assurance**. `verify` exits 0 only if cryptographic *and* semantic proof checks succeed. `demo` uses ephemeral generated signers (no private keys written). Do not treat the colocated output public keys/checkpoint as an independent trust anchor.

### M6: source-forgery containment (offline only)

`src/runtime_assurance_lab/source_auth.py` validates a domain-separated detached Ed25519 envelope on a normalized observation. The CLI command `evaluate-authenticated` requires **all** of `--intent`, `--observation`, `--attestation`, `--authority`, `--expected-intent-sha256`, `--expected-authority-sha256`, `--expected-sequence`, `--expected-prev-head` and `--now`. The intent/root hashes and prior checkpoint **must be established independently** of the untrusted source and persisted by a trusted owner. The verifier does not infer or create these anchors and does not fetch remote credentials. See `PLAN.md` M6 and `SECURITY_REVIEW.md` for attack results and a competing external-transparency design. `scripts/bench_source_auth.py` benchmarks synthetic preloaded cryptographic processing, not real runtime attestation.

This is not a Sigstore-compatible signature format. Source-authenticated `OK` indicates *authorized collector statement matches pinned intent* only; model execution and independently verified upstream publisher identities remain unproven. A compromised authorized source can lie.

- `AGENTS.md`: guardrails for future agents.
- `PLAN.md` / `DECISIONS.md`: hypothesis, two competing architectures, scope and acceptance gates.
- `UPSTREAM_AUDIT.md`: current official-project capabilities, licenses, integration points and sources.
- `SECURITY_REVIEW.md`: explicit critical review and surviving vulnerabilities.
- `EVIDENCE.md`: executed commands/results and blockers, without claims of live validation.
- `results/`: machine-readable example output and benchmark, including an offline synthetic AIBOM adapter processing baseline (`python scripts/bench_aibom_adapter.py`).

## Public GitHub Actions — offline test automation

`.github/workflows/offline-assurance.yml` runs on pushes to `main`, pull requests, and manual dispatch. It uses free **standard** Linux runners, Python 3.11/3.13, pinned checkout/setup-python action SHAs, a read-only repository token, and no retained credentials, secrets, deployment, external cluster, GPUs or paid runners. It installs version-constrained test dependencies from PyPI; constraints are **not** hash-locked.

The job runs `python -m pytest -q`, compile checks, `python scripts/ci_smoke.py` and `python scripts/check_gates.py`. The smoke executes real Python processes using **synthetic** fixtures, including expected `UNKNOWN` for AIBOM and combined AICR/AIBOM and rejection of a modified signed journal. `check_gates.py` checks **stored historical** synthetic benchmark output; it does not benchmark each runner or prove runtime assurance. A green badge demonstrates the code path on hosted CI, not a GPU/Kubernetes validation.

**Publication authorization:** On 2026-11-12 the user explicitly approved the existing public repository and application of the work. Public repository visibility does **not** grant a reuse/distribution license. This code is an offline, synthetic prototype only; real-cluster data collection, release packaging, paid services and production deployment remain unauthorized.

### M7: transactional checkpoint simulation (offline, NOT externally anchored)

`src/runtime_assurance_lab/checkpoint_store.py` adds a single-host SQLite simulation around the M6 signed-source verifier. An operator must explicitly call `checkpoint-init-offline` on a **new** database with independently verified source/workload, authority SHA-256 and intent SHA-256. The returned full-state `state_sha256` must be protected **outside the SQLite database** and passed on *each* `evaluate-authenticated-stateful` call; the method refuses to infer it or to bootstrap automatically. The stateful command validates the separately supplied digest, then verifies the source/sequence/signature while holding an SQLite write transaction. A signed `OK`, `DRIFT`, `STALE` or `UNKNOWN` result commits source-sequence progress; untrusted input does not. Return code 0 requires a committed authenticated *source assertion* matching intent, not proof of actual GPU execution.

```sh
PYTHONPATH=src python -m pytest -q tests/test_checkpoint_store.py
PYTHONPATH=src python scripts/bench_checkpoint_store.py --samples 100 --output results/checkpoint_store_benchmark.json
PYTHONPATH=src python scripts/ci_smoke.py
```

Use `python -m runtime_assurance_lab.cli checkpoint-init-offline --help` and `evaluate-authenticated-stateful --help` for the bounded file/independent-pin interface. The paired CLI paths are **not** a replacement for Sigstore, trusted time, an external monotonic key/anchor store, or cluster attestation. Restoring both SQLite **and** the operator's external state hash defeats rollback protection; this is an intentionally tested residual vulnerability. Crash recovery when the local commit precedes durable external pin publication is not automated. G4 remains blocked.


### M8: research stop/go decision (no new runtime feature)

**Current recommendation: `PAUSE_PRODUCT_BUILD`.** Official sources confirm NVIDIA AICR, Google k8s-aibom and Sigstore already provide major parts of the proposed assurance chain. The M5 600-case same-input synthetic reference study showed **zero algorithmic disagreements**, not measured incremental benefit. G4 actual upstream comparison and customer evidence remain unavailable, so expanding another inventory or signature subsystem is unjustified.

```sh
PYTHONPATH=src python scripts/run_research_gate.py --verify-report results/research_gate.json
PYTHONPATH=src python -m pytest -q tests/test_research_gate.py
```

`research/upstream_overlap.json` documents checked vendor capabilities and falsifiers; `results/research_gate.json` is a deterministic **research NO-GO** report. Exit 0 from the script means the historical report matches recomputation; it **never authorizes production**. Do not use generated checklists or self-entered data as proof of real-world product value. Only authentic upstream evidence, an independently managed trust anchor, representative blinded baseline measurements, and a customer-backed requirement can justify reopening the investment decision. See `PLAN.md` M8.

## Pre-G4 upstream overlap verification (M9, research-only)

A separate GitHub Actions **public upstream fixture preflight** checks two immutable first-party repository test fixtures against pinned Git blob hashes, extracts existing Google CycloneDX evidence and probes the already-written RAL adapters. It deliberately **does not join** NVIDIA's training recipe to Google's unrelated inference BOM or assert signed/live GPU evidence.

```sh
# Offline, lists the only two public upstream source pins; no network:
PYTHONPATH=src python scripts/run_upstream_preflight.py --list-pins

# Explicit opt-in **public** network read, used in isolated GitHub CI research job:
PYTHONPATH=src python scripts/run_upstream_preflight.py --fetch-public-testdata

# Original source/policy tests remain offline:
PYTHONPATH=src python -m pytest -q
```

See `research/g4_independent_validation_protocol.md` for the blinded, independent real-upstream comparison, trust requirements, adverse cases and stop criteria. The investment decision is still **PAUSE_PRODUCT_BUILD**; no real G4 equivalence test has been run. Public source test fixture integrity is not upstream publisher identity or production attestation.

## M10: operator-controlled G4 handoff preflight (research only)

AICR and k8s-aibom already own bundle verification and workload inventory. Rather than building yet another production collector, `src/runtime_assurance_lab/g4_handoff.py` provides an **offline, no-network compatibility gate** for three operator-supplied JSON files (pinned intent, AICR RecipeResult, AIBOM CR). Its separate CLI `scripts/run_g4_handoff.py` requires independent SHA-256 pins for **all three** raw artifacts. It performs strict parser, source-byte and normalized identity checks and emits a minimal non-sensitive report. Even a perfect local synthetic input gets `decision=PAUSE_PRODUCT_BUILD`, `g4_authorized=false` and **exit 2**; invalid input gets **exit 3**. There is intentionally no exit 0, `GO` mode, or self-attested trusted-source option.

See [`research/g4_operator_handoff.md`](research/g4_operator_handoff.md) for synthetic-only usage, operator-controlled artifact custody, a namespaced `get`-only AIBOM RBAC example and the *actual* NVIDIA/Google native-verification prerequisites. `results/g4_handoff_synthetic.json` is a deterministic **synthetic-only** example. The repo never accesses production source artifacts or authorizes G4; all live trust and customer-value blockers remain. The M8 `PAUSE_PRODUCT_BUILD` recommendation still applies.

### Vendor-native upstream baseline (research-only, no cluster)

The independent, optional CI job `.github/workflows/native-upstream-baseline.yml` runs Google's published release provenance check and NVIDIA's native embedded recipe catalog verifier on exact pinned public release archives. Source and trust limitations are in `research/g4_vendor_native_baseline.md`. It does not run Kubernetes or GPU tests, authenticate a workload or override the research gate `PAUSE_PRODUCT_BUILD`.
