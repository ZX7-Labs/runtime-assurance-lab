"""Guard reproducible open-research onboarding without asserting runtime assurance."""
from __future__ import annotations

from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = (
    "README.md",
    "CONTRIBUTING.md",
    "SUPPORT.md",
    "GOVERNANCE.md",
    "docs/ROADMAP.md",
    "docs/REPRODUCIBILITY.md",
    "docs/CLAIMS_AND_BASELINES.md",
    "docs/CONTRIBUTOR_PATHS.md",
    "docs/COMMUNITY_LAUNCH.md",
)

@pytest.mark.parametrize("path", PUBLIC_DOCS)
def test_public_documents_exist_and_link_to_real_local_files(path: str) -> None:
    current = ROOT / path
    assert current.is_file(), path
    text = current.read_text(encoding="utf-8")
    assert len(text.strip()) > 100
    # Local relative Markdown links; external URLs and section anchors are not files.
    for destination in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text):
        if destination.startswith(("https://", "http://", "mailto:", "#")):
            continue
        rel = destination.split("#", 1)[0]
        if not rel or " " in rel:  # URLs with spaces need an escaped Markdown link.
            continue
        target = (current.parent / rel).resolve()
        assert target.is_relative_to(ROOT.resolve()), f"{path}: link escapes repository: {destination}"
        assert target.exists(), f"{path}: missing local target: {destination}"

def test_newcomers_can_read_reproduction_and_expected_safe_failure() -> None:
    text = (ROOT / "docs/REPRODUCIBILITY.md").read_text(encoding="utf-8")
    for marker in (
        'python -m pip install -e ".[test]"',
        "python -m pytest -q",
        "py -3 -m venv .venv",
        "results/demo",
        "UNKNOWN",
        "PAUSE_PRODUCT_BUILD",
        "exit (2)",
        "GPU",
        "git rev-parse HEAD",
    ):
        assert marker in text
    assert "python -O" not in text

def test_technical_claims_do_not_promote_synthetic_metrics_to_runtime_proof() -> None:
    claims = (ROOT / "docs/CLAIMS_AND_BASELINES.md").read_text(encoding="utf-8")
    assert "600-case" in claims and "0 disagreements" in claims
    assert "not event-to-detection latency" in claims.lower()
    assert "PAUSE_PRODUCT_BUILD" in claims
    for p in ("NVIDIA AICR", "Google k8s-aibom", "Sigstore", "Kyverno"):
        assert p in claims
    landing = (ROOT / "README.md").read_text(encoding="utf-8")
    for pointer in ("REPRODUCIBILITY.md", "CLAIMS_AND_BASELINES.md", "CONTRIBUTOR_PATHS.md"):
        assert pointer in landing
    assert "not production assurance" in landing.lower()

def test_reproduction_issue_form_preserves_private_data_boundary() -> None:
    form = (ROOT / ".github/ISSUE_TEMPLATE/reproduction_report.yml").read_text(encoding="utf-8")
    assert form.startswith("name: ")
    assert "\ndescription: " in form
    assert "\nbody:" in form
    for entry in ("revision", "environment", "procedure", "expected", "limitations"):
        assert f"id: {entry}" in form
    assert form.count("required: true") == 5
    assert "Do not paste secrets" in form
    assert "no cluster required" in form.lower()
    config = (ROOT / ".github/ISSUE_TEMPLATE/config.yml").read_text(encoding="utf-8")
    assert "REPRODUCIBILITY.md" in config
    assert "Security reporting" in config

def test_research_invitation_has_no_product_or_community_claim() -> None:
    text = (ROOT / "docs/COMMUNITY_LAUNCH.md").read_text(encoding="utf-8")
    assert "NOT production security software" in text
    assert "not assume they were changed" in text
    assert "Do not buy stars" in text
    assert "No proof of real model execution" in text or "not a claim of product availability" in text
    guide = (ROOT / "docs/CONTRIBUTOR_PATHS.md").read_text(encoding="utf-8")
    for issue in range(1, 5):
        assert f"/issues/{issue}" in guide
    assert "A GPU is **not** required" in guide
