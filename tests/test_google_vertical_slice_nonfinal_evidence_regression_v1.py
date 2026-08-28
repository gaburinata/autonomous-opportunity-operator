"""Regression coverage for missing ADK evidence at non-final stages."""

import unittest

from opportunity_operator.cloud_vertical_slice import CloudAdkExecutor


NON_FINAL_STAGE = "PRIMARY_SOURCE_VERIFICATION"
EVENT = {"event_id": "evt-nonfinal-evidence-regression"}


class CloudAdkExecutorNonFinalEvidenceRegressionTests(unittest.TestCase):
    def _assert_fails_closed(self, workflow):
        executor = CloudAdkExecutor(workflow=workflow)

        first = executor.execute(NON_FINAL_STAGE, EVENT, ())
        cached = executor.execute(NON_FINAL_STAGE, EVENT, ())

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

        evidence = executor.runtime_evidence()
        self.assertEqual(evidence["adk_workflow_runs"], 1)
        self.assertEqual(evidence["agents_seen"], [])
        self.assertEqual(evidence["tools_called"], [])

    def test_workflow_exception_at_non_final_stage_fails_closed(self):
        def raising_workflow(event):
            del event
            raise RuntimeError("synthetic offline workflow failure")

        self._assert_fails_closed(raising_workflow)

    def test_empty_stream_at_non_final_stage_fails_closed(self):
        self._assert_fails_closed(lambda event: [])


if __name__ == "__main__":
    unittest.main()
