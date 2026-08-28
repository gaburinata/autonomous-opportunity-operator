import unittest
from unittest.mock import Mock

from opportunity_operator.workflow_coordinator import coordinate_opportunity_event


class EventWorkflowCoordinatorInvalidIdentityRegressionV1Tests(unittest.TestCase):
    def test_preserves_authoritative_invalid_event_route_with_malformed_event_id(self):
        event = {
            "event_id": 7,
            "event_type": "opportunity.discovered",
            "opportunity_id": "opp-001",
            "payload": {"sources": ["primary"]},
        }
        store = Mock()
        executor = Mock()

        result = coordinate_opportunity_event(event, store, executor)

        self.assertEqual(
            result,
            {
                "event_id": 7,
                "opportunity_id": "opp-001",
                "idempotency_key": "",
                "disposition": "FAIL_CLOSED",
                "reason_codes": ["INVALID_EVENT"],
                "stage_trace": [],
                "replayed": False,
            },
        )
        self.assertEqual(store.mock_calls, [])
        self.assertEqual(executor.mock_calls, [])


if __name__ == "__main__":
    unittest.main()
