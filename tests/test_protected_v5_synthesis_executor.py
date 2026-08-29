from __future__ import annotations

import json
import unittest

from fastapi.testclient import (
    TestClient,
)

import judge_app
import main

from opportunity_operator.protected_synthesis_executor import (
    build_protected_gemini_synthesis_executor,
)


ENV = {
    "GOOGLE_CLOUD_PROJECT":
        "unit-test-project",

    "GOOGLE_CLOUD_LOCATION":
        "us-central1",

    "AOO_MODEL_ID":
        "gemini-3.5-flash",
}


def v5_profile():
    return {
        "profile_version":
            "5",

        "goal":
            "both",

        "residence_country":
            "Bulgaria",

        "citizenships":
            ["Bulgaria"],

        "currency":
            "EUR",

        "available_money":
            "150",

        "max_cash_spend_or_risk":
            "25",

        "human_hours_per_week":
            "5",

        "exclusions":
            [],

        "skills_assets":
            [],
    }


def evidence():
    return [
        {
            "source_id":
                "source-api",

            "source_url":
                "https://example.org/api",

            "title":
                "Official API evidence",

            "excerpt":
                (
                    "A machine-readable API is "
                    "available for repeated use."
                ),
        },
    ]


def synthesis_response():
    return {
        "observations": [
            {
                "title":
                    "Build an automated monitoring product",

                "observed_condition":
                    (
                        "The source exposes repeated "
                        "machine-readable information."
                    ),

                "economic_mechanism":
                    (
                        "Create a narrow recurring "
                        "monitoring product."
                    ),

                "value_source":
                    (
                        "Users who need repeated "
                        "monitoring."
                    ),

                "why_ai_changes_feasibility":
                    (
                        "AI can automate ingestion, "
                        "classification and alerts."
                    ),

                "assumptions":
                    [],

                "cheap_test":
                    (
                        "Build a read-only prototype "
                        "and test repeated usage."
                    ),

                "evidence_required":
                    [
                        "Observed demand"
                    ],

                "source_ids":
                    [
                        "source-api"
                    ],

                "mechanism_hint":
                    "monitoring_product",
            }
        ]
    }


class _Response:

    def __init__(
        self,
        *,
        parsed=None,
        text=None,
    ):
        self.parsed = parsed
        self.text = text


class _Models:

    def __init__(
        self,
        response,
        calls,
    ):
        self._response = response
        self._calls = calls

    def generate_content(
        self,
        **kwargs,
    ):
        self._calls.append(
            kwargs
        )

        return self._response


class _Client:

    def __init__(
        self,
        response,
        calls,
    ):
        self.models = _Models(
            response,
            calls,
        )


class ProtectedGeminiExecutorTests(
    unittest.TestCase
):

    def test_factory_constructs_no_model_call(self):

        model_calls = []
        client_calls = []

        def factory(
            **kwargs,
        ):
            client_calls.append(
                kwargs
            )

            return _Client(
                _Response(
                    parsed=
                        synthesis_response()
                ),
                model_calls,
            )

        executor = (
            build_protected_gemini_synthesis_executor(
                environ=ENV,
                client_factory=factory,
            )
        )

        self.assertTrue(
            callable(executor)
        )

        self.assertEqual(
            model_calls,
            [],
        )

        self.assertEqual(
            client_calls,
            [
                {
                    "vertexai": True,
                    "project":
                        "unit-test-project",
                    "location":
                        "us-central1",
                }
            ],
        )

    def test_executor_uses_structured_json_schema(self):

        model_calls = []

        def factory(
            **kwargs,
        ):
            return _Client(
                _Response(
                    parsed=
                        synthesis_response()
                ),
                model_calls,
            )

        executor = (
            build_protected_gemini_synthesis_executor(
                environ=ENV,
                client_factory=factory,
            )
        )

        schema = {
            "type":
                "object",

            "additionalProperties":
                False,

            "properties": {
                "observations": {
                    "type":
                        "array",

                    "minItems":
                        1,

                    "maxItems":
                        32,

                    "items": {
                        "type":
                            "object",

                        "properties": {
                            "title": {
                                "type":
                                    "string",

                                # Strict AOO validation keeps these,
                                # but Vertex generation schema must not.
                                "minLength":
                                    1,

                                "maxLength":
                                    1000,
                            }
                        },

                        "required": [
                            "title"
                        ],
                    },
                }
            },

            "required": [
                "observations"
            ],
        }

        result = executor(
            "test prompt",
            schema,
        )

        self.assertEqual(
            result,
            synthesis_response(),
        )

        self.assertEqual(
            len(model_calls),
            1,
        )

        call = model_calls[0]

        self.assertEqual(
            call["model"],
            "gemini-3.5-flash",
        )

        self.assertEqual(
            call["contents"],
            "test prompt",
        )

        self.assertEqual(
            call["config"][
                "response_mime_type"
            ],
            "application/json",
        )

        vertex_schema = (
            call["config"][
                "response_json_schema"
            ]
        )

        self.assertEqual(
            vertex_schema[
                "type"
            ],
            "object",
        )

        self.assertFalse(
            vertex_schema[
                "additionalProperties"
            ]
        )

        observations = (
            vertex_schema[
                "properties"
            ][
                "observations"
            ]
        )

        self.assertEqual(
            observations[
                "minItems"
            ],
            1,
        )

        self.assertEqual(
            observations[
                "maxItems"
            ],
            32,
        )

        title_schema = (
            observations[
                "items"
            ][
                "properties"
            ][
                "title"
            ]
        )

        self.assertEqual(
            title_schema,
            {
                "type":
                    "string"
            },
        )

        # The caller's strict schema must not be mutated.
        self.assertEqual(
            schema[
                "properties"
            ][
                "observations"
            ][
                "items"
            ][
                "properties"
            ][
                "title"
            ][
                "minLength"
            ],
            1,
        )

        self.assertEqual(
            schema[
                "properties"
            ][
                "observations"
            ][
                "items"
            ][
                "properties"
            ][
                "title"
            ][
                "maxLength"
            ],
            1000,
        )

    def test_json_text_fallback_is_supported(self):

        calls = []

        def factory(
            **kwargs,
        ):
            return _Client(
                _Response(
                    parsed=None,
                    text=json.dumps(
                        synthesis_response()
                    ),
                ),
                calls,
            )

        executor = (
            build_protected_gemini_synthesis_executor(
                environ=ENV,
                client_factory=factory,
            )
        )

        result = executor(
            "prompt",
            {
                "type":
                    "object"
            },
        )

        self.assertEqual(
            result,
            synthesis_response(),
        )

    def test_missing_cloud_identity_fails_before_client(self):

        client_calls = []

        def factory(
            **kwargs,
        ):
            client_calls.append(
                kwargs
            )

            raise AssertionError(
                "client must not be constructed"
            )

        with self.assertRaises(
            ValueError
        ):
            build_protected_gemini_synthesis_executor(
                environ={
                    "AOO_MODEL_ID":
                        "gemini-3.5-flash",
                },
                client_factory=factory,
            )

        self.assertEqual(
            client_calls,
            [],
        )


class ProtectedV5EndpointTests(
    unittest.TestCase
):

    def test_default_main_has_no_synthesis_executor(self):

        client = TestClient(
            main.create_app()
        )

        response = client.post(
            "/opportunities/synthesize-v5",
            json={
                "profile":
                    v5_profile(),

                "evidence_items":
                    evidence(),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertEqual(
            data["status"],
            "DECISION_REQUIRED",
        )

        self.assertIn(
            "SYNTHESIS_EXECUTOR_NOT_CONFIGURED",
            data["reason_codes"],
        )

    def test_injected_executor_enters_build_operate(self):

        calls = []

        def executor_factory():

            def executor(
                prompt,
                schema,
            ):
                calls.append(
                    (
                        prompt,
                        schema,
                    )
                )

                return (
                    synthesis_response()
                )

            return executor

        client = TestClient(
            main.create_app(
                synthesis_executor_factory=
                    executor_factory
            )
        )

        response = client.post(
            "/opportunities/synthesize-v5",
            json={
                "profile":
                    v5_profile(),

                "evidence_items":
                    evidence(),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertEqual(
            data["status"],
            "PASS",
        )

        self.assertEqual(
            len(calls),
            1,
        )

        self.assertEqual(
            len(
                data[
                    "candidates"
                ]
            ),
            1,
        )

        build_operate = (
            data[
                "product_view"
            ][
                "build_operate"
            ]
        )

        self.assertEqual(
            len(build_operate),
            1,
        )

        self.assertIn(
            "monitoring",
            build_operate[0][
                "title"
            ].lower(),
        )


class PublicBoundaryTests(
    unittest.TestCase
):

    def test_public_judge_locks_v5_synthesis(self):

        client = TestClient(
            judge_app.app
        )

        response = client.post(
            "/opportunities/synthesize-v5",
            json={
                "profile":
                    v5_profile(),

                "evidence_items":
                    evidence(),
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertEqual(
            response.json().get(
                "status"
            ),
            "JUDGE_DEMO_LOCKED",
        )


class ProtectedClientLifetimeTests(
    unittest.TestCase
):

    def test_returned_executor_retains_client_lifetime(self):

        import gc
        import weakref

        client_refs = []
        model_calls = []

        def factory(
            **kwargs,
        ):
            client = _Client(
                _Response(
                    parsed=
                        synthesis_response()
                ),
                model_calls,
            )

            client_refs.append(
                weakref.ref(
                    client
                )
            )

            return client

        executor = (
            build_protected_gemini_synthesis_executor(
                environ=ENV,
                client_factory=factory,
            )
        )

        self.assertEqual(
            len(client_refs),
            1,
        )

        gc.collect()

        self.assertIsNotNone(
            client_refs[0](),
            "returned executor must retain the Google GenAI Client",
        )

        result = executor(
            "test prompt",
            {
                "type":
                    "object"
            },
        )

        self.assertEqual(
            result,
            synthesis_response(),
        )

        self.assertEqual(
            len(model_calls),
            1,
        )



if __name__ == "__main__":
    unittest.main()


class ProtectedExecutorDiagnosticTests(
    unittest.TestCase
):

    def test_diagnostic_exposes_type_not_credentials(self):

        from opportunity_operator.protected_synthesis_executor import (
            _safe_executor_diagnostic,
        )

        exc = RuntimeError(
            "400 invalid schema "
            "Bearer SUPERSECRET "
            "access_token=SECRET2 "
            "api_key=SECRET3"
        )

        output = _safe_executor_diagnostic(
            "GENERATE_CONTENT",
            exc,
        )

        self.assertIn(
            "TYPE=RuntimeError",
            output,
        )

        self.assertIn(
            "STAGE=GENERATE_CONTENT",
            output,
        )

        self.assertIn(
            "400 invalid schema",
            output,
        )

        for secret in (
            "SUPERSECRET",
            "SECRET2",
            "SECRET3",
        ):
            self.assertNotIn(
                secret,
                output,
            )

    def test_generate_exception_is_logged_then_reraised(self):

        import contextlib
        import io

        class FailingModels:

            def generate_content(
                self,
                **kwargs,
            ):
                raise RuntimeError(
                    "synthetic provider failure"
                )

        class FailingClient:

            models = FailingModels()

        def client_factory(
            **kwargs,
        ):
            return FailingClient()

        executor = (
            build_protected_gemini_synthesis_executor(
                environ=ENV,
                client_factory=
                    client_factory,
            )
        )

        stderr = io.StringIO()

        with (
            contextlib.redirect_stderr(
                stderr
            ),
            self.assertRaises(
                RuntimeError
            ),
        ):
            executor(
                "prompt",
                {
                    "type":
                        "object"
                },
            )

        logged = stderr.getvalue()

        self.assertIn(
            "AOO_SYNTHESIS_EXECUTOR_DIAGNOSTIC",
            logged,
        )

        self.assertIn(
            "STAGE=GENERATE_CONTENT",
            logged,
        )

        self.assertIn(
            "synthetic provider failure",
            logged,
        )
