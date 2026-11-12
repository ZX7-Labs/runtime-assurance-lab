"""Guard the public open-source contract, not the outcome of the research."""
from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_project_is_explicitly_apache_licensed_with_real_license_text():
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = meta["project"]
    assert project["license"] == "Apache-2.0"
    assert project["license-files"] == ["LICENSE", "NOTICE"]
    assert project["readme"] == "README.md"
    assert project["urls"]["Repository"] == "https://github.com/ZX7-Labs/runtime-assurance-lab"
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in license_text
    assert "Version 2.0, January 2004" in license_text
    assert "TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION" in license_text
    assert "END OF TERMS AND CONDITIONS" in license_text
    assert "ZX7 Labs contributors" in (ROOT / "NOTICE").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", [
    "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "GOVERNANCE.md",
    "docs/ARCHITECTURE.md", "docs/ROADMAP.md", "PLAN.md", "EVIDENCE.md",
    "SECURITY_REVIEW.md", "UPSTREAM_AUDIT.md", ".github/PULL_REQUEST_TEMPLATE.md",
])
def test_community_support_document_is_present(name):
    assert (ROOT / name).is_file()
    assert len((ROOT / name).read_text(encoding="utf-8").strip()) >= 100


def test_public_front_page_preserves_security_and_investment_limits():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "PAUSE_PRODUCT_BUILD" in readme
    assert "not production assurance" in readme.lower()
    assert "NVIDIA" in readme and "Google" in readme
    assert "LICENSE" in readme and "CONTRIBUTING.md" in readme
    assert "unlicensed research" not in readme.lower()


@pytest.mark.parametrize("name", ["bug_report.yml", "research_proposal.yml"])
def test_issue_forms_have_required_github_fields(name):
    text = (ROOT / ".github" / "ISSUE_TEMPLATE" / name).read_text(encoding="utf-8")
    assert text.startswith("name: ")
    assert "\ndescription: " in text
    assert "\nbody:\n" in text
    assert "\nabout:" not in text  # legacy MD issue-template key, not YAML forms
    assert "required: true" in text
    assert "SECURITY.md" in text or "PAUSE_PRODUCT_BUILD" in text


def test_generated_demo_outputs_are_ignored():
    # Contributors are free to regenerate demo files in the checkout.
    assert "results/demo/" in (ROOT / ".gitignore").read_text(encoding="utf-8")


def test_independent_review_challenge_is_discoverable():
    guide = ROOT / "research" / "INDEPENDENT_REVIEW_CHALLENGE.md"
    assert guide.is_file()
    for name in ("README.md", "CONTRIBUTING.md", "docs/ROADMAP.md"):
        assert "INDEPENDENT_REVIEW_CHALLENGE.md" in (ROOT / name).read_text(encoding="utf-8")
    text = guide.read_text(encoding="utf-8")
    for issue in range(1, 5):
        assert f"runtime-assurance-lab/issues/{issue}" in text


def test_independent_challenge_preserves_no_go_and_private_data_boundary():
    text = (ROOT / "research" / "INDEPENDENT_REVIEW_CHALLENGE.md").read_text(encoding="utf-8")
    assert "PAUSE_PRODUCT_BUILD" in text
    assert "same" in text.lower() and "upstream" in text.lower()
    assert "not" in text.lower() and "GPU" in text
    assert "SECURITY.md" in text
    assert "Do not upload" in text
