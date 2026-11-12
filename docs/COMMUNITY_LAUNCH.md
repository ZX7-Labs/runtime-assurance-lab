# Community launch playbook (maintainer guide)

**Status: public independent research; NOT production security software.** Use this only after the linked README, contributor commands and CI remain green. Announcement is a request to **test and falsify**, not a claim of product availability, model execution attestation, independent security certification, or customer adoption.

## One-sentence positioning

> Runtime Assurance Lab is a small Apache-2.0, CPU-only research harness for asking whether authenticated AI deployment intent can be compared with Kubernetes AI workload observations in a way existing NVIDIA AICR, Google k8s-aibom and Sigstore/policy tools do not already cover.

Do not call it an AI agent, a production runtime monitor, an NVIDIA/Google partnership, a GPU model execution proof or a verified commercial startup.

**Canonical links:** [repository](https://github.com/ZX7-Labs/runtime-assurance-lab) · [first contribution](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/1) · [wheel/sdist check](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/5) · [metrics audit](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/6) · [vendor parity audit](https://github.com/ZX7-Labs/runtime-assurance-lab/issues/2) · [claim matrix](CLAIMS_AND_BASELINES.md) · [reproduction guide](REPRODUCIBILITY.md).

## Posts suitable for adaptation

### Short post (X/Mastodon/Bluesky)

> Open-source research: can we distinguish AI workload *intent* from signed-but-not-necessarily-true runtime *claims*? Runtime Assurance Lab has offline Python tests and a falsifiable comparison plan. **Not production-ready; real GPU evidence and an advantage over NVIDIA AICR + Google k8s-aibom remain unproven.** Looking for reproducibility, AppSec and vendor-parity reviewers—no GPU required. https://github.com/ZX7-Labs/runtime-assurance-lab

### Professional / LinkedIn

> I'm opening Runtime Assurance Lab (Apache-2.0) for independent review. The question is narrow: does a separate evidence-correlation layer find meaningful AI workload drift beyond a properly configured composition of NVIDIA AICR, Google k8s-aibom and existing signing/policy tools?
>
> The repository contains a CPU-only Python research harness, reproducible synthetic/adversarial tests, negative findings, an upstream-coverage audit and a preregistered real-validation protocol. **It has not demonstrated GPU model execution, an independent security boundary, incremental product value, or market demand.** The research decision is `PAUSE_PRODUCT_BUILD`.
>
> Useful ways to contribute: reproduce the quickstart on another OS, verify one upstream capability with cited evidence, challenge a source-authentication assumption safely, or critique the fair same-input test design. A result showing no need for an additional product is welcome.
>
> Repo and contributor entry points: https://github.com/ZX7-Labs/runtime-assurance-lab

### Community discussion / Reddit

> **Seeking technical criticism, not signups:** Would you build a separate cross-plane AI workload assurance component when AICR, k8s-aibom and policy/signature tools already exist?
>
> I published an offline, synthetic Python research harness with fail-closed provenance checks and a no-go research gate. I am specifically looking for a missed upstream capability, a falsifiable same-input comparison, or an error in the evidence assumptions. No GPU is needed to reproduce the tests.
>
> What would you try to falsify first? Code, limitations and open issues: https://github.com/ZX7-Labs/runtime-assurance-lab
>
> (No proof of real model execution or validated product advantage is claimed.)

Follow each community's posting/self-promotion rules. **Do not** cross-post identical solicitations rapidly, mass-mention NVIDIA/Google engineers, announce unofficial endorsement or collect private customer evidence in public comments.

### हिंदी में संक्षिप्त पोस्ट

> मैंने Runtime Assurance Lab को ओपन-सोर्स (Apache-2.0) रखा है। सवाल है: NVIDIA AICR, Google k8s-aibom और मौजूदा Sigstore/policy टूल्स के रहते, क्या AI workload के इरादे और observed evidence के बीच फर्क जाँचने के लिए अलग सिस्टम चाहिए?
>
> अभी CPU पर चलने वाला research prototype, synthetic/adversarial tests और साफ limitations हैं। **असली GPU execution या अलग product value साबित नहीं हुई है।** Python, Kubernetes, security और research contributors से independent review चाहिए; GPU जरूरी नहीं। नेगेटिव रिजल्ट भी स्वीकार है।
>
> https://github.com/ZX7-Labs/runtime-assurance-lab

## GitHub metadata to set manually

Some settings are not available through the repository-file API; an owner should inspect [Settings](https://github.com/ZX7-Labs/runtime-assurance-lab/settings), not assume they were changed.

- **About → Description:** `Offline AI workload evidence research: intent vs observation, trust boundaries, reproducible tests; not production assurance.`
- **About → Website (optional):** use the repo's documentation, not a nonexistent marketing site.
- **Topics:** `ai-security`, `kubernetes`, `supply-chain-security`, `sigstore`, `reproducible-research`, `python`, `aibom`. Topics must remain accurate; do not imply vendor sponsorship.
- **Social preview (optional):** a truthful static card should include `Research prototype` and `GPU execution not verified`; no unauthorized NVIDIA/Google branding.
- **Security:** check whether GitHub **private vulnerability reporting** is enabled before asking for confidential reports; `SECURITY.md` must not imply it is already enabled.
- **Discussions:** optional, only enable if someone can moderate it. Issues remain the primary reproducible work queue.

GitHub's official guidance: [community health](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions), [topics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics), [social preview](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview).

## A small outreach experiment

Make contributions possible **before** broad promotion. Send a small, personalized, technically specific invitation to relevant Python/K8s/AppSec maintainers and researchers. Ask for one reproducible critique, not a vague promise to join a team. Share one specific issue per post; provide the standard README as context.

For a 30-day review, record:
- Profile visits/unique repo views (if available), issue views and observed engagement **without identifying users**.
- External review comments that test one precise claim, reproducible issue reports and genuinely new contributor PRs.
- Reviewed/merged PRs, median first-review response time, drop-off at install/test, and whether promised review capacity was actually met.
- Evidence that upstream already solves the problem (a *positive* research outcome), and any unresolved security disclosures kept out of public posts.

Do not buy stars, manufacture issues, infer customers from stars/forks, or promise fast review. Set a **human review budget** you can sustain. An open-source contributor community can form around falsifiable research even when there is no product; it will not form automatically from public visibility alone.

## Decision rule

Continue community research if independent reviewers contribute reproducible corrections or real comparators. Pause additional outreach if nobody can review incoming work or if private evidence cannot be accepted safely. Only reopen product development after the [pre-registered G4 gates](../research/g4_independent_validation_protocol.md), security review and real demand are actually satisfied.
