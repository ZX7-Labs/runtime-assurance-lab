# Choose a contribution that produces evidence

A GPU is **not** required to help. The project's goal is to test whether additional cross-plane runtime assurance is necessary at all—not to maximize feature count.

## Pick one small, reviewable task

| Path | Best for | First concrete output | Start |
| --- | --- | --- | --- |
| Reproduce | Students, Python developers, OS portability reviewers | Exact commit/OS/Python, commands and sanitized exit codes; one tested correction if needed | [Issue #1](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/1) |
| Audit vendor parity | Kubernetes/GPU/platform researchers | One pinned upstream feature, a fair same-input comparator, and a falsifier | [Issue #2](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/2) |
| Challenge trust | AppSec, supply-chain engineers | One source/clock/replay assumption and safe non-sensitive negative control | [Issue #3](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/3) |
| Review real-study protocol | Researchers, potential authorized operators | Critique blinded labels and evidence custody; **no live data in issues** | [Issue #4](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/4) |
| Packaging portability | Python packaging maintainers | Build and install an isolated wheel/sdist, report install and `ral --help` outcomes | [Issues](https://github.com/ZX7-Labs/runtime-assurance-lab/issues) |

For now, **documentation, reproduction, negative controls and independent review** are higher-value than adding a Kubernetes controller, new storage backend, signing service or detection promise. See the scientific [claims matrix](CLAIMS_AND_BASELINES.md).

## First contribution recipe

1. Read the [five-minute reproduction guide](REPRODUCIBILITY.md) and [contribution rules](../CONTRIBUTING.md).
2. Find a task that is still open; comment with **one** specific test you intend to do. You do not need to wait for assignment to run a local test. A maintainer response or merge is not guaranteed.
3. Work on synthetic public fixtures only. Record OS, commit and reproducible commands; avoid personal/cluster data.
4. Submit a small pull request with both expected and adverse outcomes. Say *not measured* instead of guessing.
5. Preserve the fail-closed `UNKNOWN` boundary. If you find a real vulnerability, use [private security reporting](../SECURITY.md), not a public exploit issue.

## Definition of a useful research PR

- **Claim:** one falsifiable statement or one documented issue.
- **Upstream alternative:** existing official functionality checked at pinned versions.
- **Evidence:** precise commands and outputs, with failure cases.
- **Negative control:** show how the claim could be false.
- **Scope:** no privileged agents, network upload or self-established trust root.
- **Result:** update docs and `EVIDENCE.md` if claims, tests or assumptions change.

A PR proving that an upstream tool already solves the proposed problem is valuable. A passing simulation alone is not evidence of a security or commercial advantage.

## Communication and credit

Comments, issue reports and PRs should be in clear technical English for broad review; language proficiency is **not** a gate, and concise examples or translations are welcome. Do not pressure maintainers for response times, imply endorsement or claim a contributor community before people actually participate. The [Code of Conduct](../CODE_OF_CONDUCT.md) and [governance](../GOVERNANCE.md) apply.
