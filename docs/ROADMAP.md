# Research roadmap — prove value before building a product

**Current investment decision: `PAUSE_PRODUCT_BUILD`.** This is a research status, not abandonment of the question and not permission to deploy. The long-term technical standard remains high; it is the *evidence for making a standalone product* that is missing.

| Stage | Status | Evidence required |
| --- | --- | --- |
| M1–M7: offline adapters, adversarial provenance, signed-claim and replay experiments | ✅ Research complete | Tests/decisions recorded in `EVIDENCE.md` |
| M8–M10: upstream overlap, competitor control, safe handoff | ✅ Research complete | Negative controls, reproducible reports |
| M11: vendor-native official release CPU verification | ✅ Research complete | Pinned release hashes and vendor-native CI logs |
| Open-source community foundation | ✅ License/docs/issue templates | Public SPDX license, reproducible tests, contributor guidance |
| Independent reviewer / G4 partner recruitment | **OPEN CALL — no third-party validation recorded** | [Review challenge](../research/INDEPENDENT_REVIEW_CHALLENGE.md), [potential operator coordination](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/4) |
| G4: real same-workload, equal-input validation | ⛔ Blocked | Approved cluster; independent signer/root/clock/rollback custody; matching AICR + AIBOM; blinded drift injections; real CPU/RAM/latency |
| G5: product decision and supportability | ⛔ Blocked | Credible incremental value, users, independent threat and licensing review |

## Ways to help **without a GPU**

- Audit documented upstream capabilities using pinned vendor releases and record corrections with citations.
- Reproduce and improve synthetic security counterexamples, preserving the absence of `OK` for untrusted data.
- Reproduce Python 3.11/3.13 CI across environments and improve the developer experience.
- Improve the preregistered [G4 comparison protocol](../research/g4_independent_validation_protocol.md) without overstating its results.

## What would change the roadmap

A legally shareable real evidence pair from **the same workload**, independently pinned trust/issuer identity and checkpoint, authorized scoped clusters with controlled ground truth and an honest baseline composed of existing vendor tools.

The *go/no-go* experiment must compare equal inputs, not a deliberately weak comparator. If upstream composition has equivalent verified behavior, **stop the standalone product** and consider a targeted upstream contribution. If a repeatable, security-relevant gap is demonstrated, decide the smallest solution and seek independent review **before** expanding architecture.

We do not assign a completion percentage or date to G4/G5: no valid dataset, scope approval or operator is yet available. Do not accept synthetic pass counts as substitutes.
