# Official-source audit as checked 2026-11-12

All links below are primary vendor or upstream-project sources. Source code was **not** copied into this repository. SPDX labels are verified on upstream project pages; full transitive license / export-control / trademark review is still outstanding.

| Project | Existing coverage (avoid duplication) | Documented integration point | License |
| --- | --- | --- | --- |
| NVIDIA AICR | Version-locked recipes, deployment bundles/checksums/optional attestations; `snapshot` + `validate` deployment/performance/conformance; validation is a point-in-time platform check | Consume pinned recipe and separately acquired snapshot exports; do not implement GPU/operator validation | Apache-2.0 |
| Google `k8s-aibom` | Kubernetes AI workload inventory to CycloneDX 1.6, confidence/evidence locators, model Sigstore verification, digest resolution, conditions and staleness, local kubectl verify; opt-in namespaces, cluster-wide watch cache | Read recognized AIBOM CRD (not workload secrets) through a narrow future adapter; do not build another AI inventory controller | Apache-2.0 |
| Sigstore Cosign & policy-controller | Artifact signatures, certificates/identity, Rekor proofs, bundle verification; admission-time OCI image/signature verification and digest resolution | Reuse Sigstore verifier/bundle and trust roots; policy-controller's namespace policy, not local Ed25519 format | Apache-2.0 |
| OPA / Gatekeeper | Rego decisions; Kubernetes constraint CRDs, audit, admission enforcement | Consume authoritative result in existing OPA/Gatekeeper policy rather than new webhook | Apache-2.0 |
| Kyverno | Admission/background rules and signed image/attestation verification, digest pinning, policy testing | Enforce pre-existing image policies; correlation result could be a policy input when available | Apache-2.0 |
| PyCA `cryptography` | Well-reviewed Ed25519 crypto primitives; no need to code crypto | Local signing/verification primitive only, installed version 46.0.4 | Apache-2.0 OR BSD-3-Clause |

## Sources

- NVIDIA, Nov 11 2026: https://developer.nvidia.com/blog/validating-gpu-platforms-with-runtime-ai-inventory-via-the-nvidia-dsx-ai-factory/
- NVIDIA AICR upstream: https://github.com/NVIDIA/aicr ; CLI `validate`: https://docs.nvidia.com/aicr/latest/user-guide/cli-reference/
- Google k8s-aibom upstream: https://github.com/GoogleCloudPlatform/k8s-aibom
- Sigstore Cosign verified bundles: https://docs.sigstore.dev/quickstart/quickstart-cosign/ ; format https://docs.sigstore.dev/about/bundle/ ; upstream license https://github.com/sigstore/community/blob/main/LICENSING.md
- Sigstore policy controller: https://docs.sigstore.dev/policy-controller/installation/ ; upstream https://github.com/sigstore/policy-controller
- OPA/Gatekeeper: https://www.openpolicyagent.org/docs/kubernetes ; https://github.com/open-policy-agent/opa ; https://github.com/open-policy-agent/gatekeeper
- Kyverno verification: https://release-1-18-0.kyverno.io/docs/policy-types/cluster-policy/verify-images/overview/ ; license https://github.com/kyverno/kyverno
- PyCA license: https://github.com/pyca/cryptography/blob/main/LICENSE

## Key version/security constraints

- NVIDIA Nov 11 2026 article states AICR **v1.2.0** pins k8s-aibom **1.6.2**; do not infer that older README install examples (1.5.1) are current. Pin exact version and test CRDs before real adapters.
- NVIDIA states the selected stock recipes (`h100-gke-cos-inference`, `h100-gke-cos-inference-dynamo`); per-namespace opt-in for AIBOM reporting **does not** restrict informer reads. Must threat-model workload-spec/inline-env exposure before granting cluster access.
- NVIDIA reports k8s-aibom ~4 API server requests/min, 2.2 mCPU average, 28–34 MiB steady state under its qualified conditions. These are **upstream's** measurements, not measured here and not directly comparable to the Python offline experiment.
- AIBOM can exist when a pod is pending; its `Ready=True` is not verified successful execution. `verified` model means cryptographic signature subject to identity constraints, not proof of active inference.
- Source overlap may already solve much of the use case; this repo does not claim a new market gap. Actual source-compatible correlation requirements are hypotheses until tested.

## v1.6.2 schema-level check performed 2026-11-12

Read upstream, pinned **tag `v1.6.2`**, Git commit `47bf6418e40eee22905973528b879dc075181b3f`:
- [AIBOM v1beta1 types](https://github.com/GoogleCloudPlatform/k8s-aibom/blob/v1.6.2/api/v1beta1/aibom_types.go): `apiVersion: aibom.k8saibom.dev/v1beta1`, `kind: AIBOM`; `spec.workloadRef`, `status.summary.workload`, `status.summary.models[].{identity,confidence,signed}`, `status.bomDocument.{sha256,inline,external,truncated}`, `lastReconciled`, `observedGeneration`. `ModelSummary.identity` is not a digest. `ModelSummary.signed=verified` is a controller-reported claim; this PoC does not verify its provenance.
- [Condition definitions](https://github.com/GoogleCloudPlatform/k8s-aibom/blob/v1.6.2/api/v1beta1/aibom_conditions.go): `Ready`, `Stale`; `Ready=True` means BOM generation, **not model execution**.
- [Group version](https://github.com/GoogleCloudPlatform/k8s-aibom/blob/v1.6.2/api/v1beta1/groupversion_info.go): `aibom.k8saibom.dev/v1beta1`.

The fixture `fixtures/aibom-v1beta1-synthetic.json` is handwritten to match the inspected *shape*, **not captured from an actual upstream controller**; schema compatibility has not been established by running a real release. Do not infer that a synthetic inline CycloneDX document or matching CR `bomHash` authenticates a producer. No upstream code was copied.

## M3 pinned source interpretation (2026-11-12)

- [NVIDIA AICR v1.2.0 `RecipeResult.schema.json`](https://github.com/NVIDIA/aicr/blob/v1.2.0/api/aicr/v1/schemas/RecipeResult.schema.json) has `apiVersion`, `kind`, `componentRefs`, `criteria`, `deploymentOrder`, `metadata`, and optional config/validation. The implementation validates only a narrow interoperable subset, **not** the complete AICR JSON schema. Official source [recipe metadata constants](https://github.com/NVIDIA/aicr/blob/v1.2.0/pkg/recipe/metadata.go) define resolved `RecipeResult`, and [header version constants](https://github.com/NVIDIA/aicr/blob/v1.2.0/pkg/header/header.go) identify the stable `aicr.run/v1` track. Use the tagged source, not potentially newer `latest` examples.
- [Official AICR CLI reference](https://docs.nvidia.com/aicr/latest/user-guide/cli-reference/) documents `aicr recipe --format json` and `aicr snapshot --format json`; **this PoC did not invoke either upstream binary**. It accepts only resolved JSON RecipeResult exported elsewhere, and does not interpret AICR recipe metadata as workload model identity.
- AICR's `RecipeResult` is **not** Kubernetes k8s-aibom's per-workload CR and does not independently prove a recipe was deployed or a signed AI model actually executed. The combined fixture intentionally remains `UNKNOWN`. No upstream code or schema files were copied. License remains Apache-2.0 upstream; research repo licensing remains undecided.


## M8 competitor overlap / investment gate (2026-11-12)

Official upstream review (tag pin where possible, no live tool execution):

1. **NVIDIA AICR:** [artifact verification](https://docs.nvidia.com/aicr/latest/user-guide/artifact-verification/) documents closed-world checksums, Sigstore attestation, trusted roots, creator identity and signed recipe-evidence bundles. [CLI reference](https://docs.nvidia.com/aicr/latest/user-guide/cli-reference/) explicitly states `aicr evidence verify` does not replay bundled snapshot inline constraints. It also states signer-bound evidence is **not** physical cluster attestation; a lack of that feature does not establish a new market gap.
2. **Google k8s-aibom v1.6.2:** [pinned README](https://github.com/GoogleCloudPlatform/k8s-aibom/blob/v1.6.2/README.md) covers workload inventory, CycloneDX 1.6, evidence locators, model verification policy, digest resolution and controller conditions. Model signatures do not prove runtime execution.
3. **Sigstore:** [bundle](https://docs.sigstore.dev/about/bundle/) and [policy controller](https://docs.sigstore.dev/policy-controller/installation/) already cover signed object, expected identity and transparency validation patterns.

The M5 same-input 600-case study had zero discrepancies. This neither establishes equality with upstream real tools nor an incremental capability. **Current investment outcome: PAUSE_PRODUCT_BUILD**, governed by `research/upstream_overlap.json` and `results/research_gate.json`. Candidate cross-plane temporal/provenance correlation remains unproven; G4 requires independent real measurements. Product overlap conclusions are a bounded desk review, not a formal feature-by-feature certification of current vendor releases.

## M9 first-party testdata/negative control (verified upstream Git trees, 2026-11-12)

- Google `GoogleCloudPlatform/k8s-aibom` **tag v1.6.2**, commit `47bf6418e40eee22905973528b879dc075181b3f`: [`internal/bom/testdata/golden/vllm-deployment-output.json`](https://github.com/GoogleCloudPlatform/k8s-aibom/blob/47bf6418e40eee22905973528b879dc075181b3f/internal/bom/testdata/golden/vllm-deployment-output.json), Git blob SHA-1 `b708db2f5a67c2210d29e712a7dd4f8f59487635`, 6,387 bytes. Source JSON has CycloneDX 1.6 model evidence entries, *claimed* container image SHA-256 and workload inference category. This is first-party **golden testdata**, not a Kubernetes CR or real workload observation. The project README explicitly provides runtime BOM inventory, source evidence locators and model signature verification controls.
- NVIDIA `NVIDIA/aicr` **tag v1.2.0**, annotated tag dereferenced to commit `935e0746dc54da890a23c1ecca998244b3a25de7`: [`pkg/operator/aicrjob/testdata/v1.1.2/recipe-h100-eks-ubuntu-training.json`](https://github.com/NVIDIA/aicr/blob/935e0746dc54da890a23c1ecca998244b3a25de7/pkg/operator/aicrjob/testdata/v1.1.2/recipe-h100-eks-ubuntu-training.json), Git blob SHA-1 `7aefe761a870efcc7e74971b8a9d23b093f2918e`, 105,200 bytes. Source is a stored, resolved RecipeResult v1 with 15 components and `training` criteria. The testdata's subdirectory is labeled v1.1.2 but exists at repository **v1.2.0** commit. This is not an attested production recipe bundle.
- NVIDIA upstream `pkg/evidence/verifier/verify.go` in the pinned tag contains the pre-existing evidence-verification implementation, not our work. Source-audited constraints and official docs forbid treating provider signature as proof of a physical cluster. See `research/g4_independent_validation_protocol.md` for the strict difference between first-party public fixtures, actual upstream executable comparisons and authenticated runtime evidence.
- Git blob SHA-1 is used **only as pinned source byte fidelity**. It does not establish security-grade publisher authentication or independently anchored GPU execution. Runtime output SHA-256 and version/path details are recorded separately. No provider code is copied into this project repository; only the provider's public test fixtures are read during the opt-in CI job.
- A current GitHub Releases API lookup on 2026-11-12 returned latest non-prerelease **NVIDIA AICR v1.2.0** (published 2026-11-02) and **Google k8s-aibom v1.6.2** (published 2026-10-22). Therefore the M9 upstream testdata references the latest public releases as of this check, while the independent *live* version matrix and credentials remain unavailable. See respective [`NVIDIA/aicr` releases](https://github.com/NVIDIA/aicr/releases/tag/v1.2.0) and [`GoogleCloudPlatform/k8s-aibom` releases](https://github.com/GoogleCloudPlatform/k8s-aibom/releases/tag/v1.6.2).
- **Real fixture compatibility regression (M9):** In AICR's pinned `v1.2.0` source tree, the official resolved `RecipeResult` JSON has two `Helm` components with `source=""` but nonempty local `manifestFiles` (`dra-node-labeler` and `nodewright-customizations`). The pinned `RecipeResult.schema.json` requires `source` of JSON type string, not nonempty. RAL's prior overly strict parser rejected this genuine upstream example; corrected offline parser accepts explicitly bounded local manifest filenames while continuing to flag all such inputs as unauthenticated claims. The first GitHub public-fixture check exposed this; record this as a **real compatibility failure**, not a novel assurance feature.

## M10 native vendor verification and minimal handoff research (2026-11-12)

- NVIDIA AICR v1.2.0 artifact verification: <https://docs.nvidia.com/aicr/latest/user-guide/artifact-verification/>. Native `aicr verify` checks a closed-world deployment bundle; `aicr evidence verify` verifies signed recipe-evidence bundles and included payload digests. Creator/issuer/key policy must be pinned independently; `--trust-root` is **additive** to public-good, not a replacement. Upstream already minimizes/redacts emitted evidence, so RAL should not replicate its signature or redaction machinery.
- Google k8s-aibom v1.6.2: <https://github.com/GoogleCloudPlatform/k8s-aibom/blob/v1.6.2/README.md>. Native AIBOM BOM contains model/component inventory and confidence; `kubectl aibom verify` checks published BOM hash and signature facts. A digest match alone does not prove a Pod ran a specific model. An API read needs independently authenticated Kubernetes identity and operator approval.
- Official Kubernetes RBAC: <https://kubernetes.io/docs/reference/access-authn-authz/rbac/>. `resourceNames` combined with namespace Role and only `get` can restrict access to a known AIBOM CR. No new cluster role or permissions applied here.
- Research disposition: **PAUSE_PRODUCT_BUILD**; the only added code is a safe, non-authorizing handoff preflight to prepare independently trusted G4, not a product feature or competitor replacement. `research/g4_operator_handoff.md` documents required operator custody and the no-live-data boundary.

## M11 additional primary-source observations

- NVIDIA AICR official v1.2.0 GitHub release `https://github.com/NVIDIA/aicr/releases/tag/v1.2.0` publishes Linux-amd64 executable archive with GitHub release-metadata SHA-256. Official artifact guide `https://docs.nvidia.com/aicr/latest/user-guide/artifact-verification/` describes built-in recipe catalog verification, `aicr verify` trust levels, `aicr evidence verify` signed evidence, and optional signer constraints. These upstream capabilities overlap with any proposed generic product signing/inventory layer. The native baseline uses the additionally pinned `recipe-catalog.sigstore.json` release asset for catalog signature verification; it does not verify an authentic evidence bundle.
- Google `k8s-aibom` v1.6.2 GitHub release `https://github.com/GoogleCloudPlatform/k8s-aibom/releases/tag/v1.6.2` publishes kubectl plugin archives and GitHub-signed provenance. Its official README describes `kubectl aibom verify`, Sigstore-verified model confidence and NVIDIA AICR qualification; the native CPU baseline checks release provenance and runs help only, not the cluster plugin verification.
- Both projects publish their own test evidence. Their separate test fixtures represent different workloads and cannot be joined into an authenticated cross-plane observation. No real G4 groupwise or competitor metric can be computed from these assets.
