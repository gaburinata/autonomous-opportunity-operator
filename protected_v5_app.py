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


app = create_app(
    synthesis_executor_factory=(
        build_protected_gemini_synthesis_executor
    )
)
