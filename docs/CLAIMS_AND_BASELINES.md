# Evidence ledger: what is demonstrated, what remains open

**As of 2026-11-13:** This project is a CPU-only, offline *investigation*. The governing investment decision remains `PAUSE_PRODUCT_BUILD`. The [NVIDIA November 11, 2026 integration article](https://developer.nvidia.com/blog/validating-gpu-platforms-with-runtime-ai-inventory-via-the-nvidia-dsx-ai-factory/) motivates the question but does **not** establish a missing commercial product.

## Four different levels of evidence

1. **Data shape:** a JSON document parses and carries a model reference, digest and evidence locator. This does not establish who collected it.
2. **Integrity and source assertion:** bytes match an externally controlled pin and a signature verifies against an externally established source identity. An authorized but dishonest signer may still lie.
3. **Corroborated workload state:** independently authenticated, same-workload intent and observer records, trusted clock, separately held replay state, and a fair upstream comparison. **Not completed here.**
4. **Physical model execution:** independently established fact that the model executed on a specific GPU at a specific time. **Not demonstrated here.**

Do not collapse these levels when reporting results or reviewing a pull request.

## Existing coverage first

| Existing project | Official upstream capabilities | What RAL must not replicate |
| --- | --- | --- |
| [NVIDIA AICR](https://github.com/NVIDIA/aicr) | Version-locked recipes, deployment bundle verification, snapshots, validators, optional attestations; v1.2.0 integrates k8s-aibom | GPU platform recipe/controller, bundle renderer, signature stack |
| [Google k8s-aibom](https://github.com/GoogleCloudPlatform/k8s-aibom) | Opt-in Kubernetes AI workload inventory, CycloneDX 1.6 BOM, confidence tiers, evidence locators, digest/status and optional model-signature checks | Kubernetes watcher, BOM/ML inventory collector, generic model trust verifier |
| [Sigstore](https://docs.sigstore.dev/about/bundle/) | Signing and verification of artifacts and supplied identities/transparency evidence | PKI, signing service, transparency log |
| [Kyverno](https://kyverno.io/docs/) / [OPA Gatekeeper](https://open-policy-agent.github.io/gatekeeper/website/docs/) | Policy enforcement in Kubernetes and existing admission/control workflows | Another admission/policy engine |

Source-specific license references: [NVIDIA AICR](https://github.com/NVIDIA/aicr/blob/main/LICENSE), [Google k8s-aibom](https://github.com/GoogleCloudPlatform/k8s-aibom/blob/main/LICENSE), [Sigstore Cosign](https://github.com/sigstore/cosign/blob/main/LICENSE), [Kyverno](https://github.com/kyverno/kyverno/blob/main/LICENSE), [OPA](https://github.com/open-policy-agent/opa/blob/main/LICENSE). Their respective license files govern their own code; linked repositories can change. RAL uses its own [Apache-2.0 license](../LICENSE) for owner-licensable material and **does not vendor** these implementations.

NVIDIA's article states that its sampled k8s-aibom v1.6.1 controller test used CPU-only nodes with workload pods pending. The quoted ~2.2 millicores and 28–34 MiB are **NVIDIA-reported controller observation metrics**, not RAL's overhead and not actual GPU model execution measurements. See the [official article](https://developer.nvidia.com/blog/validating-gpu-platforms-with-runtime-ai-inventory-via-the-nvidia-dsx-ai-factory/) for its setup and limitations.

## Metrics: denominator and scope matter

| Existing result | Recorded outcome | What it actually measures |
| --- | --- | --- |
| Synthetic 700-case pilot | 100% “needs-attention” recall; 0% false alarms on 70 constructed clean cases | Mutated or insufficient-evidence classification; `UNKNOWN` and `STALE` count as attention, **not confirmed drift** |
| Deliberately weak local naive comparator | ~22.2% attention recall | A strawman sanity check, **not vendor baseline** |
| Synthetic evaluation p95 | 20.43 µs | In-process Python computation; **not event-to-detection latency** |
| Synthetic signed pipeline p95 | 1.18 ms | Local synthetic signing/verification; no API/network/disk |
| 600-case historical complete-input reference | 0 disagreements | A negative control on constructed cases; **no evidence of incremental product value** |
| Authentic same-workload vendor-vs-RAL comparison | **Missing** | No real GPU/Kubernetes drift recall, precision/FPR or overhead can be claimed |

Historical data: [benchmark.json](../results/benchmark.json), [incremental_value_post_gate.json](../results/incremental_value_post_gate.json), [research_gate.json](../results/research_gate.json), [vendor-native public CPU checks](../results/g4_vendor_native_cpu.json). Some historical optimistic metrics predate strengthened source-authentication gates. Do not reuse them as present-day real-world assurances.

## A falsifiable experiment, not a roadmap of features

**H0:** With identical independently authenticated inputs, appropriately configured AICR + k8s-aibom + Sigstore/policy composition is as useful as an additional correlation component.

To reject H0, a reviewer needs a preregistered [G4 protocol](../research/g4_independent_validation_protocol.md), licensed/authorized same-workload records, independently held identity and trust pins, blinded ground truth, equally capable upstream controls, and measured collection-to-verdict latency + actual CPU/RSS/network overhead. Report missed detections and false alarms with denominators. Account for startup, normal drift, evidence loss, staleness and signer dishonesty. AICR RecipeResult and a generic AIBOM cannot be joined by an invented workload ID.

**Stop** if the vendor composition covers the requirement at comparable cost; contribute the smallest missing integration upstream. **Do not start** a standalone enforcement component on the strength of a synthetic pass, GitHub stars, unverified signups or a publication announcement. Separate customer discovery and external security review remain missing.
