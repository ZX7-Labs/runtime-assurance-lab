# runtime-assurance-lab

Private-by-default local research checkpoint for correlated AI deployment-intent/runtime-observation drift, with signed **synthetic** evidence lineage. Not a Kubernetes controller, not a Sigstore replacement, and not production-ready.

## Run without network, GPU, Docker, Kubernetes or secret access

Requires Python >=3.11 and local `cryptography>=42,<48` (tested 46.0.4); tests use pytest 9.0.2. In the provided runtime these are already installed. No automatic downloads are performed.

```sh
cd runtime-assurance-lab
PYTHONPATH=src python -m runtime_assurance_lab.cli demo --fixtures fixtures --output results/demo
PYTHONPATH=src python -m runtime_assurance_lab.cli verify --journal results/demo/journal.json --trust results/demo/trust-public.json --checkpoint results/demo/checkpoint.json
PYTHONPATH=src python -m runtime_assurance_lab.cli evaluate --intent fixtures/intent.json --observation fixtures/clean.json --now 2026-11-12T03:25:00Z
PYTHONPATH=src python -m runtime_assurance_lab.cli benchmark --output results/benchmark.json
PYTHONPATH=src pytest -q
```

`evaluate` exits 0 only for an `OK` finding, 2 for anything requiring attention, 3 for invalid input. `verify` exits 0 only if cryptographic *and* semantic proof checks succeed. `demo` uses ephemeral generated signers (no private keys written). Do not treat the colocated output public keys/checkpoint as an independent trust anchor.

- `AGENTS.md`: guardrails for future agents.
- `PLAN.md` / `DECISIONS.md`: hypothesis, two competing architectures, scope and acceptance gates.
- `UPSTREAM_AUDIT.md`: current official-project capabilities, licenses, integration points and sources.
- `SECURITY_REVIEW.md`: explicit critical review and surviving vulnerabilities.
- `EVIDENCE.md`: executed commands/results and blockers, without claims of live validation.
- `results/`: machine-readable example output and benchmark.

**No outbound repository change**: Connected `ZX7-Labs/runtime-assurance-lab` was confirmed `public` on 2026-11-12 although this task requires private-by-default. This local checkpoint must not be pushed until the visibility conflict is resolved explicitly.
