# Independent verification challenge

**Status:** open call for reproducible research — **not** a verified product, funded program, security certification, or request for private infrastructure access.

**Question:** Given the **same** independently authenticated inputs, can a small cross-plane assurance consumer report a security-relevant intent-versus-observation mismatch that the existing combination of [NVIDIA AICR](https://github.com/NVIDIA/aicr), [Google k8s-aibom](https://github.com/GoogleCloudPlatform/k8s-aibom), and [Sigstore](https://www.sigstore.dev/)/policy tooling cannot already report with comparable accuracy, trust, freshness, and operational cost?

The default hypothesis is **no distinct product advantage yet demonstrated**. `PAUSE_PRODUCT_BUILD` remains active. **A rigorous negative result is a valuable contribution.** No new inventory controller, signing stack, or privileged collector is requested.

## Choose a contribution lane

| Lane | Requires | Where to start | Done when |
| --- | --- | --- | --- |
| 1. Reproduce and improve onboarding | Python 3.11+ on Linux, macOS or Windows | [#1 portability](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/1) | A complete command/exit-code record and a minimal tested docs/compatibility fix if needed |
| 2. Falsify the distinct-value hypothesis | Public upstream sources and ability to construct fair same-input controls | [#2 independent upstream comparison](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/2) | A pinned, reproducible, adverse **or** supportive finding and an upstream-complete comparator |
| 3. Independently challenge assurance safety | Threat-model and adversarial-test expertise | [#3 source-authentication review](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/3) | Documented trust-boundary assessment and safe negative/positive test cases |
| 4. Explore real G4 feasibility | Public research experience; only later, separately authorized infrastructure | [#4 G4 research partners](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/4) | A feasibility/evidence-custody assessment, **not** a public upload of live data |

## A 15–30 minute CPU-only first reproduction

From a new, nonprivileged checkout (a shell with Python 3.11+):

```bash
git clone https://github.com/ZX7-Labs/runtime-assurance-lab.git
cd runtime-assurance-lab
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/ci_smoke.py
python scripts/run_research_gate.py --verify-report results/research_gate.json
```

Record the exact commit SHA, OS, Python version, commands, exit codes and any failing test name. The **expected** research decision is `PAUSE_PRODUCT_BUILD`; success of the gate confirms that report is reproducible, **not** that a product should ship. Existing historical synthetic acceptance checks are available with `python scripts/check_gates.py`, but do not measure GPU behavior.

## Lane 2: a fair comparison, not a strawman

Submit **one concrete, falsifiable** claim. A useful entry states:

1. **Gap claim:** exact input, workload identity, desired response, failure consequence and the user who needs it.
2. **Existing-tools baseline:** pinned versions/source locations, real vendor command or policy, and the *minimal composition* of existing tools—not an intentionally weaker dummy comparator.
3. **Same-input method:** shared source material and policy, separately authenticated signer/root/intent, trusted time and replay state, identical decision latency budget, and source-availability controls.
4. **Negative controls:** stale/missing input, mismatched workload, false `verified` label, tampering, unauthorized signer and replay/rollback. A signed statement by an approved but dishonest observer does **not** prove actual GPU execution.
5. **Results:** exact reproduction commands, expected/actual judgments, false `OK` count, real-drift recall when ground truth exists, reproducibility, relevant CPU/memory/network costs and denominators. Report unavailable measurements as unavailable.
6. **Decision:** if upstream composition already covers the gap, recommend stopping our separate implementation and pointing to or contributing the smallest useful upstream fix.

Start with the existing [preregistered G4 study design](g4_independent_validation_protocol.md), [upstream audit](../UPSTREAM_AUDIT.md), and [evidence ledger](../EVIDENCE.md). The preexisting 600-case synthetic same-input comparator found **zero disagreements**, which is **not** evidence of real-world value.

## Lane 3: trust boundaries worth attacking (responsibly)

Focus on origin identity; exact-byte/canonicalization mismatch; externally pinned key, policy and intent; signed-but-false source claims; trusted clock/freshness; duplicate consumption, rollback, root rotation and recovering from damaged checkpoint state. The SQLite checkpoint proof is local only. A real attacker able to roll back **both** the database and the operator pin can defeat it.

Report **potential or exploitable vulnerabilities privately** following [SECURITY.md](../SECURITY.md), never as a public exploit recipe. Public PRs may add generalized safe regression tests after coordinated disclosure.

## Lane 4: real-world validation cannot begin from an issue comment

Any future G4 test needs **explicit operator approval** plus authentic, legally shareable, matching AICR and AIBOM records from **one and the same workload**, independently maintained trust roots, issuer policy, clock and monotonic checkpoint, blinded labels and authorized clusters. A public repository fixture does not meet this requirement. No cluster or secret access is currently authorized by this challenge.

**Do not upload** customer workloads, exports, signing keys, credentials, internal URLs, infrastructure addresses, private attestations, or full exploit material to public GitHub. No confidential evidence intake path has been independently verified. A private channel and a written authorization scope must be agreed *before* any sensitive data is exchanged.

## Contribution acceptance rubric

| Gate | Requirement |
| --- | --- |
| Reproducible | Pin commit and upstream version; provide commands and exit codes |
| Fair | Identical inputs and policy for the project and strongest existing-tool composition |
| Secure | No untrusted `OK`, no self-pinned trust root, no public sensitive evidence |
| Falsifiable | Include an explicit way the claim could be shown false |
| Honest | Separate source assertion, cryptographic integrity, source authenticity and actual execution |
| Actionable | State the smallest upstream or project action and stop condition |

**Maintainer promise:** contributions receive review on a best-effort basis, with no guaranteed response time. We will not claim a verified reviewer, contributor team, running GPU trial, user demand or a real-world product gap until such evidence actually exists. All project code remains [Apache-2.0](../LICENSE).
