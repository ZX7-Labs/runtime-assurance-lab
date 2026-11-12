## Problem and motivation

<!-- Link issue or precise reproducible bug. For a feature, cite the upstream gap. -->

## Changes and boundaries

<!-- Which modules? Does this preserve UNKNOWN for untrusted evidence? -->

## Evidence and verification

- [ ] `python -m pytest -q`
- [ ] `python scripts/ci_smoke.py`
- [ ] `python scripts/check_gates.py` (historical stored evidence)
- [ ] `python scripts/run_research_gate.py --verify-report results/research_gate.json`
- [ ] No private evidence, secrets, production claims or copied upstream source
- [ ] Updated `EVIDENCE.md` / `SECURITY_REVIEW.md` if the claim or trust boundary changed

Exact results, environment and limitations:

## Security review

<!-- Positive + adversarial test cases, key/pin/time/replay assumptions; never paste a real exploit. -->
