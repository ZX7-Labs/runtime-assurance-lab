# G4 operator evidence handoff — preregistered, research-only

**Status: OFFLINE PREPARATION ONLY / NOT AUTHORIZED TO ACCESS A CLUSTER / NO PRODUCTION ATTESTATION / PAUSE_PRODUCT_BUILD.** This runbook is for an independently trusted operator, if the project later obtains written authorization and a representative environment. Do **not** upload actual unredacted files, credentials, public keys, cluster identifiers, private model names or real evidence to this public repository, PRs, logs or the chat by default.

## Decision and boundary

- Chosen: **reuse NVIDIA AICR's own signature/bundle verifier and Google k8s-aibom's own inventory/verification**. Our new `g4_handoff.py` is a bounded *offline document compatibility and exact-byte pin preflight*, not another publisher, trust root or controller. It cannot grant `G4` or `GO`, and deliberately exits **2 even for a matching synthetic handoff**.
- Rejected: a custom RAL collector plus new signing/canonicalization system. This would duplicate existing capabilities, increase security surface, and produce no proven incremental signal.
- Important distinction: matching SHA-256 strings against **caller-provided** pins detects changed bytes *relative to those pins*. It cannot demonstrate that those pins, sources, model claims or workload actually came from a trusted collector. **A signed but dishonest authorized source remains a possible failure.**

## Trust custody and data minimization

**Independently administered operator (not the software under evaluation)** owns all of the following before any live evaluation: exact version and digest of AICR/K8s AIBOM toolchain; vendor-verified immutable evidence bundle and creator identity; separately approved intent hash; k8s source identity and role; authenticated workload UID and time; trusted clock; durable replay/rollback checkpoint; cluster/configuration change audit; and blinded injection labels. Preserve the original artifacts, approval records, and all verifier stderr/stdout in **operator-controlled restricted storage**; never use a generated JSON claim as a substitute for those facts.

AICR's own documentation supports `aicr verify` (closed-world checksum + optional Sigstore attestation) and `aicr evidence verify` (recipe-evidence bundle with creator/issuer trust policy). Its `--trust-root` is *additive* to the built-in public root; it must not be assumed to force private-only signing. An independently approved creator/issuer policy is required, not simply a successful integrity check. `aicr evidence verify --help` from a pinned, vetted installed version is authoritative for exact flags, especially for key-signed versus keyless paths. The raw `RecipeResult` JSON is **not** itself a signature or evidence of deployment.

Google's `kubectl aibom verify <name> -n <namespace>` recomputes published BOM checksum and can show available signature facts; checksum equality does **not** authenticate the Kubernetes API export as a whole or prove the named model executed. Protect original Kubernetes API audit/identity, cluster connection and appropriate source signature evidence separately. An inline BOM can contain potentially sensitive model references and workload metadata; a redacted export must preserve whatever identifiers are necessary for the study while excluding secrets and private per-test output. NVIDIA AICR has its own minimized/redacted evidence mode; prefer it over inventing a second inconsistent redactor.

## Minimal read-only k8s authorization (operator-reviewed example only)

Use a **namespace-scoped** Role allowing `get` on a named AIBOM only; no watch/list, no secret access, no pod logs, no mutating verbs. The operator must replace the placeholders, review the identity and permissions, and apply this **only after separate approval**. Our repository does not apply or require this manifest.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: <approved-namespace>
  name: aibom-evidence-read-once
rules:
  - apiGroups: ["aibom.k8saibom.dev"]
    resources: ["aiboms"]
    resourceNames: ["<approved-aibom-cr-name>"]
    verbs: ["get"]
```

The Role alone does not grant access until a separately reviewed RoleBinding binds it to an authorized identity. Do not grant wildcard cluster roles for this study. The `resourceNames` restriction applies to `get` on the exact resource name, not arbitrary list/watch queries. All source commands remain operator-executed, never automated in this research repo.

A restricted operator could then run `kubectl -n <approved-namespace> get aibom <approved-aibom-cr-name> -o json` into a **protected** destination; don't pipe raw exports to public CI. Export the matching AICR `RecipeResult` **and separately authenticated AICR bundle/pointer** through official upstream tooling, using an identical verified workload reference and evaluation window. Preserve the original source bytes before any redaction and document exactly what redaction removed.

## Offline structural preflight (only after authorized safe data transfer)

The CLI requires **three independently delivered exact-byte pins**; do not derive them from a malicious file and claim this proves authenticity. It intentionally doesn't support `--trusted`, `--approved`, or any input-supplied `verified` switch. The report contains only byte counts, SHA-256 digests, component count, generic limitation codes and statuses; it does not echo raw model/workload names. SHA-256 fingerprints themselves can still expose membership in a known small corpus, so treat reports as potentially sensitive operational metadata.

```sh
# Demonstration ONLY using the repository's synthetic fixtures (safe to publish):
cd runtime-assurance-lab
PYTHONPATH=src python scripts/run_g4_handoff.py \
  --intent fixtures/intent-aicr-synthetic.json \
  --expected-intent-sha256 sha256:0467066640dcba132bc7aff5c812d7fbb9fbabcdd44d4ba2b771263d05306aa1 \
  --recipe fixtures/aicr-recipe-result-synthetic.json \
  --expected-recipe-sha256 sha256:a44787410b9f5f8e7c60df82007639c11b90bacff731cf75ad9ad0681305febb \
  --aibom fixtures/aibom-v1beta1-synthetic.json \
  --expected-aibom-sha256 sha256:ffaa05cc35bebadad3779608a5d50350d53df0d229c07b0fdbd261642fe28437
# exit 2 -> PAUSE_PRODUCT_BUILD, g4_authorized=false; NEVER authenticated OK.
```

`--output <fresh-file>` writes only the minimal report, refuses to overwrite, creates with `0600` permissions. No network, GPU, signature verification or cluster access occurs. The operator must review all exported data before public use. Symlinks at the final input path and non-regular files are rejected; ancestor directories, shared-host races and malicious filesystem owners are **not** a tested safe ingestion boundary. Use a private isolated workspace under operator control.

Return codes: `2` = structural report completed, yet **not authorized**, even when all raw bytes match; `3` = malformed/unreadable/inconsistent input or pins. There is intentionally **no exit-0 success path** from this command.

### Required next G4 validation, not done here

1. Collect real, legally shareable, minimally redacted *same-workload* signed AICR evidence plus v1.6.2 AIBOM CR under separate authority, and verify creator/issuer/root and collector identity using actual upstream tools and immutable operator custody.
2. Prove timestamp, deployment/workload UID, policy, signer/key and intent lineage independently; hold an external anti-rollback anchor that the test implementer cannot alter.
3. Execute the already preregistered randomized/blinded equal-input matrix against AICR alone, k8s-aibom alone, existing Sigstore/policy composition and RAL. Include genuine healthy and attacks, stale/unobservable conditions, inference plus training/agent workloads, and two topologies.
4. Record ground truth, same-input eligibility, uncertainty intervals, false authenticated `OK`, drift recall/precision and *actual end-to-end* latency/CPU/RSS. Stop on any unsupported `OK` or inability to preserve independent trust; **stop standalone product** if upstream composition gives materially equivalent coverage, or customer need remains unproven.

**Blocker today:** No authorized real artifacts, independently controlled verified root/checkpoint/clock, cluster, blinded operator or customer proof. M8 research decision **PAUSE_PRODUCT_BUILD** is unchanged. A structurally matching synthetic handoff does not unblock G4.

## Primary sources (pinned research context)

- NVIDIA AICR v1.2.0: <https://docs.nvidia.com/aicr/latest/user-guide/artifact-verification/> and <https://github.com/NVIDIA/aicr/tree/v1.2.0>
- Google k8s-aibom v1.6.2: <https://github.com/GoogleCloudPlatform/k8s-aibom/blob/v1.6.2/README.md>
- Kubernetes official RBAC `resourceNames` semantics: <https://kubernetes.io/docs/reference/access-authn-authz/rbac/>
- G4 competitor and falsification preregistration: [`g4_independent_validation_protocol.md`](g4_independent_validation_protocol.md)
