# Security policy

## Supported status

This is an **experimental offline research project**. There is no supported production release, service, authenticated Kubernetes collector or independently operated trust/checkpoint authority. A passing signature authenticates an authorized *assertion* under externally established pins; it does **not** establish physical model/GPU execution.

See [SECURITY_REVIEW.md](SECURITY_REVIEW.md) for known issues. In particular, an authorized malicious signer can lie, and a restored SQLite checkpoint plus a restored operator pin defeats local rollback detection.

## Report a vulnerability privately

**Do not disclose exploit steps, keys, private manifests or credentials in public issues or pull requests.**

Use the repository's GitHub **Security → Report a vulnerability** private-reporting option if it is enabled. If that option is unavailable, reach the maintainers via an established private channel *before* sending details; this repository does not publish a verified security email address. Do not assume public issues are private.

A useful private report includes the affected commit, minimal synthetic reproducer, expected/actual behavior, threat assumptions, and whether a positive `OK` was obtained without an independently pinned trust root. Do not include real cluster credentials or other users' data.

We will evaluate issues on a best-effort basis; no response deadline, coordinated disclosure timeline or security guarantee is promised.

## Unsafe assumptions to avoid

- A JSON `verified` label is **not** independent source authentication.
- An exact SHA-256 match proves **integrity against the provided pin**, not authority over the pin.
- A signed collector statement is not proof that a model actually ran.
- Keys, timestamps and checkpoints inside the same attacker-controlled source are not independent roots of trust.
- The offline SQLite checkpoint harness is not an external monotonic ledger.

Do not deploy this project to live clusters or process private source records based on its current CI results.
