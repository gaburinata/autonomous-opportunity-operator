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
        "$id",
        "$defs",
        "$ref",
        "$anchor",
        "type",
        "format",
        "title",
        "description",
        "enum",
        "items",
        "prefixItems",
        "minItems",
        "maxItems",
        "minimum",
        "maximum",
        "anyOf",
        "oneOf",
        "properties",
        "additionalProperties",
        "required",
        "propertyOrdering",
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

        response = (
            models.generate_content(
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

        return _parse_payload(
            response
        )

    return executor


__all__ = [
    "build_protected_gemini_synthesis_executor",
]
