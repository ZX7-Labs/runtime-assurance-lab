# Reproduce the research without a GPU

This is an **offline, synthetic-evidence research harness**, not a production agent or a live GPU/runtime attestor. A passing test does not authenticate the truth of a collector's real-world claims. For the current decision, see [the research gate](../results/research_gate.json).

## Prerequisites and boundaries

- Python 3.11+ (CI currently tests 3.11 and 3.13); Git; a local terminal.
- Network is needed for the initial Git clone and Python dependency installation, **not** to run the installed offline research tests.
- No Docker, GPU, Kubernetes API, cloud credentials, production data, tokens or signing keys are required.
- Do not upload live AICR bundles, AIBOMs, private keys, client records or infrastructure details to GitHub. Use [SECURITY.md](../SECURITY.md) for vulnerabilities.

## Cross-platform first run

Use a disposable virtual environment. From Linux/macOS:

```sh
git clone https://github.com/ZX7-Labs/runtime-assurance-lab.git
cd runtime-assurance-lab
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
python -m pytest -q
```

From Windows PowerShell (with Python on PATH):

```powershell
git clone https://github.com/ZX7-Labs/runtime-assurance-lab.git
cd runtime-assurance-lab
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
```

The Windows example invokes the venv Python directly; changing PowerShell's script-execution policy is **not** required. If the installed Python is incompatible or cannot build the package, record the exact error instead of patching security settings. The CI matrix, rather than this document, is the source of the latest passing test count.

## Portable synthetic demo

Run these from the checkout after installation. They write to the **ignored** `results/demo/` directory; do not commit its self-generated keys, journal or output.

```sh
python -m runtime_assurance_lab.cli demo --fixtures fixtures --output results/demo
python -m runtime_assurance_lab.cli verify --journal results/demo/journal.json --trust results/demo/trust-public.json --checkpoint results/demo/checkpoint.json
```

The demo constructs its **own** signing keys and a matching local checkpoint. A successful verification proves that a synthetic journal's internal consistency was checked against its co-generated files—not independent source authenticity, a production rollback anchor or actual GPU execution.

To observe the intentional rejection of untrusted data:

```sh
python -m runtime_assurance_lab.cli evaluate --intent fixtures/intent.json --observation fixtures/clean.json --now 2026-11-12T03:25:00Z
```

Expected research behavior: `UNKNOWN`, with a nonzero exit (2) because an unsigned complete-looking claim cannot become authenticated `OK`. Do **not** treat this expected nonzero exit as a broken test.

## Independent checks

```sh
python scripts/ci_smoke.py
python scripts/check_gates.py
python scripts/run_research_gate.py --verify-report results/research_gate.json
python -m compileall -q src tests scripts
```

- `ci_smoke.py` exercises CLI/negative controls on a CPU.
- `check_gates.py` verifies **stored historical synthetic acceptance results**, not a fresh benchmark.
- `run_research_gate.py` must report `PAUSE_PRODUCT_BUILD` and `report_matches=true`: this is an investment **no-go**, not a test failure.
- Python module compilation is a syntax check, not a security audit.

See [recorded commands and results](../EVIDENCE.md). Historical synthetic measurements cannot be compared to NVIDIA's published controller CPU/memory numbers: they measure different systems under different conditions.

## Interpret the four verdicts

| Status | Meaning | Do not conclude |
| --- | --- | --- |
| `OK` | Qualified, explicitly scoped **source assertion** matches pinned intent after independent gate assumptions | A model physically executed on a GPU |
| `DRIFT` | A trusted-enough assertion contains an intent mismatch | Malicious execution or a witnessed GPU event |
| `UNKNOWN` | Source, identity, evidence or integrity is insufficient | That the system is healthy |
| `STALE` | Observation is too old for the configured freshness window | That current intent matches or differs |

The public unauthenticated `evaluate` path returns `UNKNOWN` for otherwise complete matching **and** mismatching claims. Source authentication is a separate, heavily qualified research path; a caller-supplied `verified` string cannot bypass it.

## What a useful reproduction report contains

Open a [reproduction report](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/new/choose), or improve [issue #1](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/1):

- Git commit SHA (`git rev-parse HEAD`), OS, architecture, Python version, clean/dirty checkout.
- Exact commands, exit codes and *sanitized* outputs (especially unexpected nonzero exits).
- Expected and observed status; whether anything required a GPU, cluster or network.
- Minimal synthetic reproducer; which existing test or upstream source backs the claim.
- Never paste live workloads, credentials, internal URLs or private evidence.

A reproduced limitation, a portability failure or a result showing existing vendor tools already solve a problem is a **successful research contribution**.
