"""A demo verification failure must remain fatal even with Python -O.

These tests intentionally execute a child interpreter with assertions disabled.
They use synthetic fixtures and patch only the demo's local verification result;
they do not claim any live workload security properties.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]

_CHILD = """
import sys
from pathlib import Path
import runtime_assurance_lab.cli as cli

mode, marker, output = sys.argv[1:]
if mode == 'chain':
    cli.verify = lambda *a, **kw: (False, marker)
elif mode == 'semantics':
    cli.verify = lambda *a, **kw: (True, 'SYNTHETIC_CHAIN_CHECK')
    cli.verify_decision_semantics = lambda *a, **kw: (False, marker)
else:
    sys.exit(9)

try:
    cli.demo(Path('fixtures'), Path(output))
except ValueError as exc:
    if marker not in str(exc):
        print('unexpected error:', exc)
        sys.exit(7)
    sys.exit(0)

print('FAIL: demo accepted a rejected verification')
sys.exit(8)
"""


@pytest.mark.parametrize(("mode", "marker"), [
    ("chain", "FORCED_CHAIN_FAILURE"),
    ("semantics", "FORCED_SEMANTICS_FAILURE"),
])
def test_demo_fails_closed_when_python_assertions_are_disabled(
    tmp_path: Path, mode: str, marker: str
) -> None:
    target = tmp_path / mode
    result = subprocess.run(
        [sys.executable, "-O", "-c", _CHILD, mode, marker, str(target)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, (
        f"mode={mode}; exit={result.returncode}; "
        f"stdout={result.stdout}; stderr={result.stderr}"
    )
    # Failure must occur before journal/trust/checkpoint artifacts are written.
    assert not (target / "journal.json").exists()
    assert not (target / "trust-public.json").exists()
    assert not (target / "checkpoint.json").exists()
