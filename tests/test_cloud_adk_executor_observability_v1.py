import json
import unittest

from opportunity_operator.cloud_vertical_slice import CloudAdkExecutor


EVENT = {
    "event_id": "observability-test-event",
    "event_type": "opportunity.discovered",
    "opportunity_id": "observability-test-opportunity",
    "payload": {},
}


class CloudAdkExecutorObservabilityTests(unittest.TestCase):

    def test_workflow_exception_is_fail_closed_but_classified_safely(self):
        def workflow(event):
            del event
            raise RuntimeError("TOP_SECRET_EXCEPTION_TEXT")

        executor = CloudAdkExecutor(workflow=workflow)

        result = executor.execute(
            "PRIMARY_SOURCE_VERIFICATION",
            EVENT,
            [],
        )

        self.assertEqual(
            result,
            {
                "status": "TERMINAL",
                "disposition": "KILL",
                "reason_codes": [
                    "MISSING_ADK_WORKFLOW_EVIDENCE",
                ],
            },
        )

        runtime = executor.runtime_evidence()

        self.assertEqual(
            runtime["workflow_state"],
            "WORKFLOW_EXCEPTION",
        )
        self.assertEqual(
            runtime["workflow_error_phase"],
            "WORKFLOW",
        )
        self.assertEqual(
            runtime["workflow_error_type"],
            "RuntimeError",
        )
        self.assertEqual(
            runtime["raw_stream_items_seen"],
            0,
        )
        self.assertEqual(
            runtime["normalized_stream_items_seen"],
            0,
        )

        # Sensitive exception text must never enter runtime evidence.
        self.assertNotIn(
            "TOP_SECRET_EXCEPTION_TEXT",
            json.dumps(runtime),
        )

    def test_normalization_exception_is_distinguished_and_safe(self):
        def workflow(event):
            del event
            return [
                {
                    "author": "discovery_agent",
                    "text": "candidate event",
                }
            ]

        executor = CloudAdkExecutor(workflow=workflow)

        def broken_normalizer(item):
            del item
            raise ValueError("SECRET_NORMALIZATION_TEXT")

        executor._normalize = broken_normalizer

        result = executor.execute(
            "PRIMARY_SOURCE_VERIFICATION",
            EVENT,
            [],
        )

        self.assertEqual(
            result["reason_codes"],
            ["MISSING_ADK_WORKFLOW_EVIDENCE"],
        )

        runtime = executor.runtime_evidence()

        self.assertEqual(
            runtime["workflow_state"],
            "NORMALIZATION_EXCEPTION",
        )
        self.assertEqual(
            runtime["workflow_error_phase"],
            "NORMALIZATION",
        )
        self.assertEqual(
            runtime["workflow_error_type"],
            "ValueError",
        )
        self.assertEqual(
            runtime["raw_stream_items_seen"],
            1,
        )
        self.assertEqual(
            runtime["normalized_stream_items_seen"],
            0,
        )

        self.assertNotIn(
            "SECRET_NORMALIZATION_TEXT",
            json.dumps(runtime),
        )

    def test_true_empty_stream_is_distinguished_from_exception(self):
        def workflow(event):
            del event
            return []

        executor = CloudAdkExecutor(workflow=workflow)

        result = executor.execute(
            "PRIMARY_SOURCE_VERIFICATION",
            EVENT,
            [],
        )

        self.assertEqual(
            result["reason_codes"],
            ["MISSING_ADK_WORKFLOW_EVIDENCE"],
        )

        runtime = executor.runtime_evidence()

        self.assertEqual(
            runtime["workflow_state"],
            "EMPTY_STREAM",
        )
        self.assertIsNone(
            runtime["workflow_error_phase"],
        )
        self.assertIsNone(
            runtime["workflow_error_type"],
        )
        self.assertEqual(
            runtime["raw_stream_items_seen"],
            0,
        )
        self.assertEqual(
            runtime["normalized_stream_items_seen"],
            0,
        )

    def test_unrecognized_stream_is_distinguished_from_empty_stream(self):
        def workflow(event):
            del event

            return [
                {
                    "author": "unknown_runtime_author",
                    "text": "some event was returned",
                }
            ]

        executor = CloudAdkExecutor(workflow=workflow)

        result = executor.execute(
            "PRIMARY_SOURCE_VERIFICATION",
            EVENT,
            [],
        )

        self.assertEqual(
            result["reason_codes"],
            ["MISSING_ADK_WORKFLOW_EVIDENCE"],
        )

        runtime = executor.runtime_evidence()

        self.assertEqual(
            runtime["workflow_state"],
            "UNRECOGNIZED_STREAM",
        )
        self.assertEqual(
            runtime["raw_stream_items_seen"],
            1,
        )
        self.assertEqual(
            runtime["normalized_stream_items_seen"],
            1,
        )
        self.assertEqual(runtime["agents_seen"], [])
        self.assertEqual(runtime["tools_called"], [])

    def test_valid_agent_evidence_remains_continue(self):
        def workflow(event):
            del event

            return [
                {
                    "author": "discovery_agent",
                    "text": "evidence observed",
                }
            ]

        executor = CloudAdkExecutor(workflow=workflow)

        result = executor.execute(
            "PRIMARY_SOURCE_VERIFICATION",
            EVENT,
            [],
        )

        self.assertEqual(
            result,
            {
                "status": "CONTINUE",
                "reason_codes": [
                    "ADK_EVIDENCE_OBSERVED",
                ],
            },
        )

        runtime = executor.runtime_evidence()

        self.assertEqual(
            runtime["workflow_state"],
            "EVIDENCE_OBSERVED",
        )
        self.assertEqual(
            runtime["raw_stream_items_seen"],
            1,
        )
        self.assertEqual(
            runtime["normalized_stream_items_seen"],
            1,
        )
        self.assertEqual(
            runtime["agents_seen"],
            ["discovery_agent"],
        )
        self.assertIsNone(
            runtime["workflow_error_type"],
        )


if __name__ == "__main__":
    unittest.main()
