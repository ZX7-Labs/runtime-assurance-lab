<div align="center">

# Runtime Assurance Lab

**Know what AI workload evidence proves—and what it does not.**

[![CI](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/workflows/offline-assurance.yml/badge.svg)](https://github.com/ZX7-Labs/runtime-assurance-lab/actions/workflows/offline-assurance.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](pyproject.toml)

*A small, open-source research laboratory for testing claims about AI workload intent, observed configuration and evidence trust.*

[Run locally](#get-started) · **[Choose a contribution](docs/CONTRIBUTOR_PATHS.md)** · [Research claims](docs/CLAIMS_AND_BASELINES.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

</div>

> [!IMPORTANT]
> **Research prototype, not production assurance.** The current investment decision is `PAUSE_PRODUCT_BUILD`: we have **not** demonstrated an advantage over a correctly configured combination of existing NVIDIA AICR, Google k8s-aibom and signature/policy tools. We welcome rigorous contributions that *test* this hypothesis, not unverified feature claims.

## The question

A deployment recipe says **what should run**. An inventory report says **what a collector observed**. A signature can tell us **who signed an assertion**. None of these alone proves **which model actually executed on a GPU**.

Can independent, trustworthy cross-plane correlation detect meaningful drift that upstream tools—used together with the same evidence and policy—would otherwise miss?

**We do not know yet.** This repository makes that question reproducible and falsifiable rather than presenting synthetic passing tests as proof. It is a research platform for independent reviewers, **not** a new AI runtime monitor or a production assurance service.

| We have | We do **not** have |
| --- | --- |
| Strict, offline Python contracts and fail-closed evaluation | Live Kubernetes or GPU execution attestation |
| AICR RecipeResult and k8s-aibom JSON research adapters | A trusted live collector or Kubernetes controller |
| Ed25519 source-assertion tests with externally supplied pins | An independently operated trust/monotonic-checkpoint service |
| Tamper, replay, rollback and forged-source regression tests | An audited production security boundary |
| Reproducible synthetic experiments and vendor-native CPU release checks | A demonstrated advantage over upstream tools or real customer validation |

## Start contributing: one claim, one reproduction, one review

You can contribute **without a GPU, cluster, account credentials or existing access to NVIDIA/Google infrastructure**. Choose a task matching your background:

- **First contribution:** [#1 · reproduce the quickstart on macOS/Windows](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/1) (`good first issue`).
- **Research:** [#2 · try to falsify the standalone-product hypothesis](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/2) using real upstream capabilities and **fair same-input controls**.
- **Security:** [#3 · independently review source authenticity and replay boundaries](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/3) (disclose vulnerabilities privately).
- **Real-world validation:** [#4 · explore an authorized, privacy-safe G4 research partnership](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/4) (do **not** post live data).
- **Packaging:** [#5 · independently test wheel/sdist and installed CLI](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/5) (no GPU).
- **Metrics review:** [#6 · verify benchmark definitions and limitations](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/6) (no GPU).

**[Pick a concrete first task](docs/CONTRIBUTOR_PATHS.md)** · [Independent challenge and evidence rubric](research/INDEPENDENT_REVIEW_CHALLENGE.md) · [Reproduction instructions for Linux, macOS and Windows](docs/REPRODUCIBILITY.md).

We welcome rigorous findings that tell us **not to build** a redundant product. No external reviewer, real G4 operator, community adoption, or live GPU evidence is claimed yet.

## Get started

You need **Python 3.11+**. No GPU, cluster, credentials or Docker required for local tests.

```bash
git clone https://github.com/ZX7-Labs/runtime-assurance-lab.git
cd runtime-assurance-lab
python -m pip install -e ".[test]"
python -m pytest -q
```

Explore the synthetic signed-journal demo (output is generated outside the checkout):

```bash
ral demo --fixtures fixtures --output results/demo
ral verify --journal results/demo/journal.json \
  --trust results/demo/trust-public.json \
  --checkpoint results/demo/checkpoint.json
python scripts/run_research_gate.py --verify-report results/research_gate.json
```

The demo **creates its own keys and trust data** in an ignored folder. A successful `verify` verifies internal consistency of a self-generated example—not independent source identity, a real cluster or GPU execution. For a PowerShell/Windows invocation that does not rely on POSIX line continuations, use the [portable reproduction guide](docs/REPRODUCIBILITY.md).

To see the fail-closed behavior:

```bash
ral evaluate --intent fixtures/intent.json \
  --observation fixtures/clean.json --now 2026-11-12T03:25:00Z
# Deliberately returns UNKNOWN (exit code 2): source authenticity is unverified.
```

For additional commands, run `ral --help`. A research report showing `PAUSE_PRODUCT_BUILD` is a **correct** outcome, not a broken test.

## How the research fits together

```text
Operator intent (JSON)        Upstream recipe / AIBOM export (JSON)
           |                               |
           +-------- strict parsing -------+
                           |
                 identity / byte pins
                           |
              trust boundary (NOT implicit)
                           |
            offline evaluator / replay checks
                           |
                  OK / DRIFT / UNKNOWN / STALE
                           |
                 evidence and falsification
```

**Important:** the plain `evaluate`/AIBOM/recipe adapters and unsigned receipts do **not** issue authenticated `OK`. The separately scoped `evaluate-authenticated` path can authenticate a **signed source assertion** only when externally established identity, trust/intent pins, time and replay checkpoint are supplied. The local SQLite checkpoint is a simulation, not an independent rollback authority. A dishonest *authorized* signer can still lie. [Architecture and trust boundaries](docs/ARCHITECTURE.md).

## What is and is not verified

**Read the [claims and baseline matrix](docs/CLAIMS_AND_BASELINES.md) before quoting any benchmark.** Existing local microsecond measurements are not end-to-end detection latency or Kubernetes CPU/memory overhead. In a historical 600-case synthetic **same-input** reference comparison, there were **zero disagreements**—no verified incremental advantage. The weak "naive" baseline is not a NVIDIA/Google/policy baseline.

- **Verified in CI:** Python 3.11/3.13 tests; synthetic/adversarial source-authentication checks; pinned public **repository test fixtures**; constrained research gates. Native CPU experiments have exercised published vendor CLIs and checked release signatures/checksums; see the exact [evidence ledger](EVIDENCE.md).
- **Not verified:** an actual model running on a GPU, the origin of a live workload observation, same-workload AICR↔AIBOM attestation, real detection latency or market demand. [Independent G4 validation protocol](research/g4_independent_validation_protocol.md).
- **Existing work matters:** [NVIDIA AICR](https://github.com/NVIDIA/aicr) and [Google k8s-aibom](https://github.com/GoogleCloudPlatform/k8s-aibom) are already Apache-2.0 open source and cover much of the underlying functionality. [Upstream overlap audit](UPSTREAM_AUDIT.md). We are **not** rebuilding their controllers or signing stack.

## Contributing

**Good first contributions:** reproduce a failing test on a clean machine; improve malicious-input regression coverage; tighten error messages without converting `UNKNOWN` to `OK`; review the upstream comparison protocol; or contribute independent, citable research on a concrete gap.

**Pick an open task:** [#1 · reproduce the quickstart](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/1) (beginner-friendly), [#2 · independent upstream comparison](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/2), or [#3 · trust-boundary review](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/3).

Start with [CONTRIBUTING.md](CONTRIBUTING.md), the [contributor paths](docs/CONTRIBUTOR_PATHS.md), [reproducibility guide](docs/REPRODUCIBILITY.md), [architecture](docs/ARCHITECTURE.md), and [research roadmap](docs/ROADMAP.md). Open a [research proposal](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/new/choose) before proposing a large feature. Do not publish credentials, private cluster exports, private signing keys or sensitive model information in an issue/PR.

Development requires **evidence, not confidence**: run `python -m pytest -q`, `python scripts/ci_smoke.py`, `python scripts/check_gates.py` (stored historical evidence), and `python scripts/run_research_gate.py --verify-report results/research_gate.json` from the repository root. Real G4 work requires authorization and independent custody. [Security reporting](SECURITY.md).

## Repository map

| Path | Purpose |
| --- | --- |
| [`src/runtime_assurance_lab/`](src/runtime_assurance_lab/) | Offline contracts, comparison, provenance and replay |
| [`tests/`](tests/) + [`fixtures/`](fixtures/) | Deterministic and adversarial tests; **synthetic** fixtures |
| [`scripts/`](scripts/) | Reproduction, benchmarks, research and smoke checks |
| [`results/`](results/) | Historical machine-readable research results, **not product SLAs** |
| [`research/`](research/) | G4 operator handoff, vendor comparison and preregistered testing |
| [`PLAN.md`](PLAN.md) · [`EVIDENCE.md`](EVIDENCE.md) | Milestones, limits, commands and archived findings |
| [`docs/CLAIMS_AND_BASELINES.md`](docs/CLAIMS_AND_BASELINES.md) | Truth-in-metrics matrix; existing vendor overlap and falsifiers |
| [`docs/CONTRIBUTOR_PATHS.md`](docs/CONTRIBUTOR_PATHS.md) | Specific no-GPU tasks for first-time contributors |

## License and independence

**Apache License 2.0.** See [LICENSE](LICENSE) and [NOTICE](NOTICE). Copyright holders retain their rights. Dependencies and externally referenced upstream projects retain their own licenses. This project is independently maintained and is **not affiliated with or endorsed by NVIDIA, Google or Sigstore**.

*Open source is the invitation to test the hypothesis—not a claim that the hypothesis has already been proven.*
