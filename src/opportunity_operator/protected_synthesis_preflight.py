"""Protected synthesis executor construction diagnostic.

This module never invokes the returned executor and therefore never calls
Gemini / generate_content.

It exists only to distinguish:
- environment validation failure,
- SDK import/client construction failure,
- invalid client surface,
from an actual model-generation failure.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .protected_synthesis_executor import (
    _safe_executor_diagnostic,
    build_protected_gemini_synthesis_executor,
)


def run_protected_synthesis_executor_preflight(
    *,
    builder: Callable[..., object] | None = None,
) -> dict[str, Any]:
    """Construct the protected executor without invoking it."""

    selected_builder = (
        build_protected_gemini_synthesis_executor
        if builder is None
        else builder
    )

    try:
        executor = selected_builder()

    except Exception as exc:
        return {
            "status":
                "FAIL_CLOSED",

            "stage":
                "EXECUTOR_FACTORY",

            "diagnostic":
                _safe_executor_diagnostic(
                    "EXECUTOR_FACTORY",
                    exc,
                ),

            "executor_constructed":
                False,

            "model_call":
                False,
        }

    if not callable(executor):
        return {
            "status":
                "FAIL_CLOSED",

            "stage":
                "EXECUTOR_FACTORY",

            "diagnostic":
                (
                    "AOO_SYNTHESIS_EXECUTOR_DIAGNOSTIC"
                    "|STAGE=EXECUTOR_FACTORY"
                    "|TYPE=TypeError"
                    "|CODE=None"
                    "|STATUS=None"
                    "|MESSAGE=executor is not callable"
                ),

            "executor_constructed":
                False,

            "model_call":
                False,
        }

    return {
        "status":
            "PASS",

        "stage":
            "EXECUTOR_FACTORY",

        "diagnostic":
            None,

        "executor_constructed":
            True,

        "model_call":
            False,
    }


__all__ = [
    "run_protected_synthesis_executor_preflight",
]
