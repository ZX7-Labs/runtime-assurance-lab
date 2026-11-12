# G4 research: upstream-native public release verification (NOT live G4)

**Decision:** `PAUSE_PRODUCT_BUILD`. No product runtime feature should be added while the independently authenticated same-workload comparison remains absent.

## Rationale and architecture comparison

| Candidate | Observable evidence | Incremental product value | Decision |
| --- | --- | --- | --- |
| Build our own runtime inventory, signature, bundle verifier or policy controller | Google k8s-aibom already provides the controller, ML-BOM, confidence/locator, model signature verification and CLI `verify`; AICR already publishes recipes, verifies bundles/evidence, and selects k8s-aibom in qualified configurations | Overlap is substantial; duplicate operation/security cost | **Reject** |
| Run provider-native release checks on CPU-only public artifacts | Independently verify Google release provenance with GitHub attestation, invoke NVIDIA's embedded signed-catalog verifier; strict release byte pins | Establishes what upstream tools actually run and what cannot be concluded without live evidence | **Implement once as a bounded preflight** |
| Compare intent and runtime on a real workload under separate independent trust control | Requires authenticated AICR recipe, matching running AIBOM for the same workload, blinded fault injections, trusted roots/time/checkpoint, measured cluster/GPU cost | Could falsify our H0 of no distinct product | **Blocked** until such evidence exists |

The baseline script runs on an **ordinary GitHub-hosted CPU runner** and downloads only three immutable, SHA-256-pinned release assets from the official GitHub repositories. It rejects binary archive symlinks and unsafe names and extracts a single expected executable to a temporary directory. It checks:

- `gh attestation verify` on Google's v1.6.2 `kubectl-aibom` Linux archive using Google's published provenance bundle and the independent GitHub CLI's `--owner GoogleCloudPlatform` identity constraint;
- `aicr recipe verify-catalog` using NVIDIA's **actual v1.2.0 Linux release executable**, after checking the release archive SHA-256 against pinned GitHub release metadata;
- actual `kubectl-aibom --help` invocation (proof the binary runs, not of BOM source verification).

This **does not** verify NVIDIA's release binary's publisher signature; the pinned release checksum is a content identifier, not a standalone authentication mechanism. The AICR embedded catalog test is vendor-native, but it does not validate a deployed workload or signed upstream runtime evidence. Google's release provenance authenticates the published binary artifact, not any particular AIBOM from a cluster.

## Reproduction

`python scripts/g4_vendor_native_baseline.py --output /tmp/g4-vendor-native.json`

Requires Linux amd64, GitHub CLI (`gh`) with attestation support, outbound HTTPS to public GitHub release assets, no secrets, no Kubernetes, no GPU, no third-party installation. `--output` refuses overwriting. Run only in the opt-in / path-filtered `.github/workflows/native-upstream-baseline.yml`; this baseline is not part of the normal offline CI and must not become a persistent paid/background poll.

A successful process returns `decision=PAUSE_PRODUCT_BUILD`, `g4_completed=false`, `gpu_execution_verified=false`, and `same_workload_upstream_evidence=false`. Failures exit nonzero with `public_vendor_baseline=INCOMPLETE`, not a simulated success. Pinned release artifacts and their SHA-256 are in the script; GitHub metadata and source tag links are in `UPSTREAM_AUDIT.md`.

**No live G4 claim:** no actual AICR evidence bundle is correlated with an AIBOM from the same cluster. G4's preregistered 2-class / 2-topology, blinded, equal-input benchmark cannot be run without separately controlled real source identities, authentic evidence and an authorized GPU cluster. Releasing this CPU-native baseline is not a substitute for those inputs.

## Hard project stop

If the independently verified vendor composition matches our detector on all policy-relevant cases under equal inputs, or if no representative real evidence can be made available, **do not develop a standalone product**. The existing M1-M10 research results remain historical; do not infer that a new feature becomes justified because vendor binaries were successfully downloaded or executed.

Upstream evidence:
- NVIDIA AICR v1.2.0 release: https://github.com/NVIDIA/aicr/releases/tag/v1.2.0
- NVIDIA artifact verification: https://docs.nvidia.com/aicr/latest/user-guide/artifact-verification/
- Google k8s-aibom v1.6.2: https://github.com/GoogleCloudPlatform/k8s-aibom/releases/tag/v1.6.2
- Google native ML-BOM and signature confidence: https://github.com/GoogleCloudPlatform/k8s-aibom/tree/v1.6.2
