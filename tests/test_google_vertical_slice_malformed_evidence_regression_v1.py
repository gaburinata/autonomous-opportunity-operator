"""Regression coverage for malformed ADK evidence at non-final stages."""

import unittest
from unittest.mock import patch

from opportunity_operator.cloud_vertical_slice import CloudAdkExecutor


NON_FINAL_STAGE = "PRIMARY_SOURCE_VERIFICATION"
EVENT = {"event_id": "evt-malformed-evidence-regression"}
RECOGNIZED_TOOL = "eligibility_capital_deadline_gate"


class CloudAdkExecutorMalformedEvidenceRegressionTests(unittest.TestCase):
    def _assert_malformed_fails_closed(self, malformed_event):
        workflow_calls = []

        def fake_workflow(event):
            workflow_calls.append(event)
            return [malformed_event]

        executor = CloudAdkExecutor(workflow=fake_workflow)
        with patch.object(
            CloudAdkExecutor,
            "_production_workflow",
            side_effect=AssertionError("injected workflow must bypass cloud execution"),
        ) as production_workflow:
            first = executor.execute(NON_FINAL_STAGE, EVENT, ())
            cached = executor.execute(NON_FINAL_STAGE, EVENT, (first,))

        self.assertEqual(workflow_calls, [EVENT])
        production_workflow.assert_not_called()
        self.assertEqual(first, cached, "cached fail-closed result must be deterministic")
        self.assertEqual(set(first), {"status", "disposition", "reason_codes"})
        self.assertEqual(first["status"], "TERMINAL")
        self.assertEqual(first["disposition"], "KILL")
        self.assertIsInstance(first["reason_codes"], list)
        self.assertTrue(first["reason_codes"])
        self.assertTrue(
            all(isinstance(code, str) and code for code in first["reason_codes"])
        )
        self.assertNotIn("ADK_EVIDENCE_OBSERVED", first["reason_codes"])
        self.assertEqual(executor.runtime_evidence()["adk_workflow_runs"], 1)

    def test_recognized_agent_name_without_event_evidence_fails_closed(self):
        self._assert_malformed_fails_closed({"author": "discovery_agent"})

    def test_string_tool_call_fails_closed(self):
        self._assert_malformed_fails_closed(
            {"author": "tool", "tool_call": RECOGNIZED_TOOL}
        )

    def test_recognized_tool_result_without_result_payload_fails_closed(self):
        self._assert_malformed_fails_closed(
            {"author": "tool", "tool_result": {"name": RECOGNIZED_TOOL}}
        )

    def test_recognized_tool_call_without_arguments_payload_fails_closed(self):
        self._assert_malformed_fails_closed(
            {"author": "tool", "tool_call": {"name": RECOGNIZED_TOOL}}
        )

    def test_canonical_observed_tool_call_can_continue(self):
        workflow_calls = []

        def fake_workflow(event):
            workflow_calls.append(event)
            return [
                {
                    "author": "tool",
                    "tool_call": {"name": RECOGNIZED_TOOL, "arguments": {}},
                }
            ]

        executor = CloudAdkExecutor(workflow=fake_workflow)
        with patch.object(
            CloudAdkExecutor,
            "_production_workflow",
            side_effect=AssertionError("injected workflow must bypass cloud execution"),
        ) as production_workflow:
            result = executor.execute(NON_FINAL_STAGE, EVENT, ())

        self.assertEqual(workflow_calls, [EVENT])
        production_workflow.assert_not_called()
        self.assertEqual(
            result,
            {"status": "CONTINUE", "reason_codes": ["ADK_EVIDENCE_OBSERVED"]},
        )


if __name__ == "__main__":
    unittest.main()
