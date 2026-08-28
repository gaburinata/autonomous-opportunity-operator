import copy
import unittest
from pathlib import Path
from unittest.mock import patch

import opportunity_operator.real_source_decision as bridge

from opportunity_operator.primary_source_intake import (
    ingest_primary_source,
)


PUBLIC = lambda host: ["93.184.216.34"]


def fetcher(url, timeout_seconds, max_bytes):
    del timeout_seconds, max_bytes

    return {
        "status_code": 200,
        "headers": {
            "content-type": "text/plain; charset=utf-8",
        },
        "body": b"Legitimate primary source opportunity evidence.",
        "final_url": url,
        "redirect_chain": [],
    }


def ingestor(url):
    return ingest_primary_source(
        url,
        fetcher=fetcher,
        resolver=PUBLIC,
    )


def profile():
    return {
        "operator_jurisdiction": "Bulgaria",
        "available_capital": "150",
        "max_cash_spend": "0",
        "max_human_hours": "8",
        "objective": "Assess whether this opportunity merits attention.",
    }


class MemoryStore:

    def __init__(self):
        self.completed = {}
        self.claimed = set()

    def load(self, key):
        value = self.completed.get(key)
        return copy.deepcopy(value) if value is not None else None

    def claim(self, key):
        if key in self.claimed:
            return False
        self.claimed.add(key)
        return True

    def complete(self, key, outcome):
        self.completed[key] = copy.deepcopy(outcome)


class SentinelExecutor:

    def runtime_evidence(self):
        return {}


class InvalidEnvelopeExecutor:

    def __init__(self):
        self.calls = []

    def execute(self, stage, event, prior_results):
        self.calls.append(
            (
                stage,
                copy.deepcopy(event),
                copy.deepcopy(prior_results),
            )
        )

        # Invalid by the frozen coordinator contract:
        # CONTINUE may not contain any disposition field.
        return {
            "status": "CONTINUE",
            "disposition": None,
            "reason_codes": [
                "MALFORMED_EXECUTOR_OUTPUT",
            ],
        }

    def runtime_evidence(self):
        return {
            "calls": len(self.calls),
        }


class ExecutorTransparencyRegressionTests(unittest.TestCase):

    def test_exact_executor_object_is_passed_to_coordinator(self):
        executor = SentinelExecutor()
        store = object()
        captured = {}

        def fake_coordinate(event, received_store, received_executor):
            captured["event"] = copy.deepcopy(event)
            captured["store"] = received_store
            captured["executor"] = received_executor

            return {
                "event_id": event["event_id"],
                "opportunity_id": event["opportunity_id"],
                "idempotency_key": "test-key",
                "disposition": "WATCH",
                "reason_codes": ["TEST_COORDINATOR_RETURN"],
                "stage_trace": [],
                "replayed": False,
            }

        with patch.object(
            bridge,
            "coordinate_opportunity_event",
            side_effect=fake_coordinate,
        ):
            result = bridge.execute_primary_source_decision(
                "https://example.com/opportunity",
                "opp-transparency",
                profile(),
                store_factory=lambda: store,
                executor_factory=lambda: executor,
                ingestor=ingestor,
            )

        self.assertEqual(result["status"], "PASS")
        self.assertIs(captured["executor"], executor)
        self.assertIs(captured["store"], store)

    def test_disposition_null_continue_is_not_sanitized_by_bridge(self):
        executor = InvalidEnvelopeExecutor()
        store = MemoryStore()

        result = bridge.execute_primary_source_decision(
            "https://example.com/opportunity",
            "opp-invalid-envelope",
            profile(),
            store_factory=lambda: store,
            executor_factory=lambda: executor,
            ingestor=ingestor,
        )

        self.assertEqual(result["status"], "PASS")

        self.assertEqual(
            result["outcome"]["disposition"],
            "KILL",
        )

        self.assertEqual(
            result["outcome"]["reason_codes"],
            ["INVALID_STAGE_RESULT"],
        )

        self.assertEqual(len(executor.calls), 1)

    def test_bridge_contains_no_executor_adapter(self):
        source = Path(bridge.__file__).read_text(encoding="utf-8")

        self.assertNotIn("_CanonicalExecutor", source)
        self.assertNotIn("CanonicalExecutor", source)


if __name__ == "__main__":
    unittest.main()
