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
