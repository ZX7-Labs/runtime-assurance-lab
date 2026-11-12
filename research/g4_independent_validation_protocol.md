# G4 independent baseline and stop/go protocol (preregistered preflight)

**State:** DESIGN ONLY / **NO LIVE DATA** / no permission to deploy / no authentic signed provenance provided. Reviewed 2026-11-12. This document exists to prevent expanding a redundant product or presenting synthetic unit tests as enterprise validation. It is not a customer agreement or security sign-off.

## The real hypothesis worth testing

H1: A distinct, *portable* correlation consumer detects a policy-relevant **intent-versus-runtime** change that cannot be detected with equivalent correctness, source freshness, provenance, auditability and operational cost using **AICR + k8s-aibom + existing Sigstore/policy controllers**, given the same independently authenticated evidence and equivalent response time.

Alternative H0: The composition of existing upstream tools already supplies that signal, possibly with a thin integration; a separate product would duplicate capabilities or add unsupported assurance claims. **H0 is current provisional investment decision.** No product features until G4 evidence contradicts it.

## Independent evidence custody — prerequisites, not automatic assumptions

An authorized operator other than the test implementation owner must supply and hold: (1) upstream bundle/CR exports with minimal redacted workload fields and exact version IDs; (2) issuer/key identity policy, separately pinned Sigstore trust roots/expected creator; (3) independent immutable expected intent, trusted timestamp, secure source-of-truth for checkpoint sequence/head; (4) run manifest and precommitted randomized injection schedule; (5) sealed result labels kept from the implementation reviewer. Do not assume Git object hashes, self-supplied public keys, or status labels authenticate runtime.

**Every purported `OK` must be rejected unless this custody exists.** Intent provenance, observed model execution and GPU source identity are independently required; merely signing what Kubernetes reported does not prove inference execution. Request signed attestation/independent corroboration, *if* available, rather than inventing one.

## Test matrix and precommit

Use at least two workload classes (**inference** and **training or serving-agent**) and two cluster topologies (one local/managed and one materially different; actual choices recorded before testing). Within each class/topology use randomized controlled scenarios, including: unchanged healthy control, image/model digest change, AICR recipe/platform deviation, stale/missing pod or AIBOM evidence, source-key impersonation, signed-but-false payload, signer revocation/rotation, replay/rollback, clock skew and collector outage. Keep sample identifiers and blinded ground-truth injection labels externally. Test both genuine drift and evidence that cannot justify a decision. Disclose any case with no independent execution witness as *unobservable*, never call it false-negative-free assurance.

### Equal-input competitor comparison

Run **AICR alone**, **k8s-aibom alone**, **Sigstore/OPA/Kyverno admission/audit controls**, **their documented composition with a minimal query/policy**, and **proposed correlation** over the **same** events, evidence, trust policy, trusted time, reporting interval and workload identity. Exclude intentionally naive baselines from differentiation claims. Execute actual upstream versions; documentation comparisons are not substitutes. Store version, config, collector RBAC, resource requests, provenance validity and any disabled features in the published research record. Repeat runs with blinded order to reduce observer bias.

### Metrics and integrity gates

Record per-scenario confusion matrices for *actual drift*, *needs review*, *unsupported OK*, and *source-authentication failure*. Compute false-positive rate, actual drift recall, precision, coverage, evidence missing rate and latency distribution **from source change to accepted decision**. Measure controller/consumer CPU/RSS/network/disk/persistent-state and recovery/restart behavior. Include 95% uncertainty intervals and per-class/per-topology breakdown; report empty denominators as unavailable. Qualify hardware and sample size before threshold selection. Do not use historical Python p95 microbenchmarks as pod RSS/latency.

**Hard stop, irrespective of attractive coverage:** any unsupported authenticated `OK`, unauthenticated or replayed source accepted, inability to protect monotonic state, unexpected cluster privileges, or inability to reproduce an upstream verdict. Do not hide failures in aggregate metrics.

**Commercial stop:** when the equal-input upstream composition achieves materially equivalent verified behavior, or when customers do not pay for or adopt the distinct workflow, stop standalone product expansion; offer the smallest verifiable upstream issue/patch if warranted. A statistically tiny or unrepeatable difference is not enough. Decide performance/value thresholds and sample/power plan *before* viewing genuine labels; current samples are insufficient to set valid operational SLOs.

## Available research experiment now — not G4

`python scripts/run_upstream_preflight.py --fetch-public-testdata` (run only in the explicitly network-enabled GitHub Actions research job) downloads two **public source repository test fixtures**, not live infrastructure evidence:

- Google `k8s-aibom` v1.6.2 fixed commit: CycloneDX 1.6 `vllm-deployment-output.json`, `inference` BOM fixture with model claims and a container image SHA-256 *claim*.
- NVIDIA AICR v1.2.0 fixed commit: `v1.1.2/recipe-h100-eks-ubuntu-training.json`, `training` RecipeResult fixture. The **fixture metadata** says 1.1.2; it is checked in the repository at the **v1.2.0 commit**. These are distinct concepts.

Both exact bytes are checked against fixed upstream Git blob SHA-1 and reported SHA-256. This is fidelity to published test assets, **not independent publisher signature verification**. Our own GitHub CI executes our Python extraction and adapters, **not Google's or NVIDIA's binaries**. The two fixtures come from different workload classes and have no common authenticated deployment ID: comparison must explicitly return `cross_plane_link_verified=false`. The locally constructed healthy AIBOM wrapper tests our adapter but is **not an upstream AIBOM CR export**; Google already has a container digest within the raw BOM, whereas the current summary-only adapter correctly refuses to promote it into a trusted normalized observation. This is an overlap/coverage constraint, not proof of added value.

## Dependencies required to unblock real G4

First receive a legally shareable redacted real AICR RecipeResult + signed evidence bundle and matching Google AIBOM resource/export from the **same identifiable workload**, along with separately controlled creator/root/clock and persistent checkpoint. Then obtain authorized test clusters, resource monitors, controlled injection permission, and a blinded evaluator. Only after upstream verifier identity checks succeed should any live cross-plane comparison begin. Commercial G5 requires real customers and full licensing review.

**M8/M9 stop rule:** do not confuse green upstream public-testdata CI with real G4 progress beyond preflight preparation. If no independent data will be made available, keep `PAUSE_PRODUCT_BUILD` and discontinue feature expansion rather than accumulate synthetic implementations.
