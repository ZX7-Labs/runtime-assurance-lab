# Critical review — offline prototype only

Review method: adversarial scenarios written separately from the happy-path fixtures; source and data-flow inspection. **Not** an independent third-party audit or second model's verification.

## Finding S-001 (HIGH): Signed-but-false decision

The first implementation checked event envelope signatures, parent workload binding and hash-chain anchoring, but **not the correctness** of a signed evaluator's `OK` claim. A buggy/compromised authorized signer could claim `OK` despite drift and pass crypto-only verification.

**Fix implemented:** add `verify_decision_semantics` which independently recomputes the result from authenticated parent claims at separately supplied clock and pinned policy version. CLI `verify` now requires both crypto and semantic verification. New regression `test_valid_signed_but_false_decision_rejected_by_independent_recomputation` demonstrates cryptographic success but semantic rejection. Retested.

## Finding S-002 (MEDIUM): Unhashable reference crash

Malformed `refs` containing non-string elements could throw instead of returning invalid proof. **Fix:** explicit type guard before constructing a set; attack test added.

## Finding S-003 (MEDIUM): Ambiguous JSON and unbounded local files

Default `json.loads` accepted duplicate keys with last-key-wins semantics and nonstandard `NaN`/`Infinity`; local inputs had no file-size limit. The verifier also assumed a mapping-shaped trust store and a syntactically valid external anchor.

**Fix implemented:** reject duplicate keys at all nesting depths, nonfinite numeric tokens, invalid UTF-8 and files larger than 8 MiB; bound accepted journal event count to 10,000; validate trust type and external head form. Added CLI, parser, malformed-trust and malformed-anchor regressions. These are offline PoC limits, not a comprehensive parser/DoS threat model.

## Outstanding material risks (not resolved here)

- **Trust root / head:** demonstration writes keys/checkpoint alongside journal; an attacker replacing all three could defeat detection. External WORM/transparency anchoring and identity/key rotation are mandatory for any real service.
- **Truth vs authenticity:** signed observations and `model_confidence=verified` are only *claims* from a synthetic source. No live k8s-aibom signature verification, artifact trust verification, model-execution attestation, or cluster authorization exists.
- **Time:** freshness relies on an externally trustworthy UTC clock; local test fixed time is a deterministic fixture, not a clock attestation.
- **Sampling/coverage:** untracked namespaces, unsupported workload kinds, pending pods, incomplete digests and unresolved models cannot be declared clean. Cluster-wide informer read scope creates real sensitive metadata exposure.
- **Race/consistency:** cross-plane snapshot versioning, event lag/ordering, revoked identities, resync and recovery are not implemented on real APIs. No concurrency tests, source-authentication tests or Byzantine failure model.
- **Availability/DoS:** a coarse 8 MiB per-file limit and 10,000-event cap now exist; nested JSON depth, aggregate input size, process limits and streaming/load-shedding for hostile multi-tenant input are NOT addressed. Expose nothing to production.
- **Portability:** simple `json.dumps(sort_keys=True)` is a local canonical encoding contract, not RFC 8785 or Sigstore's protocol. Do not interoperate or advertise it as Sigstore-compliant.

Review disposition: acceptable **only** as a synthetic local research checkpoint. No production sign-off.

## S-007 — CI trust boundary (M2, 2026-11-12)

- Public PRs can execute untrusted repository test code. This CI deliberately uses only `pull_request`/`push`, a read-only `GITHUB_TOKEN`, `persist-credentials: false`, no repository secrets, no `pull_request_target`, no external attestations, and no GitHub write scopes. An attacker can still consume allowed public CI resources; branch rules and fork approval are externally controlled.
- First-party actions are pinned to Git object commit SHAs fetched from official GitHub tags (2026-11-12); updates require explicit review. Standard runners are free for public repositories according to GitHub documentation, but only standard `ubuntu-24.04` is used, never a paid larger runner.
- PyPI packages and setuptools build dependencies are version-constrained but **not checksum-locked**; a compromised package index/artifact or malicious contributor may still affect job execution. CI does not run with secrets, but these are not sufficient controls for trusted production publishing. No SBOM, provenance attestation or reproducible wheel builds are claimed.
- A passing CI pipeline verifies synthetic source behavior and deterministic smoke contracts only; it does not authenticate AICR exports, provide an independently held journal checkpoint or prove GPU workload execution.
