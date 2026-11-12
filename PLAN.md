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

Gate G4 (real integration, BLOCKED): verify actual AICR recipe/snapshot and k8s-aibom CRD schema/version, export redacted allowed fields, compare against AICR-only+k8s-aibom-only+Sigstore+policy-enforced baselines, with randomized controlled injection, blinded labels, at least 2 workloads classes and >1 cluster topology. Demonstrate recall/precision, end-to-end latency and cluster overhead. Do not deploy before access approval.

Gate G5 (commercialization, BLOCKED): before open-source/open-core/dual licensing, complete derivative-work/dependency licensing, independent threat review, user validation and actual evidence of unmet need. No pricing, private data ingestion, or publication during this phase.
