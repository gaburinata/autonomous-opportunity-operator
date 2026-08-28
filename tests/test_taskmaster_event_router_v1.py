import hashlib
import unittest

from opportunity_operator.event_router import route_opportunity_event


class TaskmasterEventRouterV1Tests(unittest.TestCase):
    def event(self, **overrides):
        value = {
            "event_id": "evt-001",
            "event_type": "opportunity.discovered",
            "opportunity_id": "opp-001",
        }
        value.update(overrides)
        return value

    def expected_key(self, opportunity_id="opp-001", event_id="evt-001"):
        return hashlib.sha256(
            (opportunity_id + "\x00" + event_id).encode("utf-8")
        ).hexdigest()

    def test_new_opportunity_routes_to_primary_source_verification(self):
        result = route_opportunity_event(self.event())

        self.assertEqual(
            result,
            {
                "event_id": "evt-001",
                "opportunity_id": "opp-001",
                "idempotency_key": self.expected_key(),
                "disposition": "PROCESS",
                "next_stage": "PRIMARY_SOURCE_VERIFICATION",
                "reason_codes": ["NEW_OPPORTUNITY"],
            },
        )

    def test_duplicate_event_is_noop(self):
        result = route_opportunity_event(
            self.event(),
            seen_event_ids={"evt-001"},
        )

        self.assertEqual(result["disposition"], "NOOP")
        self.assertEqual(result["next_stage"], "NONE")
        self.assertEqual(result["reason_codes"], ["DUPLICATE_EVENT"])

    def test_duplicate_has_priority_over_human_action(self):
        result = route_opportunity_event(
            self.event(action_class="WALLET_TRANSACTION"),
            seen_event_ids={"evt-001"},
        )

        self.assertEqual(result["disposition"], "NOOP")
        self.assertEqual(result["reason_codes"], ["DUPLICATE_EVENT"])

    def test_spending_requires_human_gate(self):
        result = route_opportunity_event(
            self.event(action_class="SPEND_MONEY")
        )

        self.assertEqual(result["disposition"], "DECISION_REQUIRED")
        self.assertEqual(result["next_stage"], "HUMAN_GATE")
        self.assertEqual(
            result["reason_codes"],
            ["HUMAN_AUTHORIZATION_REQUIRED"],
        )

    def test_external_submission_requires_human_gate(self):
        result = route_opportunity_event(
            self.event(
                event_type="opportunity.economics_changed",
                action_class="EXTERNAL_SUBMISSION",
            )
        )

        self.assertEqual(result["disposition"], "DECISION_REQUIRED")
        self.assertEqual(result["next_stage"], "HUMAN_GATE")

    def test_deadline_change_routes_to_hard_gate(self):
        result = route_opportunity_event(
            self.event(event_type="opportunity.deadline_changed")
        )

        self.assertEqual(result["disposition"], "PROCESS")
        self.assertEqual(result["next_stage"], "DETERMINISTIC_HARD_GATE")
        self.assertEqual(result["reason_codes"], ["DEADLINE_CHANGED"])

    def test_economics_change_routes_to_economic_evidence(self):
        result = route_opportunity_event(
            self.event(event_type="opportunity.economics_changed")
        )

        self.assertEqual(result["next_stage"], "ECONOMIC_EVIDENCE")
        self.assertEqual(result["reason_codes"], ["ECONOMICS_CHANGED"])

    def test_source_change_routes_to_verification(self):
        result = route_opportunity_event(
            self.event(event_type="opportunity.source_changed")
        )

        self.assertEqual(
            result["next_stage"],
            "PRIMARY_SOURCE_VERIFICATION",
        )
        self.assertEqual(result["reason_codes"], ["SOURCE_CHANGED"])

    def test_failure_memory_change_routes_to_failure_memory(self):
        result = route_opportunity_event(
            self.event(
                event_type="opportunity.failure_memory_changed"
            )
        )

        self.assertEqual(result["next_stage"], "FAILURE_MEMORY")
        self.assertEqual(
            result["reason_codes"],
            ["FAILURE_MEMORY_CHANGED"],
        )

    def test_unknown_event_watches(self):
        result = route_opportunity_event(
            self.event(event_type="something.new")
        )

        self.assertEqual(result["disposition"], "WATCH")
        self.assertEqual(result["next_stage"], "NONE")
        self.assertEqual(
            result["reason_codes"],
            ["UNSUPPORTED_EVENT_TYPE"],
        )

    def test_invalid_event_fails_closed(self):
        result = route_opportunity_event(
            {
                "event_id": "",
                "event_type": "opportunity.discovered",
                "opportunity_id": "opp-001",
            }
        )

        self.assertEqual(
            result,
            {
                "event_id": "",
                "opportunity_id": "opp-001",
                "idempotency_key": "",
                "disposition": "FAIL_CLOSED",
                "next_stage": "NONE",
                "reason_codes": ["INVALID_EVENT"],
            },
        )

    def test_input_and_seen_collection_are_not_mutated(self):
        event = self.event(extra={"a": 1})
        before = {
            "event_id": event["event_id"],
            "event_type": event["event_type"],
            "opportunity_id": event["opportunity_id"],
            "extra": {"a": 1},
        }

        seen = ["old-event"]
        seen_before = list(seen)

        first = route_opportunity_event(event, seen)
        second = route_opportunity_event(event, seen)

        self.assertEqual(first, second)
        self.assertEqual(event, before)
        self.assertEqual(seen, seen_before)
        self.assertEqual(
            first["idempotency_key"],
            self.expected_key(),
        )


if __name__ == "__main__":
    unittest.main()
