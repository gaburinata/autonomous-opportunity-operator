from __future__ import annotations

import json
import unittest

from opportunity_operator.synthesis_runtime import (
    SYNTHESIS_RESPONSE_SCHEMA,
    execute_evidence_backed_synthesis,
)


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
        "skills_assets": ["Python"],
        "constraints": ["No leverage"],
    }


def evidence():
    return [
        {
            "source_id": "source-1",
            "source_url": "https://example.org/source",
            "title": "Primary evidence",
            "excerpt": (
                "A documented machine-readable interface "
                "supports repeated automated access."
            ),
        }
    ]


def model_response():
    return {
        "observations": [
            {
                "title": "Automated evidence service",
                "observed_condition": (
                    "A documented machine-readable interface exists."
                ),
                "economic_mechanism": (
                    "Useful processed output may support usage payment."
                ),
                "value_source": "Users of processed output.",
                "why_ai_changes_feasibility": (
                    "Automation reduces recurring transformation work."
                ),
                "assumptions": [],
                "cheap_test": "Build a bounded read-only prototype.",
                "evidence_required": [
                    "Observed demand evidence",
                ],
                "source_ids": [
                    "source-1",
                ],
                "mechanism_hint": "machine_api",
            }
        ]
    }


class JsonSafeRuntimeTests(unittest.TestCase):

    def test_public_runtime_result_is_plain_json_safe(self):
        def executor(prompt, schema):
            return model_response()

        result = execute_evidence_backed_synthesis(
            profile(),
            evidence(),
            executor,
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["candidates"]), 1)

        candidate = result["candidates"][0]

        self.assertIsInstance(candidate, dict)

        encoded = json.dumps(
            result,
            sort_keys=True,
        )

        self.assertIsInstance(encoded, str)

        self.assertEqual(
            candidate["origin"],
            "synthesized",
        )

        self.assertIsNone(
            candidate["capital_required"],
        )

        self.assertIsInstance(
            candidate["source_ids"],
            list,
        )


class ExecutorSchemaTests(unittest.TestCase):

    def observation_properties(self):
        observations = (
            SYNTHESIS_RESPONSE_SCHEMA
            ["properties"]
            ["observations"]
        )

        return observations["items"]["properties"]

    def test_source_ids_schema_requires_nonempty_array(self):
        field = self.observation_properties()["source_ids"]

        self.assertEqual(
            field.get("type"),
            "array",
        )

        self.assertGreaterEqual(
            field.get("minItems", 0),
            1,
        )

    def test_evidence_required_schema_requires_nonempty_array(self):
        field = self.observation_properties()["evidence_required"]

        self.assertEqual(
            field.get("type"),
            "array",
        )

        self.assertGreaterEqual(
            field.get("minItems", 0),
            1,
        )


if __name__ == "__main__":
    unittest.main()
