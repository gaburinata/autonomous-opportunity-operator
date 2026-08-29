"""Protected V5 synthesis-enabled Cloud Run entrypoint.

This is intentionally separate from:
- main:app
- judge_app:app

Importing this module constructs no model call. The model is invoked only by
an authenticated POST to the synthesis endpoint.
"""

from main import create_app
from opportunity_operator.protected_synthesis_executor import (
    build_protected_gemini_synthesis_executor,
)
from opportunity_operator.protected_synthesis_preflight import (
    run_protected_synthesis_executor_preflight,
)


app = create_app(
    synthesis_executor_factory=(
        build_protected_gemini_synthesis_executor
    )
)

@app.get("/internal/synthesis-executor-preflight")
async def synthesis_executor_preflight():
    """Private preview diagnostic. Constructs executor; never invokes model."""

    return (
        run_protected_synthesis_executor_preflight()
    )
