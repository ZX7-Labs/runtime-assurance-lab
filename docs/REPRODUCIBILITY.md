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

## Wheel and sdist check (issue #5)

One independent run of the build-and-install path, on a fresh checkout. This is a single observation on one OS and Python version, not a statement about other platforms, and it does not replace the CI matrix.

- Commit: `efa069cdfbaae19da610dd98658e42a8adb98f77` (clean checkout of `main`).
- Environment: Windows 11 (10.0.26300), x86-64, Python 3.14.4, pip 26.0.1, `build` from PyPI, normal build isolation with network access to PyPI (setuptools and, at install time, `cryptography` and `cffi` were downloaded; installed `cryptography` 47.0.0). The project's declared range is Python 3.11 and 3.13; 3.14 is outside the CI matrix.

Commands (a disposable build venv; nothing is committed, and `dist/` is outside the checkout):

```sh
python -m venv build-env
build-env/bin/python -m pip install build        # Windows: build-env\Scripts\python.exe
build-env/bin/python -m build --wheel --sdist --outdir ../dist .
python -m venv env-wheel && env-wheel/bin/python -m pip install ../dist/runtime_assurance_lab-0.1.0-py3-none-any.whl
python -m venv env-sdist && env-sdist/bin/python -m pip install ../dist/runtime_assurance_lab-0.1.0.tar.gz
```

Observed:

- Build succeeded and produced `runtime_assurance_lab-0.1.0-py3-none-any.whl` (22 entries) and `runtime_assurance_lab-0.1.0.tar.gz` (49 entries).
- Wheel metadata: `License-Expression: Apache-2.0`, `LICENSE` and `NOTICE` under `dist-info/licenses/`, and the README as the long description. The sdist contains `LICENSE`, `NOTICE`, `README.md`, `pyproject.toml`, `src/` and `tests/` (but not `fixtures/`, `scripts/` or `docs/`, so the `fixtures/` paths below are from the checkout).
- Both installs succeeded; the package imports from `site-packages`, not from the checkout.

From a directory outside the repository (`FIX` is the checkout's `fixtures/` directory), with each installed `ral`:

| Command | Expected | Observed |
| --- | --- | --- |
| `ral --help` | usage, exit 0 | usage listing 11 subcommands, exit 0 (wheel and sdist installs) |
| `ral evaluate --intent FIX/intent.json --observation FIX/clean.json --now 2026-11-12T03:25:00Z` | `UNKNOWN`, exit 2 | `{"rules": ["SOURCE_AUTHENTICITY_UNVERIFIED"], "status": "UNKNOWN", "workload": "lab/demo"}`, exit 2 (both installs) |
| `ral demo --fixtures FIX --output demo` then `ral verify --journal demo/journal.json --trust demo/trust-public.json --checkpoint demo/checkpoint.json` | verified | `demo` exit 0; `verify` prints `{"reason": "DECISIONS_RECOMPUTED", "verified": true}`, exit 0 (wheel install) |

Not checked: the test suite and `scripts/` against the installed package (the wheel does not contain them), Linux and macOS, Python 3.11 and 3.13, and an offline or `--no-build-isolation` build. No packaging defect was found, so no code change is proposed. The `ral` wrapper in a venv is `ral.exe` on Windows.

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
