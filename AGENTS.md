# Agent operating contract (2026-11-12)

- Scope: offline cross-plane assurance experiment. Never assert runtime truth solely from a BOM, a signature, or fixture tests.
- Remote `ZX7-Labs/runtime-assurance-lab` is **PUBLIC**. Do not push, open PRs, change visibility, create another remote, deploy, release, spend money, or read secrets without explicit authorization. Local-only work is allowed.
- Sequence: inspect -> design -> implement -> unit/integration/adversarial/performance tests -> fix -> retest -> critical review -> local checkpoint. Append commands, results, unknowns to `EVIDENCE.md`.
- Trust boundaries: intent from AICR-qualified exports; observations from opted-in k8s-aibom; signatures from Sigstore or explicitly trusted signers; policy from an externally pinned version. No source may self-assert its own trust root. Unknown/expired data cannot pass assurance.
- Use typed, explicit JSON contracts; `src/runtime_assurance_lab` remains free of Kubernetes SDK imports and networking. Adapters belong at edges; fail closed on input ambiguity.
- Do not copy upstream controller, Sigstore, or policy-engine implementations. Check upstream documentation/licenses before adding dependencies. No license selected for this private prototype.
- Reproduce: `PYTHONPATH=src pytest -q`; `PYTHONPATH=src python -m runtime_assurance_lab.cli demo`; `PYTHONPATH=src python -m runtime_assurance_lab.cli benchmark`.
- Stop if cross-plane use case is upstream-complete or meaningful real-world differentiation cannot be demonstrated with authorized, non-sensitive evidence. Do not claim production readiness or a market fit.
