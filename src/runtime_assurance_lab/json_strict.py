"""Single strict JSON boundary for local, untrusted evidence documents.

The caller is responsible for bounding input bytes before invoking this parser.
Rejects duplicate keys, nonfinite constants, exponent overflow and invalid UTF-8.
"""
from __future__ import annotations

import json
import math
from typing import Any


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"nonfinite JSON value: {value}")


def _finite_float(value: str) -> float:
    try:
        parsed = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError("invalid JSON floating-point value") from exc
    if not math.isfinite(parsed):
        raise ValueError("nonfinite JSON floating-point value")
    return parsed


def loads_strict(raw: str | bytes) -> Any:
    if not isinstance(raw, (str, bytes)):
        raise ValueError("JSON data must be text or bytes")
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    return json.loads(text, object_pairs_hook=_unique_pairs,
                      parse_constant=_reject_constant, parse_float=_finite_float)
