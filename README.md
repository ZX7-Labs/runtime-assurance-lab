# runtime-assurance-lab

Publicly accessible, unlicensed research checkpoint for correlated AI deployment-intent/runtime-observation drift, with signed **synthetic** evidence lineage. Not a Kubernetes controller, not a Sigstore replacement, and not production-ready.

## Run without network, GPU, Docker, Kubernetes or secret access

Requires Python >=3.11 and local `cryptography>=42,<48` (tested 46.0.4); tests use pytest 9.0.2. In the provided runtime these are already installed. No automatic downloads are performed.

```sh
cd runtime-assurance-lab
PYTHONPATH=src python -m runtime_assurance_lab.cli demo --fixtures fixtures --output results/demo
PYTHONPATH=src python -m runtime_assurance_lab.cli verify --journal results/demo/journal.json --trust results/demo/trust-public.json --checkpoint results/demo/checkpoint.json
PYTHONPATH=src python -m runtime_assurance_lab.cli evaluate --intent fixtures/intent.json --observation fixtures/clean.json --now 2026-11-12T03:25:00Z
PYTHONPATH=src python -m runtime_assurance_lab.cli evaluate-aibom --intent fixtures/intent.json --aibom fixtures/aibom-v1beta1-synthetic.json --now 2026-11-12T03:25:00Z
PYTHONPATH=src python -m runtime_assurance_lab.cli benchmark --output results/benchmark.json
PYTHONPATH=src pytest -q
```

`evaluate-aibom` is an offline, **version-pinned** Google k8s-aibom `v1.6.2` AIBOM/v1beta1 JSON adapter, with a **synthetic** CR sample. It performs no Kubernetes API calls, rejects inconsistent input, leaves unavailable digests null and intentionally returns `UNKNOWN`/exit 2 for the sample. The AIBOM summary alone is not a cryptographically trusted runtime attestation.

`evaluate` exits 0 only for an `OK` finding, 2 for anything requiring attention, 3 for invalid input. `verify` exits 0 only if cryptographic *and* semantic proof checks succeed. `demo` uses ephemeral generated signers (no private keys written). Do not treat the colocated output public keys/checkpoint as an independent trust anchor.

- `AGENTS.md`: guardrails for future agents.
- `PLAN.md` / `DECISIONS.md`: hypothesis, two competing architectures, scope and acceptance gates.
- `UPSTREAM_AUDIT.md`: current official-project capabilities, licenses, integration points and sources.
- `SECURITY_REVIEW.md`: explicit critical review and surviving vulnerabilities.
- `EVIDENCE.md`: executed commands/results and blockers, without claims of live validation.
- `results/`: machine-readable example output and benchmark, including an offline synthetic AIBOM adapter processing baseline (`python scripts/bench_aibom_adapter.py`).

## Public GitHub Actions — offline test automation

`.github/workflows/offline-assurance.yml` runs on pushes to `main`, pull requests, and manual dispatch. It uses free **standard** Linux runners, Python 3.11/3.13, pinned checkout/setup-python action SHAs, a read-only repository token, and no retained credentials, secrets, deployment, external cluster, GPUs or paid runners. It installs version-constrained test dependencies from PyPI; constraints are **not** hash-locked.

The job runs `python -m pytest -q`, compile checks, `python scripts/ci_smoke.py` and `python scripts/check_gates.py`. The smoke executes real Python processes using **synthetic** fixtures, including expected `UNKNOWN` for AIBOM and rejection of a modified signed journal. `check_gates.py` checks **stored historical** synthetic benchmark output; it does not benchmark each runner or prove runtime assurance. A green badge demonstrates the code path on hosted CI, not a GPU/Kubernetes validation.

**Publication authorization:** On 2026-11-12 the user explicitly approved the existing public repository and application of the work. Public repository visibility does **not** grant a reuse/distribution license. This code is an offline, synthetic prototype only; real-cluster data collection, release packaging, paid services and production deployment remain unauthorized.
