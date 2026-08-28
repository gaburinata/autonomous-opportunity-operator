from __future__ import annotations

import copy
from decimal import Decimal
import importlib.util
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from opportunity_operator.opportunity_synthesis import (
    SynthesisObservation,
    build_synthesized_candidate,
)
from opportunity_operator.synthesis_runtime import (
    build_synthesis_prompt,
    canonicalize_evidence_items,
    execute_evidence_backed_synthesis,
    validate_synthesis_response,
)


ROOT = Path(__file__).resolve().parents[1]


def profile():
    return {
        "goal": "both",
        "country": "Bulgaria",
        "available_capital": "150",
        "max_cash_spend": "0",
        "human_hours_per_week": "8",
        "ai_autonomy": "maximum",
        "willingness": {
            "build_business": True,
            "work_with_customers": False,
            "sell": False,
            "publish_content": False,
            "invest_capital": False,
            "contests_juries": True,
            "financial_protocols": True,
        },
        "skills_assets": [
            "Python",
            "automation",
        ],
        "constraints": [
            "No leverage",
            "No borrowing",
        ],
    }


def evidence():
    return [
        {
            "source_id": "source-api",
            "source_url": "https://example.org/api",
            "title": "Official API documentation",
            "excerpt": (
                "The documented API exposes machine-readable records "
                "under a stable usage interface."
            ),
        },
        {
            "source_id": "source-pricing",
            "source_url": "https://example.org/pricing",
            "title": "Official pricing documentation",
            "excerpt": (
                "The documented service charges users for repeated "
                "machine-readable access."
            ),
        },
    ]


def response():
    return {
        "observations": [
            {
                "title": "Automated structured-data service",
                "observed_condition": (
                    "Official documentation shows a stable "
                    "machine-readable data interface."
                ),
                "economic_mechanism": (
                    "A derived automated service could exchange "
                    "useful processed output for usage payment."
                ),
                "value_source": (
                    "Users paying for repeated machine-readable access."
                ),
                "why_ai_changes_feasibility": (
                    "AI can automate transformation, monitoring and "
                    "quality checks that would otherwise require "
                    "recurring manual work."
                ),
                "assumptions": [
                    "Demand exists for the derived output.",
                ],
                "cheap_test": (
                    "Build a bounded read-only prototype and measure "
                    "whether the output is materially more useful."
                ),
                "evidence_required": [
                    "Observed demand or usage evidence",
                    "Measured delivery cost",
                ],
                "source_ids": [
                    "source-api",
                    "source-pricing",
                ],
                "mechanism_hint": "machine_api",
            }
        ]
    }


def load_main():
    spec = importlib.util.spec_from_file_location(
        "aoo_v3_phase3_main",
        ROOT / "main.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EvidenceTests(unittest.TestCase):

    def test_evidence_canonicalization_is_deterministic_and_nonmutating(self):
        raw = evidence()
        before = copy.deepcopy(raw)

        first = canonicalize_evidence_items(raw)
        second = canonicalize_evidence_items(raw)

        self.assertEqual(first, second)
        self.assertEqual(raw, before)

    def test_evidence_requires_https_unique_sources(self):
        bad_url = evidence()
        bad_url[0]["source_url"] = "http://example.org"

        with self.assertRaises((TypeError, ValueError)):
            canonicalize_evidence_items(bad_url)

        duplicate = evidence()
        duplicate[1]["source_id"] = "source-api"

        with self.assertRaises((TypeError, ValueError)):
            canonicalize_evidence_items(duplicate)

    def test_empty_evidence_is_rejected(self):
        with self.assertRaises((TypeError, ValueError)):
            canonicalize_evidence_items([])


class PromptTests(unittest.TestCase):

    def test_prompt_is_repeatable_and_evidence_disciplined(self):
        first = build_synthesis_prompt(
            profile(),
            evidence(),
        )
        second = build_synthesis_prompt(
            profile(),
            evidence(),
        )

        self.assertEqual(first, second)

        for token in (
            "observed condition",
            "economic mechanism",
            "value source",
            "why AI changes feasibility",
            "cheap",
            "evidence required",
            "source-api",
            "source-pricing",
            "unknown",
        ):
            self.assertIn(
                token.lower(),
                first.lower(),
            )

    def test_prompt_contains_person_profile(self):
        prompt = build_synthesis_prompt(
            profile(),
            evidence(),
        )

        self.assertIn("Bulgaria", prompt)
        self.assertIn("maximum", prompt)
        self.assertIn("No leverage", prompt)


class ResponseValidationTests(unittest.TestCase):

    def test_valid_response_is_accepted_with_stable_ids(self):
        first = validate_synthesis_response(
            response(),
            evidence(),
        )
        second = validate_synthesis_response(
            response(),
            evidence(),
        )

        self.assertEqual(first, second)
        self.assertEqual(len(first), 1)

        item = first[0]

        self.assertTrue(
            item["observation_id"].startswith("obs-")
        )
        self.assertTrue(
            item["candidate_id"].startswith("synth-")
        )

    def test_unknown_provenance_fails_closed(self):
        value = response()
        value["observations"][0]["source_ids"] = [
            "invented-source"
        ]

        with self.assertRaises((TypeError, ValueError)):
            validate_synthesis_response(
                value,
                evidence(),
            )

    def test_extra_model_field_fails_closed(self):
        value = response()
        value["observations"][0]["guaranteed_revenue"] = "1000000"

        with self.assertRaises((TypeError, ValueError)):
            validate_synthesis_response(
                value,
                evidence(),
            )


class CandidateTests(unittest.TestCase):

    def test_synthesized_unknown_capital_remains_none(self):
        observation = SynthesisObservation(
            observation_id="obs-x",
            observed_condition="Observed condition",
            economic_mechanism="Usage payment",
            value_source="Documented payer",
            why_ai_changes_feasibility="Automation reduces labor",
            assumptions=(),
            cheap_test="Bounded prototype",
            evidence_required=("Demand evidence",),
            source_ids=("source-x",),
            mechanism_hint="machine_api",
        )

        candidate = build_synthesized_candidate(
            observation,
            candidate_id="synth-x",
            title="Synthesized hypothesis",
        )

        self.assertIsNone(
            candidate.capital_required
        )

        self.assertIsNone(
            candidate.estimated_upside
        )

        self.assertIsNone(
            candidate.max_loss
        )


class ExecutorTests(unittest.TestCase):

    def test_executor_called_once_and_candidates_are_validated(self):
        calls = []

        def fake_executor(prompt, schema):
            calls.append((prompt, schema))
            return response()

        result = execute_evidence_backed_synthesis(
            profile(),
            evidence(),
            fake_executor,
        )

        self.assertEqual(
            result["status"],
            "PASS",
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            len(result["candidates"]),
            1,
        )
        self.assertEqual(
            result["candidates"][0].origin.value,
            "synthesized",
        )

    def test_executor_exception_fails_closed(self):
        def broken(prompt, schema):
            raise RuntimeError("model exploded")

        result = execute_evidence_backed_synthesis(
            profile(),
            evidence(),
            broken,
        )

        self.assertEqual(
            result["status"],
            "FAIL_CLOSED",
        )
        self.assertEqual(
            result["candidates"],
            [],
        )
        self.assertIn(
            "SYNTHESIS_EXECUTOR_FAILED",
            result["reason_codes"],
        )

    def test_malformed_model_output_fails_closed(self):
        def fake_executor(prompt, schema):
            return {
                "observations": [
                    {
                        "title": "unsupported",
                        "source_ids": ["invented"],
                    }
                ]
            }

        result = execute_evidence_backed_synthesis(
            profile(),
            evidence(),
            fake_executor,
        )

        self.assertEqual(
            result["status"],
            "FAIL_CLOSED",
        )
        self.assertEqual(
            result["candidates"],
            [],
        )


class EndpointTests(unittest.TestCase):

    def test_no_executor_returns_decision_required_without_model_construction(self):
        main = load_main()

        client = TestClient(
            main.create_app()
        )

        response_http = client.post(
            "/opportunities/synthesize",
            json={
                "profile": profile(),
                "evidence_items": evidence(),
            },
        )

        self.assertEqual(
            response_http.status_code,
            200,
        )

        data = response_http.json()

        self.assertEqual(
            data["status"],
            "DECISION_REQUIRED",
        )

        self.assertIn(
            "SYNTHESIS_EXECUTOR_NOT_CONFIGURED",
            data["reason_codes"],
        )

    def test_invalid_request_never_constructs_executor(self):
        main = load_main()
        calls = []

        def factory():
            calls.append("constructed")

            def executor(prompt, schema):
                return response()

            return executor

        client = TestClient(
            main.create_app(
                synthesis_executor_factory=factory,
            )
        )

        result = client.post(
            "/opportunities/synthesize",
            json={
                "profile": {"goal": "make me rich"},
                "evidence_items": evidence(),
            },
        ).json()

        self.assertEqual(calls, [])
        self.assertIn(
            result["status"],
            {"INVALID", "FAIL_CLOSED"},
        )

    def test_fake_executor_places_hypothesis_in_build_operate(self):
        main = load_main()
        calls = []

        def factory():
            calls.append("constructed")

            def executor(prompt, schema):
                calls.append("called")
                return response()

            return executor

        client = TestClient(
            main.create_app(
                synthesis_executor_factory=factory,
            )
        )

        result = client.post(
            "/opportunities/synthesize",
            json={
                "profile": profile(),
                "evidence_items": evidence(),
            },
        ).json()

        self.assertEqual(
            result["status"],
            "PASS",
        )

        self.assertEqual(
            calls,
            ["constructed", "called"],
        )

        view = result["product_view"]

        self.assertEqual(
            len(view["build_operate"]),
            1,
        )

        self.assertEqual(
            view["build_operate"][0]["origin"],
            "synthesized",
        )


if __name__ == "__main__":
    unittest.main()
