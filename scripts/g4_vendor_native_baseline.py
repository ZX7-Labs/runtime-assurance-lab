"""Execute *upstream* public release binaries on a CPU-only runner.

Research experiment only: release provenance and recipe catalog verification do NOT
establish live Kubernetes/GPU provenance, cross-plane linkage or product value.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.request import Request, urlopen

RELEASES = {
    "aicr": {
        "url": "https://github.com/NVIDIA/aicr/releases/download/v1.2.0/aicr_1.2.0_linux_amd64.tar.gz",
        "sha256": "3ff6935fd7988373903a2a30f1c24a74a5f8a9052a310615db19fcfec4cfe9a2",
        "max_size": 32_000_000,
        "binary": "aicr",
    },
    "aicr_catalog_sigstore": {
        "url": "https://github.com/NVIDIA/aicr/releases/download/v1.2.0/recipe-catalog.sigstore.json",
        "sha256": "80744565b8d79da72afc0720dc551e9664eb91e1d94da90c1fad1ba65d8802cc",
        "max_size": 25_000,
    },
    "aibom": {
        "url": "https://github.com/GoogleCloudPlatform/k8s-aibom/releases/download/v1.6.2/kubectl-aibom_v1.6.2_linux_amd64.tar.gz",
        "sha256": "5a7f7e98e55d59ce3f7e5fa9ce385b544775ddefd32bcdf20b6e9fc234b2a7c0",
        "max_size": 12_000_000,
        "binary": "kubectl-aibom",
    },
    "aibom_provenance": {
        "url": "https://github.com/GoogleCloudPlatform/k8s-aibom/releases/download/v1.6.2/kubectl-aibom_v1.6.2.provenance.intoto.jsonl",
        "sha256": "a90db7b45bd48ae6663d48494287b11a6b6bd0339a338de3a2eca891209a62f8",
        "max_size": 25_000,
    },
}


class BaselineError(ValueError):
    """Failure is not a production verifier verdict."""


def checked_bytes(data: bytes, sha256: str, max_size: int) -> bytes:
    if not data or len(data) > max_size:
        raise BaselineError("download is empty or exceeds pinned size cap")
    if hashlib.sha256(data).hexdigest() != sha256:
        raise BaselineError("download does not match pinned release SHA-256")
    return data


def download(name: str) -> bytes:
    item = RELEASES[name]
    request = Request(item["url"], headers={"User-Agent": "runtime-assurance-research/1.0"})
    with urlopen(request, timeout=45) as response:
        if response.url.split(":", 1)[0] != "https":
            raise BaselineError("release redirected off HTTPS")
        data = response.read(item["max_size"] + 1)
    return checked_bytes(data, item["sha256"], item["max_size"])


def extract_one_binary(tgz: bytes, binary_name: str, dest: Path) -> Path:
    matches: list[bytes] = []
    with tarfile.open(fileobj=io.BytesIO(tgz), mode="r:gz") as bundle:
        for member in bundle.getmembers():
            name = PurePosixPath(member.name)
            if name.name != binary_name:
                continue
            if not member.isfile() or member.issym() or member.islnk():
                raise BaselineError("release binary is not a regular file")
            if name.is_absolute() or ".." in name.parts or member.size < 1 or member.size > 120_000_000:
                raise BaselineError("release binary path or size invalid")
            with bundle.extractfile(member) as handle:
                raw = handle.read(120_000_001)
            if len(raw) != member.size:
                raise BaselineError("release binary truncated")
            matches.append(raw)
    if len(matches) != 1:
        raise BaselineError("release archive must contain exactly one expected binary")
    dest.write_bytes(matches[0])
    dest.chmod(0o700)
    return dest


def run_required(argv: list[str], *, timeout: int = 90) -> dict:
    environment = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "TMPDIR", "SSL_CERT_FILE") if k in os.environ}
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=environment)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BaselineError(f"native test unavailable: {type(exc).__name__}") from exc
    if completed.returncode != 0:
        raise BaselineError(f"native command failed (exit {completed.returncode}): {Path(argv[0]).name}: {(completed.stderr or completed.stdout)[-400:]}")
    return {"passed": True, "exit_code": 0, "tool": Path(argv[0]).name}


def execute() -> dict:
    if sys.platform != "linux" or os.uname().machine != "x86_64":
        raise BaselineError("pinned binaries require Linux x86_64")
    with tempfile.TemporaryDirectory(prefix="g4-upstream-native-") as tmp:
        work = Path(tmp)
        aicr_tar, google_tar = download("aicr"), download("aibom")
        provenance = download("aibom_provenance")
        catalog_signature = download("aicr_catalog_sigstore")
        aicr = extract_one_binary(aicr_tar, "aicr", work / "aicr")
        aibom = extract_one_binary(google_tar, "kubectl-aibom", work / "kubectl-aibom")
        archive = work / "kubectl-aibom_v1.6.2_linux_amd64.tar.gz"
        archive.write_bytes(google_tar)
        bundle = work / "kubectl-aibom_v1.6.2.provenance.intoto.jsonl"
        bundle.write_bytes(provenance)
        # This uses the GitHub CLI's independent GitHub attestation verifier
        # rather than trusting a checksum embedded inside the downloaded archive.
        gh = shutil.which("gh")
        if gh is None:
            raise BaselineError("independent gh attestation verifier unavailable")
        provenance_result = run_required([gh, "attestation", "verify", str(archive), "--owner", "GoogleCloudPlatform", "--bundle", str(bundle)])
        catalog_bundle = work / "recipe-catalog.sigstore.json"
        catalog_bundle.write_bytes(catalog_signature)
        catalog_result = run_required([str(aicr), "recipe", "verify-catalog", str(catalog_bundle)])
        google_result = run_required([str(aibom), "--help"])
        return {
            "schema": "g4-vendor-native-public-baseline-v1",
            "source_type": "PUBLIC_SIGNED_VENDOR_RELEASES_NO_RUNTIME_EVIDENCE",
            "verified_release_shas": {key: RELEASES[key]["sha256"] for key in ("aicr", "aicr_catalog_sigstore", "aibom", "aibom_provenance")},
            "google_release_attestation": provenance_result,
            "nvidia_embedded_catalog_verification": catalog_result,
            "google_cli_invocation": google_result,
            "actual_kubernetes_cluster_connected": False,
            "gpu_execution_verified": False,
            "same_workload_upstream_evidence": False,
            "cross_plane_link_verified": False,
            "independent_real_customer_comparison": False,
            "g4_completed": False,
            "g5_completed": False,
            "decision": "PAUSE_PRODUCT_BUILD",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new local JSON file; refuses overwrite")
    args = parser.parse_args()
    try:
        result = execute()
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, sort_keys=True, indent=2)
            handle.write("\n")
        print(json.dumps(result, sort_keys=True))
        return 0  # Only the public-vendor CPU baseline passed; NEVER a G4 GO.
    except (BaselineError, OSError, tarfile.TarError) as exc:
        print(json.dumps({"decision": "PAUSE_PRODUCT_BUILD", "g4_completed": False,
                          "public_vendor_baseline": "INCOMPLETE", "error": str(exc)[-500:]}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
