# Project governance

This is an independent **open research** repository, not a maintained production service. Contributions are welcome; support, release schedules and review deadlines are not promised.

## Decisions

- Decisions should be traceable to a concrete issue, documented experiment, negative control, security finding or upstream source.
- Maintainers decide whether to merge, revise or decline work. Large product features require *evidence of a real unmet need*, not only appealing architecture.
- `PAUSE_PRODUCT_BUILD` is the current product-investment decision. It does **not** prevent research corrections, tests, documentation improvements, interoperability fixes or independent security review.
- Material changes to threat assumptions, test methodology or the value claim should be recorded in `DECISIONS.md` and `EVIDENCE.md` alongside commands and results.

## Review standards

Contributions should preserve fail-closed evaluation, minimize privileges and external services, include adversarial tests, respect upstream licenses and avoid inventing claims of model execution. Do not merge sensitive cluster data or credentials into the public repository.

## How to participate

The project has no dedicated funded maintainer/reviewer team. An issue comment is a useful signal of interest, not an assignment or promise of response. Prefer small, reproducible contributions. Prioritize independently verified errors in the research record, unsafe trust-boundary assumptions and upstream parity over new product implementation.

No one should treat stars, forks, issue comments or an unreviewed PR as validated user demand.

Use [CONTRIBUTING.md](CONTRIBUTING.md) and the repository issue templates. Security reports are handled privately per [SECURITY.md](SECURITY.md) where a suitable channel is available. Community conduct follows [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
