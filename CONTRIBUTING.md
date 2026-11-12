# Contributing to Runtime Assurance Lab

Thank you for helping test a hard question: **does a separate cross-plane assurance layer add verifiable information beyond existing tools?** You do not need a GPU or cloud account to contribute to the offline research.

## Start here

1. Read the [README](README.md), [architecture/trust boundary](docs/ARCHITECTURE.md), [roadmap](docs/ROADMAP.md), and [Code of Conduct](CODE_OF_CONDUCT.md).
2. For a substantial idea, use the **Research proposal** issue template first. State what NVIDIA AICR, Google k8s-aibom or existing policy/Sigstore tools cannot already do, and how to falsify your claim.
3. For a small bug or regression, use the **Bug report** template, attach a minimized non-sensitive reproducer and state the expected `OK`/`DRIFT`/`UNKNOWN` behavior.
4. Fork the public repository, create a focused branch, and submit a pull request. Maintainers review changes; submissions are not automatically accepted.

**No GPU? No problem.** Start with the [portable reproduction guide](docs/REPRODUCIBILITY.md) and [contributor paths](docs/CONTRIBUTOR_PATHS.md). A small, well-documented negative result is preferable to an unscoped feature request.

**Available starting points:** [#1 Portability / quickstart](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/1), [#2 Equal-input upstream research](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/2), [#3 Public threat-model review](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/3). For a new idea use the issue templates.

**Want a specific, reviewable task?** Start with the [independent verification challenge](research/INDEPENDENT_REVIEW_CHALLENGE.md), including its fair-comparison method, contributor lanes, evidence rubric and safe-data rules. [#4](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/4) is for *potential* real G4 research partners, not public upload of evidence.

## Local development

```bash
python -m pip install -e ".[test]"
python -m pytest -q
python scripts/ci_smoke.py
python scripts/check_gates.py
python scripts/run_research_gate.py --verify-report results/research_gate.json
python -m compileall -q src tests scripts
```

`check_gates.py` validates **stored historical synthetic** acceptance evidence, not a fresh GPU benchmark. The research gate must continue to return `PAUSE_PRODUCT_BUILD` until credible external G4 data changes the investment decision.

On Windows PowerShell, the venv Python can be invoked as `.\\.venv\\Scripts\\python.exe` without changing script-execution policy; see the [portable guide](docs/REPRODUCIBILITY.md). A smoke result is not a claim that the application supports a real GPU.

CI uses Python **3.11 and 3.13**, a read-only token and CPU-only GitHub-hosted runners. Local development can use either supported version; GitHub CI must pass both. Do not introduce secrets, GPU dependencies, paid services, automatic network fetches into the library, new controllers or new trust formats as routine changes.

## What makes a strong pull request

- **Problem and scope:** a specific bug, falsifiable hypothesis or documented compatibility gap; link upstream behavior or reproducible evidence where relevant.
- **Security boundaries:** no `OK` on unauthenticated input; never trust a source-provided signature key, time or checkpoint merely because it was included in the payload.
- **Tests:** include both a positive and an adversarial/fail-closed control. State commands, exact results, and any Python-version differences.
- **Truth in reporting:** distinguish integrity from source authenticity; signed claims from runtime execution; synthetic metrics from actual detection latency; and upstream parity from distinct value.
- **Documentation:** update `PLAN.md`, `EVIDENCE.md` and/or `SECURITY_REVIEW.md` when behavior, evidence or threat assumptions change. Do not rewrite historical negative findings into wins.
- **Small, reviewable changes:** no unrelated reformatting, generated caches, private cluster data, secrets or vendor code copied into this repository.

### Good first areas

| Area | Helpful contribution | Why it matters |
| --- | --- | --- |
| CLI ergonomics | Improve clear error messages for invalid/unverifiable JSON | Safer fail-closed behavior |
| Regressions | Add deterministic tamper, Unicode, replay or malformed-evidence cases | Harder-to-break trust boundaries |
| Documentation | Reproduce quickstart on Linux/macOS/Windows and report discrepancies | Lower contributor onboarding cost |
| Comparative research | Independently verify a cited upstream feature and suggest an **equal-input** test | Stops building redundant code |

Any data from a real environment must be authorized, de-identified, legally shareable and approved for publication **before** a PR is opened. If you find a vulnerability, follow [SECURITY.md](SECURITY.md), **not** a public issue with exploit details.

## License for contributions

By submitting a contribution you agree to license it under this repository's **Apache License 2.0**. Do not submit code you lack the right to relicense. Preserve third-party copyright and licensing notices; avoid copying upstream source code merely to build an adapter.

There is no contributor SLA, production support commitment, or guaranteed roadmap. Comments expressing intent are helpful for avoiding duplicate work; no assignment, response or merge is guaranteed. For questions use [SUPPORT.md](SUPPORT.md). For shareable, accurate project positioning see the [maintainer launch playbook](docs/COMMUNITY_LAUNCH.md). Decisions prioritize clear evidence and safety over feature count.
