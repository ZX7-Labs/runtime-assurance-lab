# Architecture and trust boundaries

This project is a **Python-only offline research harness**, not a Kubernetes extension, enforcement point or proof of model execution.

## Components

| Module | Purpose | Hard limitation |
| --- | --- | --- |
| `contracts.py` / `json_strict.py` | Typed intent/observation and bounded JSON | No authority established by parsing |
| `aicr_adapter.py` | RecipeResult exact-byte pinning | A recipe is not proof of deployment |
| `aibom_adapter.py` | Narrow AIBOM CR → observation mapping | CR status/confidence is collector-reported |
| `evaluate.py` | Pure decision policy | Unauthenticated matches return `UNKNOWN` |
| `source_auth.py` | Scoped Ed25519 source-assertion verification | Requires separately anchored authority, intent, clock and prior state |
| `checkpoint_store.py` | SQLite transaction/replay **simulation** | Both database and external pin can be restored |
| `crossplane_receipt.py` | Deterministic independent recomputation | Source bytes and pin can be jointly forged |
| `g4_handoff.py` | Operator-provided local evidence preflight | Structural validation never grants G4 approval |
| `research_gate.py` | Reproducible no-go research decision | No customer value or real upstream parity established |

## Decision semantics

- `OK`: permitted **only** for an independently pinned and scoped, signed-source assertion that agrees with the intent. It authenticates the **claim**, not its physical truth.
- `DRIFT`: recorded policy disagreement where the required trusted inputs exist; does not prove model execution.
- `UNKNOWN`: missing, self-attested, unverifiable or insufficient evidence. **Default for untrusted JSON.**
- `STALE`: the time/freshness checks fail for an otherwise interpretable observation.

Raw JSON, AIBOM summaries, unanchored RecipeResult digests and self-generated demo journals must **never** be promoted to authenticated `OK`.

## Security model

1. Define the independently controlled intended workload and allowed source identity.
2. Parse input with strict bounds, reject duplicate keys/nonfinite values, and check exact bytes against the correct intended digest.
3. For the experimental authenticated path, verify detached signature, source scope, key identity, protected pins, freshness and replay sequence **against separately supplied expected state**.
4. Never treat the experiment's SQLite state or matching digest as an independently administered trust anchor.
5. Require native upstream Sigstore/issuer policy and independent evidence custody before any real G4 experiment.

The local canonical JSON signature format is **not** Sigstore/DSSE/JCS interoperable. An authorized signer can assert an untrue observation; independent runtime corroboration is not provided.

## Existing upstream capabilities

[NVIDIA AICR](https://github.com/NVIDIA/aicr) and [Google k8s-aibom](https://github.com/GoogleCloudPlatform/k8s-aibom) already supply substantial recipe, bundle-verification, inventory, BOM and signing functionality. Do not implement those again without evidence of an actual uncovered requirement. See [upstream audit](../UPSTREAM_AUDIT.md) and [equal-input G4 protocol](../research/g4_independent_validation_protocol.md).

## Non-goals

Not a model-serving platform, full attestation service, inference monitor, AI inventory controller, secure signing service, production security appliance or new cloud provider. `PAUSE_PRODUCT_BUILD` remains the correct research result until real independently trusted evidence establishes otherwise.
