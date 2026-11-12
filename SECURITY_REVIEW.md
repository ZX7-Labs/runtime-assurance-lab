# Critical review — offline prototype only

Review method: adversarial scenarios written separately from the happy-path fixtures; source and data-flow inspection. **Not** an independent third-party audit or second model's verification.

## Finding S-001 (HIGH): Signed-but-false decision

The first implementation checked event envelope signatures, parent workload binding and hash-chain anchoring, but **not the correctness** of a signed evaluator's `OK` claim. A buggy/compromised authorized signer could claim `OK` despite drift and pass crypto-only verification.

**Fix implemented:** add `verify_decision_semantics` which independently recomputes the result from authenticated parent claims at separately supplied clock and pinned policy version. CLI `verify` now requires both crypto and semantic verification. New regression `test_valid_signed_but_false_decision_rejected_by_independent_recomputation` demonstrates cryptographic success but semantic rejection. Retested.

## Finding S-002 (MEDIUM): Unhashable reference crash

Malformed `refs` containing non-string elements could throw instead of returning invalid proof. **Fix:** explicit type guard before constructing a set; attack test added.

## Outstanding material risks (not resolved here)

- **Trust root / head:** demonstration writes keys/checkpoint alongside journal; an attacker replacing all three could defeat detection. External WORM/transparency anchoring and identity/key rotation are mandatory for any real service.
- **Truth vs authenticity:** signed observations and `model_confidence=verified` are only *claims* from a synthetic source. No live k8s-aibom signature verification, artifact trust verification, model-execution attestation, or cluster authorization exists.
- **Time:** freshness relies on an externally trustworthy UTC clock; local test fixed time is a deterministic fixture, not a clock attestation.
- **Sampling/coverage:** untracked namespaces, unsupported workload kinds, pending pods, incomplete digests and unresolved models cannot be declared clean. Cluster-wide informer read scope creates real sensitive metadata exposure.
- **Race/consistency:** cross-plane snapshot versioning, event lag/ordering, revoked identities, resync and recovery are not implemented on real APIs. No concurrency tests, source-authentication tests or Byzantine failure model.
- **Availability/DoS:** memory limits and input/event journal length caps are not set for hostile multi-tenant JSON. Expose nothing to production until bounded parsers and load shedding exist.
- **Portability:** simple `json.dumps(sort_keys=True)` is a local canonical encoding contract, not RFC 8785 or Sigstore's protocol. Do not interoperate or advertise it as Sigstore-compliant.

Review disposition: acceptable **only** as a synthetic local research checkpoint. No production sign-off.
