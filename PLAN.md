# Research plan — runtime-assurance-lab

## Hypothesis and falsification

Hypothesis H1: A separate, portable correlation layer can bind **qualified deployment intent** to **observed AI workload evidence**, with explicit lineage/freshness and a re-verifiable decision, without duplicating AICR, k8s-aibom, Sigstore, or policy engines.

Falsify H1 if upstream already offers complete cross-plane correlation with identities, time semantics and proof of decision, or if representative integration offers no incremental signal beyond existing tool combinations. Stop rather than build a redundant controller.

## Architecture comparison

| Dimension | (A) K8s-native reconciliation controller | (B) Event-sourced signed evidence graph |
| --- | --- | --- |
| Ownership | Cluster-local informer and CRD state | Stateless comparator + independent append-only evidence store |
| Inputs | Kubernetes watches, AICR recipe CR/export, AIBOM CRs | Signed/pinned AICR intent export and read-only k8s-aibom AIBOM snapshot stream |
| Output | `AssuranceStatus` CR and Kubernetes events | Signed/anchored decision with content-addressed parent links |
| Strength | Immediate K8s lifecycle, native resync and status | Cross-cluster/time replay, offline audit, independently reproducible decisions |
| Duplication risk | **High**: k8s-aibom already reconciles resources; Gatekeeper/Kyverno already enforce | Moderate: Sigstore signs artifacts; must restrict work to cross-plane correlation and avoid reinventing signing/trust infrastructure |
| Permissions | Watches workloads/AIBOMs cluster-wide, CR write, RBAC and availability concerns | Offline PoC needs **zero cluster permissions**; later readonly minimal adapter per targeted namespace |
| Operational risks | Watch load, CRD upgrades, resync storms, cluster upgrades | Signed false claims, missing source trust/anchors, replay, out-of-order and stale events |
| Proof feasibility here | No Kubernetes/Docker/GPU tools available | Full deterministic offline tests and local benchmarks |

**Decision: B as a small, replaceable investigation prototype.** Not a new generalized event platform. Durable trace later should use existing transparency/immutable backends; local Ed25519/hash-chain code is only to demonstrate audit invariants and a falsifiable trust model. No Kubernetes controller is built in this checkpoint. Reassess after live use-case evidence.

## Usage / contracts

```
ral evaluate --intent fixtures/intent.json --observation fixtures/clean.json --now 2026-11-12T03:25:00Z
ral demo --fixtures fixtures --output results/demo
ral verify --journal results/demo/journal.json --trust results/demo/trust-public.json --checkpoint results/demo/checkpoint.json
ral benchmark --output results/benchmark.json
```

`Intent{workload,model_ref,model_digest,image_digest,platform_recipe_digest}` is the pinned expectation. `Observation{workload,model_ref?,model_digest?,image_digest?,platform_recipe_digest?,observed_at,model_confidence,evidence_locator,source}` is an intentionally normalized **synthetic** fixture contract, NOT raw NVIDIA or Google API data. The platform recipe fingerprint is a future AICR/snapshot adapter field; it is not claimed to be produced by k8s-aibom.

Core rule `evaluate(intent, observation, now, max_age=300s, skew=30s) -> Finding`. Status: `OK`, `DRIFT`, `UNKNOWN`, `STALE`; all non-OK imply **needs review**, not necessarily malicious drift. Stale/future observations cannot assert current drift. Model identity requires both pinned model reference+digest and upstream `verified` claim; this pilot does **not** independently validate that upstream Sigstore claim. Decision semantic verification recomputes outputs from signed inputs at separately trusted `now`.

`evidence` is a DAG of intent, observation and decision events; a signed hash-chain serializes them with parent hashes. Three ephemeral local principals have limited roles. The result only demonstrates tamper-evidence with separately protected public key material and a separately anchored head; the demo saves these side by side **for convenience only**, so the demo is not a secure audit log. No canonical CycloneDX or Sigstore bundle verification is implemented.

## Module boundaries / recovery

- `contracts.py`: schema and bounds; never silently normalize ambiguous input.
- `aicr_adapter.py`: exact-byte pin and bounded AICR v1.2.0 resolved JSON RecipeResult adapter (no provenance authentication).
- `crossplane_receipt.py`: deterministic report over original source bytes; independently replayable only with caller-supplied pin, clock and sources; never authenticates origins.
- `json_strict.py`: common fail-closed JSON boundary (including finite-number enforcement).
- `aibom_adapter.py`: version-pinned, read-only **offline** AIBOM v1beta1 CR adapter; maps only actual upstream summary fields, never upgrades unsigned CR claims to verified identity.
- `evaluate.py`: pure deterministic policy, no I/O.
- `evidence.py`: Ed25519 event envelope, causal links, role constraints, anchor verification, separate semantic recomputation.
- `bench.py`: labeled synthetic cases, honest limited local comparator, processing/CPU/Python heap measurements.
- `cli.py`: JSON file boundary and non-zero status on unknown/drift/stale/bad proof.
- `fixtures/`: synthetic only. `tests/`: unit, CLI integration, adversarial, synthetic benchmark smoke.
- Recovery: no mutable service state or network; rerun with original immutable inputs; missing event must fail against independently held checkpoint. Never repair corrupted evidence in place.

## Staged acceptance and stop gates

Gate G0 (scope): AICR/k8s-aibom already cover collection; Sigstore/policy engines cover signatures and admission. If their documented future work closes exact H1, stop and contribute upstream instead.

Gate G1 (local contracts): strict parse; missing/ambiguous fields fail; `OK` requires fresh, complete, verified matching data.

Gate G2 (tamper/semantic): all enumerated local signature, rewrite, reorder, role, reference, truncation and signed-false-decision attacks rejected under independently anchored trust assumptions. Full rollback protection is impossible without external anchoring.

Gate G3 (synthetic performance): establish baseline first; then provisionally require >=98% recall and <=1% FPR on constructed labeled cases; p95 evaluation <1ms and <=20x the in-process naive comparator; peak measured Python heap allocation <=2x local baseline plus 1MiB. These are **pilot sanity gates**, calibrated from initial local measurement; not deployable SLOs. Capture event-to-detection latency and pod CPU/RSS only on authorized real clusters.

Milestone M1 (offline integration preparation, DONE 2026-11-12): pin Google k8s-aibom `v1.6.2` tag and inspect the upstream `api/v1beta1` schema. Accept exported JSON AIBOM CR without any cluster API permission; verify namespace/workload binding, Ready/Stale and observedGeneration, timestamp presence, and inline CycloneDX 1.6 BOM hash/size/type. Return `UNKNOWN` on healthy synthetic CR because model/image digests, AICR recipe association, and independent signature verification are not established by the CR summary. Fail closed on malformed BOMs, conflicting identities and schema mismatches. This does NOT satisfy G4.

Milestone M2 (public, CPU-only CI, HOSTED-VERIFIED 2026-11-12): build a no-privilege GitHub Actions matrix (Python 3.11 and 3.13) that reruns unit/integration/adversarial tests, module compilation, synthetic acceptance-report validation, and a separate subprocess smoke that checks clean/DRIFT/STALE/AIBOM-UNKNOWN/tamper behavior. Pin first-party action commits, do not retain checkout credentials, give the job only `contents: read`, bound jobs to 10 minutes, and do not use secrets, deployments, caches, privileged containers, GPUs, or paid runners. Freeze tested Linux dependency versions in CI constraints (not hash-locked), document PyPI supply-chain trust as residual risk. Local pipeline checks prove only source behavior; mark CI as hosted-verified **only after** a GitHub-hosted run succeeds. This milestone is NOT G4 and does not validate live Kubernetes behavior.

Milestone M3 (offline cross-plane recipe byte-pin, PUBLISHED + HOSTED-VERIFIED 2026-11-12): pin **NVIDIA AICR v1.2.0** `RecipeResult` (`apiVersion: aicr.run/v1`) using an exact, bounded SHA-256 over a caller-provided **JSON export**, separately matching that digest to an explicit normalized `Intent.platform_recipe_digest`; then feed only the partial, version-pinned Google AIBOM v1beta1 observation to the existing evaluator. No AICR-specific model/workload fields are invented; the recipe does not prove deployment, a trusted publisher, cluster state or model execution. Require strict JSON including overflow rejection, bound raw inputs, test tampering/version ambiguity/invalid CRs, and report `UNKNOWN` for the combined synthetic fixture. Bench only local preloaded processing. The pin itself and the intent are **not authenticated** by this PoC. No YAML parser, snapshot collector, Sigstore bundle verifier, registry/network fetch, Kubernetes RBAC or new controller. This preparation does NOT satisfy G4.

Milestone M4 (offline reproducible cross-plane receipt, PUBLISHED + HOSTED-VERIFIED 2026-11-12): on user-supplied local JSON files, deterministically derive a bounded receipt containing exact SHA-256 of intent/AICR `RecipeResult`/AIBOM CR bytes, adapter versions/limitations, policy version, normalized trusted timestamp, and `UNKNOWN`/`STALE`/`DRIFT` decision. `receipt-offline` creates a new file exclusively (no overwrite); `replay-offline` requires **independently supplied** source files, expected AICR pin, and evaluation clock and recomputes ALL fields. Reject false `OK`, changed bytes, schema/version/limitations/clock/policy mismatch, type-confused JSON, and unavailable inputs. The receipt is NOT signed, authenticated, anchored or proof of execution; its fingerprints are integrity claims over caller-controlled bytes. Keep this separate from existing synthetic signed-journal demonstration; future authentic source attestation should use existing Sigstore and trusted upstream export mechanisms, not a bespoke signing format. Test adversarial replay, response errors and recovery, benchmark preloaded processing only, and run in existing read-only CPU CI once published. Never present replay success as evidence of upstream identity, real deployment or freshness. This is NOT G4.

Milestone M5 (offline incremental-value falsification / negative control, PUBLISHED + HOSTED-VERIFIED 2026-11-12): run deterministic labeled **synthetic** conditions separating (a) policy-visible, complete fresh claims, (b) hidden true drift behind missing/stale/future evidence, and (c) nonconformant values actually reported. Compare the evaluator to both the intentionally limited naive local comparator and an independently coded **same-input** reference policy. Count `DRIFT` separately from review-required `UNKNOWN`/`STALE`, preventing an attention recall from being presented as drift recall. Require no `OK` on partial evidence and zero fair-reference discrepancies for the controlled policy model; add an explicit attacker-controlled matching-source probe which currently produces **unsafe `OK`** and must remain a G4 trust-origin blocker; treat such parity as **no algorithmic advantage established**, not as product differentiation. No upstream NVIDIA/Google software is executed. Store full breakdown and code in `results/incremental_value.json`, `scripts/bench_incremental_value.py`, and tests. Repetitions are deterministic identity variations, NOT independent population samples; timing is preloaded local Python only. Leave G4 blocked until authorized representative upstream comparisons.

Gate G4 (real integration, BLOCKED): verify actual AICR recipe/snapshot and k8s-aibom CRD schema/version, export redacted allowed fields, compare against AICR-only+k8s-aibom-only+Sigstore+policy-enforced baselines, with randomized controlled injection, blinded labels, at least 2 workloads classes and >1 cluster topology. Demonstrate recall/precision, end-to-end latency and cluster overhead. Do not deploy before access approval.

Gate G5 (commercialization, BLOCKED): before open-source/open-core/dual licensing, complete derivative-work/dependency licensing, independent threat review, user validation and actual evidence of unmet need. No pricing, private data ingestion, or publication during this phase.

## M6 — source-forgery containment before G4 (offline, implemented and hosted CI verified 2026-11-12)

**S-018 reproduction:** v1 `evaluate()` accepted a counterfeit, complete normalized observation with `model_confidence="verified"` and returned `OK`, without checking its origin. This was an untrusted label, NOT signature verification. Keep M1–M5 as completed historical research, but their pre-M6 accuracy/microbench numbers are **claim-only historical diagnostics**, not authenticated assurance.

### Competing remediation architectures

| Criterion | A — independently pinned offline source gate | B — standardized externally anchored attestation/transparency verification |
| --- | --- | --- |
| Inputs | Exact raw observation, detached Ed25519 proof, out-of-band pinned authority and intent hashes, external expected sequence and predecessor | Trusted workload identity via Sigstore/DSSE bundles, verified material/identity policy, external transparency checkpoint, AICR/AIBOM source-level attestations |
| Authenticity | Key identity tied to allowlisted source/workload by immutable pinned manifest | Issuer identity and delegation policy verified via upstream attestation/bundle trust roots |
| Replay/rollback | Fail closed unless caller supplies durable next sequence and predecessor from a state it controls | Signed/anchored append-only log checkpoints and inclusion/consistency proof with durable monotonic state |
| Trust failure | Explicit `UNKNOWN`; no source-supplied `verified` flag can authenticate itself | Explicit `UNKNOWN`; reject invalid/missing upstream bundle, root or log proof |
| Feasibility now | Implement/test entirely offline using existing PyCA dependency, no new permissions | BLOCKED: authentic upstream bundles/identity policy and external anchor/cluster absent |
| Residual risk | A compromised authorized signer can still lie; ephemeral or self-supplied anchors offer no real security | Transparency alone does not prove measured runtime truth; adds dependency and operational requirements |

**Decision:** prototype A as the smallest defensible *local containment* while preserving B as the G4 interop target. Never call the prototype a Sigstore verifier or execution attestation; do not invent a CA or hosted signing service.

### Trust-boundary requirements (must be checked together)

1. **Origin/source identity:** a separately configured `source_id`/`key_id` and per-workload allowlist; compare with signed envelope and normalized observation.
2. **Trusted signing keys:** exact manifest bytes must match a SHA-256 pin established **independently of input files and observer**. Neither a CR `signed` label nor a public key shipped with its claim establishes trust.
3. **Signatures and canonicalization:** detached Ed25519 over a domain-separated, schema-exact signable envelope, containing SHA-256 of **exact observation bytes**; strict UTF-8 JSON rejects duplicate keys/nonfinite input. Local sorted-key JSON canonicalization is **NOT JCS/DSSE/Sigstore interoperable**.
4. **Provenance and freshness:** signature covers source identity, workload, timestamp and digest; externally supplied UTC time checks age/skew. A signature validates the authorized source's assertion—not inference execution or actual model hash verification.
5. **Replay/rollback:** require separately held exact `expected_sequence` and `expected_prev_head`; return `UNKNOWN` for a replay, gap, branch or rollback. On verified input expose a `next_checkpoint`, but **caller** must persist and protect it transactionally; code does not provide a secure store or automatic advancement.
6. **Intent provenance:** exact intent-byte digest must independently match an operator-pinned SHA-256; an attacker-controlled intent and a forged matching observation cannot establish assurance.
7. **Fail closed:** untrusted `evaluate`, AIBOM, cross-plane receipts and locally signed journals cannot promote raw records to authenticated `OK` or `DRIFT`. Explicit `evaluate-authenticated` is the only CLI path that permits authenticated-source comparison.

**Acceptance:** reproducible forged-source `OK` before / `UNKNOWN` after; valid pinned signer yields source-authenticated `OK` for a synthetically matching claim; source/key/workload mismatches, tampering, invalid proofs, timestamp misbinding, replay, rollback, missing anchors and invalid/changed roots fail closed. Preserve historical M5 numbers with a clearly labeled *claim-only* comparator; policy version bumps to `ral-intent-observation-v2-provenance-gate` so old signed verdicts cannot silently replay.

**Security stop:** do not use this proof to assert running AI model identity or production conformance. Before G4/G5, require source-specific upstream signature/identity semantics, independently protected key trust and anti-rollback store, secure trusted time, external review and authentic real workload evidence. Do not ship an `OK` claim from a raw AIBOM CR, unanchored recipe pin, a self-supplied key or a replayed signed journal.

**Hosted verification (2026-11-12):** the public GitHub `main` source commit `16fc4f4cca166912939b03fd3128b17bd076e8d0` passed Python 3.11 and 3.13 matrix run 43167150345, with 158 tests per job. That verifies source behavior on standard runners only; external source-authentication roots and durable checkpoint storage are still absent.

**Upstream interoperability constraint:** NVIDIA AICR already documents offline `aicr verify --trust-root` bundle verification and explicit `--require-creator` signer controls ([official artifact verification](https://docs.nvidia.com/aicr/latest/user-guide/artifact-verification/)); its root is additive to the embedded public-good root, so signer identity must still be constrained. The PoC has **not** run this verifier on authentic evidence. Use those upstream capabilities and a separately monitored trust root in future G4 rather than generalizing this local Ed25519 envelope.

## M7 — independently pinned local checkpoint transaction harness (offline; not G4)

**Motivation:** M6's source verifier accepts externally supplied sequence/previous-head values but does not protect those values between calls. A caller can accidentally reuse an old checkpoint or race concurrent verifications. G4's independently administered, tamper-proof monotonic store and authentic upstream evidence are still unavailable.

**Alternatives compared:**

| Option | Verification / state owner | Offline feasibility | Risk |
| --- | --- | --- | --- |
| A — bounded SQLite transactional simulation | Local SQLite row per `source_id` + `workload`, `BEGIN IMMEDIATE` locks through signed-source validation and synchronous commit; caller independently supplies SHA-256 of whole previous checkpoint, pinned intent and authority | Available without network/permissions; standard-library SQLite | Local database is **not** an independent trust root; operator must protect the state digest separately. Restoring both DB and external digest can replay. Crash after DB commit but before operator persists next digest can halt recovery. |
| B — external monotonic CAS / transparency checkpoint | Independent durable authority holds source trust, expected next sequence, and compare-and-swap anchor; existing Sigstore/AICR verification establishes source identity | **Blocked** without authorized independent service, real signed upstream evidence, and clock/key policies | Additional trust and operational burden; a compromised authorized signer can still lie about runtime. |

**Decision:** implement **A only as a falsifiable harness** (`checkpoint_store.py`) exercising transactional advancement under an *independently held* pin; keep B as the required G4 architecture. Not a new signing standard, certificate authority, managed service or production-proof checkpoint. No new dependencies, cluster permissions or network access.

**Contracts:** operator explicitly bootstraps a NEW database with externally known `source_id`, workload, root digest and intent digest; bootstrapping refuses an existing path. The returned `state_sha256` must be stored in a separately protected channel and supplied on **every** subsequent `evaluate-authenticated-stateful`. Validation begins inside an SQLite `BEGIN IMMEDIATE` transaction and checks root/intent/entire-state pins, Ed25519 proof, signed stream sequence/predecessor, source scope and freshness. Every authenticated signed claim, including `UNKNOWN`/`DRIFT`/`STALE`, advances the monotonically recorded sequence; untrusted failures do not. A checkpoint must commit before success is returned. No automatic bootstrap or recovery/rewind. SQLite uses synchronous FULL, an exclusively created mode-0600 file and a bounded 5-second lock wait. `evaluate-authenticated` remains a stateless proof check and MUST NOT be advertised as stateful rollback protection.

**Acceptance:** deterministic restart/replay, altered authority/intent, forged signature, restored SQLite snapshot with independently held new pin, concurrent same-sequence attempts, broken state/schema, missing DB, symlink, failed commit, and trusted negative verdict all fail closed or safely advance as specified. **Negative control:** restoring BOTH SQLite and the *externally held* digest permits replay; document as unresolved rather than claiming protection. Record 100-sample local SQLite + crypto transaction processing baseline, keep historic 7/7 synthetic gates labeled as stored/claim-only. Hosted CI on Python 3.11/3.13 required before claiming publication verification.

**Stop/next action:** Do not use this SQLite simulation to authorize live deployment or replace an external CAS/transparency service. G4 requires an authorized, independently administered monotonic checkpoint authority, pinned signed AICR/AIBOM provenance, trusted time, and read-only cluster integration. If existing upstream tools already meet H1, stop duplicating them. G5 is still blocked.


## M8 — upstream overlap and investment-stop gate (2026-11-12, offline research)

**Goal:** Answer the user's explicit constraint: do **not** build a product without demonstrated incremental value. No new AI inventory, signature format, storage engine, Kubernetes controller, or policy feature is authorized by this research gate. Preserve M1–M7 as completed *offline* research checkpoints.

**Independent primary-source overlap review:**

- NVIDIA AICR v1.2.0 already verifies deployment bundle inventories/checksums and optional Sigstore signatures, trusted-root and creator identity, plus signed recipe-evidence bundles combining recipe/snapshot/validator results/BOM. The official CLI reference explicitly notes `aicr evidence verify` does **not** replay inline constraints against the bundled snapshot. Source: https://docs.nvidia.com/aicr/latest/user-guide/artifact-verification/ and https://docs.nvidia.com/aicr/latest/user-guide/cli-reference/ (reviewed 2026-11-12; latest docs can evolve).
- Google k8s-aibom v1.6.2 already inventories Kubernetes AI workloads, tracks declarations/inference with evidence locators, resolves image digests, and has verified model-signature confidence with configurable trust roots and signer constraints; BOM snapshots are not executed-model attestations. Source: pinned `https://github.com/GoogleCloudPlatform/k8s-aibom/blob/v1.6.2/README.md` (tag commit `47bf6418e40eee22905973528b879dc075181b3f`).
- Sigstore already has artifact/bundle signature/transparency and identity-policy controls. Source: https://docs.sigstore.dev/about/bundle/ and https://docs.sigstore.dev/policy-controller/installation/.

**Competing strategies:** (A) immediately add another reconciliation/signature/rollback product component; (B) freeze feature expansion and falsify the cross-plane incremental-value hypothesis using actual upstream-composed baselines. Chose **B**. A overlaps native products, increases attack surface and has no positive same-input synthetic delta (M5: **0 / 600 comparator disagreements**, not a real upstream benchmark). The possible niche of constraint replay/cross-plane time alignment is an *unproven hypothesis*, not evidence of customer demand or ability to attest GPU execution. There are no authentic upstream artifacts, independent customer samples or controlled cluster comparisons yet.

**Executable M8 research contract:** `research/upstream_overlap.json` records three existing upstream capability groups, pinned references and three falsifiable hypotheses; `src/runtime_assurance_lab/research_gate.py` reads that matrix and historical **claim-only** `results/incremental_value_post_gate.json` with bounded strict JSON, rejects missing/contradictory source records and fake GO flags, and emits a deterministic `results/research_gate.json`. `scripts/run_research_gate.py --verify-report results/research_gate.json` recomputes and compares the committed decision in CPU-only CI; tests in `tests/test_research_gate.py` deliberately attempt to promote synthetic evidence into product approval. Exit code 0 means *report verified*, **not product GO**. This is an auditable research guardrail, NOT independent proof or a cryptographic trust anchor.

**Decision: `PAUSE_PRODUCT_BUILD`.** Stop new product-scope feature implementation until all four separately established G4/G5 inputs exist: authenticated real AICR/AIBOM source evidence; independent authority/monotonic checkpoint; controlled live upstream baseline comparison (two workload classes and multiple topology types); and a customer-backed measurable requirement. If AICR+k8s-aibom+Sigstore/policy tools achieve equal outcomes for the target use case, **stop the standalone project** and contribute the minimal missing behavior upstream when justified. Avoid further synthetic benchmark polishing as substitute for this decision.

**Next executable action:** arrange a narrowly authorized evidence/data access process: redacted real upstream signed AICR recipe-evidence bundle and matching AIBOM CR, source signer identity, separately administered trust anchors, read-only Kubernetes scope, and predefined measurement plan. If not available, maintain the research no-go and do not expand the implementation. G4/G5, independent security review, CPU/RSS/latency instrumentation and physical execution proof remain blocked.


## M8 publication checkpoint (2026-11-12)

M8 research source and tests published as GitHub `main` commit `87fb6031f19cf6c03f766b1022e6a1ae195ea50d`. The immutable source tree matched local Git blobs for **71/71** tracked files; GitHub Actions run [43227942102](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43227942102) completed successfully on Python 3.11 and 3.13 (**199 tests passed per job**), including the NO-GO report check. These results do not waive `PAUSE_PRODUCT_BUILD` or unblock G4/G5. The only next admissible research is to secure independent real-world upstream/customer validation, not further product-scope coding.

## M9 — substantial pre-G4 upstream parity/falsification workstream (research only)

Status: **implementation and hosted validation pending** at planning start; leave G4 and G5 BLOCKED. No more runtime subsystems until actual incremental value is established.

Scope: (1) re-verify pinned NVIDIA AICR v1.2.0 and Google k8s-aibom v1.6.2 upstream **public test fixtures**, byte-for-byte; (2) run independent extraction of already supplied CycloneDX model and image-digest claims; (3) exercise existing AICR/AIBOM adapters and show information/trust limits; (4) fail closed on tamper, spoofing, schema/identity contradictions, redirect/oversized inputs; (5) publish a pre-registered, blinded head-to-head protocol versus existing real upstream tools; (6) run a separate, no-secrets, CPU-only GitHub research CI job with network reads restricted to immutable official public fixture paths. See `research/g4_independent_validation_protocol.md` and `src/runtime_assurance_lab/upstream_preflight.py`.

Acceptance: independently pinned Git blob identity of BOTH public fixtures, exact Google existing digest/model metadata counts, NVIDIA RecipeResult interpretation, **no cross-plane join across unrelated fixtures**, no authenticated `OK`, `PAUSE_PRODUCT_BUILD` retained, adversarial tests and Python 3.11/3.13 hosted CI green. Do not claim upstream binary execution, genuine cluster evidence, market fit or production value from pinned source test fixtures. The external G4/G5 blockers and kill criteria remain unchanged.

**M9 real-public-fixture correction:** The first hosted research job exposed a previously hidden compatibility bug: official NVIDIA `RecipeResult` has `source=""` with local manifests, which the prior parser rejected although the upstream schema only requires a JSON string. Narrowly fix this existing adapter for bounded explicit `manifestFiles`; preserve source-unattested limitations and no `OK`. Retest and rerun all three hosted CI jobs before treating public-testdata preflight as verified. This repair does not lift `PAUSE_PRODUCT_BUILD` or G4/G5 blocks.

## M10 — operator-controlled G4 evidence handoff gate (offline preparation, 2026-11-12)

**Why this is not another product feature:** M9 confirmed that NVIDIA AICR and Google k8s-aibom already expose substantial inventory and source-authentication primitives; adding another controller or bespoke verifier has no proven incremental benefit. M8's `PAUSE_PRODUCT_BUILD` remains binding. The next *unblocked* work is a reproducible, privacy-conscious **operator evidence handoff interface** that cannot falsely promote structural matches to trusted runtime assurance.

**Alternatives:** (A) write an additional RAL collector/trust-root and create new runtime service (rejected: duplicates upstream and weakens security); (B) require independently administered source proofs and use native `aicr verify`/`aicr evidence verify` plus Kubernetes AIBOM APIs, with a bounded local raw-byte/structural preflight (chosen). Native verified evidence and cluster access are still unavailable, so no G4 test is claimed.

**Implementation scope:** `g4_handoff.py` and an explicit `run_g4_handoff.py` CLI accept only three bounded offline JSON artifacts (operator intent, AICR v1.2.0 RecipeResult, Google AIBOM v1beta1) plus three *separately provided* exact SHA-256 pins. Reuse the earlier strict JSON and upstream adapters; check structural workload, model and category consistency without inventing runtime binding. Output only source SHA-256/size and generic diagnostic codes. The CLI must reject nonregular/symlink files, malformed and tampered content, preserve exclusive `0600` report outputs, and **always return nonzero**: exit 2 on a structurally consistent but unauthenticated handoff; exit 3 on invalid inputs. `g4_authorized` and `authentic_upstream_provenance_verified` remain `false`, without any user-controlled override. There is no remote fetch, cluster API call, certificate/attestation verification, database migration or new package dependency.

**Acceptance / stop:** falsify self-attested signers, mismatched identities, nonfinite/duplicate-key JSON, digest spoofing, unsafe output, and incomplete AIBOM; run full test suite, 16 process smoke cases, historical gates, both hosted Python jobs and independent upstream-public-fixture job; verify published immutable file hashes. The recorded synthetic handoff report is research-only. Genuine G4 still requires a separately authorized, redacted, signed same-workload evidence set, independently retained root/intent/time/checkpoint, actual vendor-native signature verification, controlled blinded equal-input comparison and external reviewer. See `research/g4_operator_handoff.md`. No standalone product restart without new verified incremental value.

**M10 hosted verification (2026-11-12):** GitHub source commit `8b8b0a1e3bf4dc95c015df320cf2cc845d4c8cd8` passed hosted GitHub Actions run [43238958517](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43238958517): Python 3.11/3.13 each **269 tests passed**, 16 subprocess smoke cases, stored 7/7 research pilot gates and pinned public upstream fixture research job. The full committed 82-file source tree matched local Git blob identities. These are **offline research checks only**, not G4 production or live workload verification. The operator-controlled handoff guide is now ready, but G4 actual execution and G5 product validation remain BLOCKED; the next work requires externally authenticated same-workload sources and a customer-value reason to restart.

## M11 — vendor-native signed-release baseline (bounded CPU research; **not G4**)

Before attempting any costly Kubernetes/GPU experiment, test what the pinned official vendor tools can verify directly. Two alternatives were evaluated: (A) clone native inventory/signing functionality, rejected due overlap and unproven value; (B) run the actual public vendor release executables and vendor-released provenance with independently pinned artifact hashes, chosen as the next unblocked falsification step. See `research/g4_vendor_native_baseline.md`.

Run `scripts/g4_vendor_native_baseline.py` in a path-scoped GitHub CPU job, with checksum-pinned NVIDIA AICR v1.2.0 and Google k8s-aibom v1.6.2 Linux-amd64 artifacts, and the Google provenance bundle. Verify Google's archive with `gh attestation verify --owner GoogleCloudPlatform`, call `aicr recipe verify-catalog <bundle-path>` against the pinned NVIDIA Sigstore catalog bundle, and invoke `kubectl-aibom --help`. The executable identity, catalogue authenticity, and *runtime* authenticity are different controls; report each separately. Fail with nonzero exit when a required step is unavailable; never silently degrade to `GO`. No cluster credentials, privilege, secrets, Docker, GPU or deployment.

**Acceptance:** deterministic local adversarial tests, existing complete Python 3.11/3.13 suites, new GitHub-hosted upstream native CPU job, exact committed tree comparison, and explicit evidence of all partial/failed attempts. No new product feature, independent customer comparison, live instrumentation or production-readiness claim. `PAUSE_PRODUCT_BUILD` remains binding. G4/G5 remain blocked until an operator supplies a legal authentic matching AICR/AIBOM pair, separately administered trust and an authorized test environment. If these are unavailable, do not continue writing synthetic product code.

**M11 actual native verification (research complete, G4 still blocked):** corrected the NVIDIA CLI contract to include release-pinned `recipe-catalog.sigstore.json` and verified live GitHub-hosted execution in run [43244660419](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/runs/43244660419). Verified Google GitHub provenance for its published CLI archive, NVIDIA's actual embedded catalogue signature using its published Sigstore bundle, and Google's real CLI help invocation; none verifies a running GPU model. Code explicitly reports `g4_completed=false` and `PAUSE_PRODUCT_BUILD`, with results and limitations in `results/g4_vendor_native_cpu.json` and `EVIDENCE.md` §32. No real same-workload signed AICR/AIBOM pair was supplied. Therefore G4 and G5 remain blocked; no separate product expansion should proceed. This concludes the presently unblocked vendor-native CPU research scope.

## Community open-source readiness (2026-11-12)

Repository owner authorized publishing the existing original code as open source and preparing a high-quality developer-facing repo. **License decision (supersedes old D-006): Apache-2.0** for owner-licensable original material, with SPDX package metadata and attribution NOTICE. Preserve all M1–M11 results, tests, policy semantics and negative findings. Do not present source publication as G4 completion, product value proof or a production release. Third-party dependencies and upstream repos retain their own licenses.

**Deliverables:** short and accurate public README with tested quickstart; CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, architecture and roadmap; tested GitHub issue and PR forms; a small metadata regression test; generated demo outputs removed and ignored; full existing security/CI/gates remain mandatory. Do not delete scientific evidence or test fixtures in a cosmetic cleanup.

**Acceptance:** SPDX license is recognized by GitHub, source package includes LICENSE/NOTICE, Python 3.11/3.13 CI and public vendor fixture research jobs pass, README runnable commands work on synthetic fixtures, changed source blob hashes are verified on GitHub, no secrets/private data exposed. The research gate must stay `PAUSE_PRODUCT_BUILD`. Real G4, G5 and security assurance remain blocked on independently authenticated real same-workload evidence, protected trust roots, actual GPU/Kubernetes infrastructure and external adversarial review.
