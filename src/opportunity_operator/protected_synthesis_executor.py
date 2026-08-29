"""Protected Gemini executor for evidence-backed opportunity synthesis.

Security / architecture boundary:
- no client or credential lookup occurs at module import;
- no model call occurs while constructing the application;
- Cloud Run ADC/service identity is used by google-genai at invocation time;
- executor accepts the frozen synthesis prompt + JSON schema contract;
- structured output is returned to the existing deterministic validator;
- this module does not decide whether any hypothesis is valid or profitable.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
import os
import re
import sys
from typing import Any, Callable


_ENV_TEXT = re.compile(
    r"[A-Za-z0-9._:/-]{1,256}\Z",
    re.ASCII,
)


def _required_env_text(
    env: Mapping[str, str],
    name: str,
) -> str:

    value = env.get(
        name
    )

    if (
        not isinstance(value, str)
        or not _ENV_TEXT.fullmatch(
            value.strip()
        )
    ):
        raise ValueError(
            f"missing or invalid {name}"
        )

    return value.strip()


# Google response_json_schema supports only a documented
# subset of JSON Schema. AOO intentionally keeps a stricter
# deterministic post-generation schema, including string-length
# constraints. Do not weaken that authoritative validator.
#
# Instead, project the strict AOO schema into the subset accepted
# by Vertex for generation guidance, then validate Gemini output
# against the original strict AOO schema afterwards.
_VERTEX_JSON_SCHEMA_KEYS = frozenset(
    {
        # Generation guidance only.
        #
        # The authoritative AOO schema is deliberately stricter and is
        # applied after generation. Vertex only needs enough structure
        # to produce the expected object shape.
        "type",
        "properties",
        "required",
        "items",
        "enum",
    }
)


def _vertex_response_schema(
    value: object,
) -> object:
    """Project strict AOO JSON Schema into Vertex's supported subset."""

    if isinstance(value, Mapping):

        projected: dict[str, object] = {}

        for key, child in value.items():

            if key not in _VERTEX_JSON_SCHEMA_KEYS:
                continue

            if key == "properties":

                if not isinstance(
                    child,
                    Mapping,
                ):
                    raise ValueError(
                        "invalid schema properties"
                    )

                projected[
                    key
                ] = {
                    str(name):
                        _vertex_response_schema(
                            schema
                        )
                    for name, schema
                    in child.items()
                }

                continue

            if key == "$defs":

                if not isinstance(
                    child,
                    Mapping,
                ):
                    raise ValueError(
                        "invalid schema defs"
                    )

                projected[
                    key
                ] = {
                    str(name):
                        _vertex_response_schema(
                            schema
                        )
                    for name, schema
                    in child.items()
                }

                continue

            projected[
                key
            ] = _vertex_response_schema(
                child
            )

        return projected

    if isinstance(value, list):
        return [
            _vertex_response_schema(
                child
            )
            for child in value
        ]

    return value


def _safe_executor_diagnostic(
    stage: str,
    exc: BaseException,
) -> str:
    """Return bounded non-secret error metadata for protected logs only."""

    exc_type = type(exc).__name__

    code = getattr(
        exc,
        "code",
        None,
    )

    status = getattr(
        exc,
        "status",
        None,
    )

    message = getattr(
        exc,
        "message",
        None,
    )

    if not isinstance(
        message,
        str,
    ):
        message = str(exc)

    # Never permit auth material into Cloud Run logs.
    redactions = (
        (
            re.compile(
                r"Bearer\s+[^\s\"']+",
                re.I,
            ),
            "Bearer <REDACTED>",
        ),
        (
            re.compile(
                r"(?:access[_-]?token|id[_-]?token|api[_-]?key)"
                r"\s*[=:]\s*[^\s,;\"']+",
                re.I,
            ),
            "<REDACTED_CREDENTIAL>",
        ),
        (
            re.compile(
                r"ya29\.[A-Za-z0-9._-]+",
                re.I,
            ),
            "<REDACTED_TOKEN>",
        ),
    )

    for pattern, replacement in redactions:
        message = pattern.sub(
            replacement,
            message,
        )

    message = " ".join(
        message.split()
    )

    if len(message) > 1200:
        message = (
            message[:1200]
            + "...<TRUNCATED>"
        )

    return (
        "AOO_SYNTHESIS_EXECUTOR_DIAGNOSTIC"
        + "|STAGE="
        + stage
        + "|TYPE="
        + exc_type
        + "|CODE="
        + repr(code)
        + "|STATUS="
        + repr(status)
        + "|MESSAGE="
        + message
    )


def _log_executor_failure(
    stage: str,
    exc: BaseException,
) -> None:

    print(
        _safe_executor_diagnostic(
            stage,
            exc,
        ),
        file=sys.stderr,
        flush=True,
    )


def _parse_payload(
    response: object,
) -> dict[str, object]:

    parsed = getattr(
        response,
        "parsed",
        None,
    )

    if isinstance(
        parsed,
        Mapping,
    ):
        return dict(parsed)

    text = getattr(
        response,
        "text",
        None,
    )

    if (
        not isinstance(text, str)
        or not text.strip()
    ):
        raise ValueError(
            "Gemini returned no structured payload"
        )

    payload = json.loads(
        text
    )

    if not isinstance(
        payload,
        Mapping,
    ):
        raise ValueError(
            "Gemini payload must be an object"
        )

    return dict(payload)


def build_protected_gemini_synthesis_executor(
    *,
    environ: Mapping[str, str] | None = None,
    client_factory: Callable[..., object] | None = None,
) -> Callable[
    [str, dict[str, Any]],
    dict[str, object],
]:
    """Construct one synchronous structured Gemini executor.

    The actual model call happens only when the returned callable is invoked.
    """

    env = dict(
        os.environ
        if environ is None
        else environ
    )

    project = _required_env_text(
        env,
        "GOOGLE_CLOUD_PROJECT",
    )

    location = _required_env_text(
        env,
        "GOOGLE_CLOUD_LOCATION",
    )

    model = _required_env_text(
        env,
        "AOO_MODEL_ID",
    )

    if client_factory is None:

        from google import genai

        client_factory = (
            genai.Client
        )

    client = client_factory(
        vertexai=True,
        project=project,
        location=location,
    )

    models = getattr(
        client,
        "models",
        None,
    )

    if (
        models is None
        or not callable(
            getattr(
                models,
                "generate_content",
                None,
            )
        )
    ):
        raise TypeError(
            "invalid Gemini client"
        )

    def executor(
        prompt: str,
        schema: dict[str, Any],
    ) -> dict[str, object]:

        if (
            not isinstance(prompt, str)
            or not prompt.strip()
        ):
            raise ValueError(
                "invalid synthesis prompt"
            )

        if not isinstance(
            schema,
            Mapping,
        ):
            raise ValueError(
                "invalid synthesis schema"
            )

        vertex_schema = (
            _vertex_response_schema(
                dict(schema)
            )
        )

        try:
            response = (
                client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "temperature":
                            0,

                        "response_mime_type":
                            "application/json",

                        "response_json_schema":
                            vertex_schema,
                    },
                )
            )

        except Exception as exc:
            _log_executor_failure(
                "GENERATE_CONTENT",
                exc,
            )
            raise

        try:
            return _parse_payload(
                response
            )

        except Exception as exc:
            _log_executor_failure(
                "PARSE_PAYLOAD",
                exc,
            )
            raise

    return executor


__all__ = [
    "build_protected_gemini_synthesis_executor",
]
