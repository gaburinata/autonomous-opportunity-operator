import copy
import hashlib
import json
import unittest

from fastapi.testclient import TestClient

import main

from opportunity_operator.primary_source_intake import (
    build_discovered_event,
    ingest_primary_source,
)

from opportunity_operator.real_source_decision import (
    build_decision_event,
    canonicalize_decision_profile,
    execute_primary_source_decision,
)


PUBLIC = lambda host: ["93.184.216.34"]


def fake_fetch(
    body=b"<html><body>Prize opportunity source evidence.</body></html>",
):
    def inner(url, timeout_seconds, max_bytes):
        return {
            "status_code": 200,
            "headers": {
                "content-type": "text/html; charset=utf-8",
            },
            "body": body,
            "final_url": url,
            "redirect_chain": [],
        }

    return inner


def ingestor(url):
    return ingest_primary_source(
        url,
        fetcher=fake_fetch(),
        resolver=PUBLIC,
    )


def profile(**changes):
    value = {
        "operator_jurisdiction": "Bulgaria",
        "available_capital": "150.00",
        "max_cash_spend": "0.00",
        "max_human_hours": "8.500",
        "objective": "Assess whether pursuing this opportunity is worthwhile.",
    }

    value.update(changes)

    return value


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


class FakeExecutor:

    stages = (
        "PRIMARY_SOURCE_VERIFICATION",
        "DETERMINISTIC_HARD_GATE",
        "INVESTIGATION",
        "FAILURE_MEMORY",
        "ECONOMIC_EVIDENCE",
        "FINAL_ADJUDICATION",
    )

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

        self.assert_event(event)

        if stage == "FINAL_ADJUDICATION":
            return {
                "status": "TERMINAL",
                "disposition": "KILL",
                "reason_codes": [
                    "TEST_DECISION_COMPLETE",
                ],
            }

        return {
            "status": "CONTINUE",
            "reason_codes": [
                "TEST_STAGE_COMPLETE",
            ],
        }

    @staticmethod
    def assert_event(event):
        payload = event["payload"]

        assert isinstance(payload["source_text"], str)
        assert payload["source_text"]

        assert len(payload["source_sha256"]) == 64
        assert len(payload["text_sha256"]) == 64

        assert payload["decision_profile"]["operator_jurisdiction"]
        assert payload["decision_profile"]["objective"]

    def runtime_evidence(self):
        return {
            "fake_executor_calls": len(self.calls),
        }


class DecisionProfileTests(unittest.TestCase):

    def test_profile_is_canonical_and_input_is_unchanged(self):
        original = profile()
        before = copy.deepcopy(original)

        result = canonicalize_decision_profile(original)

        self.assertEqual(original, before)

        self.assertEqual(
            result,
            {
                "operator_jurisdiction": "Bulgaria",
                "available_capital": "150",
                "max_cash_spend": "0",
                "max_human_hours": "8.5",
                "objective": (
                    "Assess whether pursuing this opportunity is worthwhile."
                ),
            },
        )

    def test_profile_rejects_invalid_numeric_values_and_extra_keys(self):
        bad = [
            profile(available_capital="-1"),
            profile(max_cash_spend="NaN"),
            profile(max_human_hours="1e2"),
            profile(extra="x"),
        ]

        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    canonicalize_decision_profile(value)


class DecisionEventTests(unittest.TestCase):

    def source_event(self):
        document = ingestor("https://example.com/opportunity")

        return build_discovered_event(
            document,
            "real-opp-001",
        )

    def test_event_identity_is_deterministic_and_profile_sensitive(self):
        source = self.source_event()
        before = copy.deepcopy(source)

        first = build_decision_event(source, profile())
        second = build_decision_event(source, profile())

        changed = build_decision_event(
            source,
            profile(max_human_hours="9"),
        )

        self.assertEqual(first, second)
        self.assertNotEqual(first["event_id"], changed["event_id"])
        self.assertEqual(source, before)

        canonical = canonicalize_decision_profile(profile())

        payload = json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        expected = hashlib.sha256(
            (
                source["event_id"]
                + "\x00"
                + payload
            ).encode("utf-8")
        ).hexdigest()

        self.assertEqual(
            first["event_id"],
            "decision-" + expected,
        )

        self.assertEqual(
            first["payload"]["source_event_id"],
            source["event_id"],
        )

        self.assertEqual(
            first["payload"]["source_text"],
            source["payload"]["source_text"],
        )

        self.assertNotIn("action_class", first)


class BridgeExecutionTests(unittest.TestCase):

    def test_intake_failure_constructs_no_store_or_executor(self):
        store_calls = []
        executor_calls = []

        def bad_ingestor(url):
            del url

            return {
                "status": "FAIL_CLOSED",
                "reason_codes": ["SOURCE_FETCH_FAILED"],
            }

        result = execute_primary_source_decision(
            "https://example.com/x",
            "opp-x",
            profile(),
            store_factory=lambda: store_calls.append(1),
            executor_factory=lambda: executor_calls.append(1),
            ingestor=bad_ingestor,
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(store_calls, [])
        self.assertEqual(executor_calls, [])

    def test_same_source_and_profile_replays_without_executor(self):
        store = MemoryStore()
        created = []

        def factory():
            executor = FakeExecutor()
            created.append(executor)
            return executor

        first = execute_primary_source_decision(
            "https://example.com/opportunity",
            "opp-replay",
            profile(),
            store_factory=lambda: store,
            executor_factory=factory,
            ingestor=ingestor,
        )

        second = execute_primary_source_decision(
            "https://example.com/opportunity",
            "opp-replay",
            profile(),
            store_factory=lambda: store,
            executor_factory=factory,
            ingestor=ingestor,
        )

        self.assertEqual(first["status"], "PASS")
        self.assertEqual(second["status"], "PASS")

        self.assertFalse(first["outcome"]["replayed"])
        self.assertTrue(second["outcome"]["replayed"])

        # Executor is created only after durable replay check would be ideal,
        # but the current coordinator receives an executor object.
        # The important invariant is zero execute() calls on replay.
        self.assertEqual(len(created[0].calls), 6)
        self.assertEqual(len(created[1].calls), 0)

        self.assertEqual(
            first["decision_event_id"],
            second["decision_event_id"],
        )

    def test_changed_profile_creates_new_workflow_identity(self):
        store = MemoryStore()

        first_executor = FakeExecutor()
        second_executor = FakeExecutor()

        first = execute_primary_source_decision(
            "https://example.com/opportunity",
            "opp-profile",
            profile(),
            store_factory=lambda: store,
            executor_factory=lambda: first_executor,
            ingestor=ingestor,
        )

        second = execute_primary_source_decision(
            "https://example.com/opportunity",
            "opp-profile",
            profile(max_human_hours="10"),
            store_factory=lambda: store,
            executor_factory=lambda: second_executor,
            ingestor=ingestor,
        )

        self.assertNotEqual(
            first["decision_event_id"],
            second["decision_event_id"],
        )

        self.assertEqual(len(first_executor.calls), 6)
        self.assertEqual(len(second_executor.calls), 6)

    def test_compact_result_never_contains_source_text(self):
        store = MemoryStore()

        result = execute_primary_source_decision(
            "https://example.com/opportunity",
            "opp-compact",
            profile(),
            store_factory=lambda: store,
            executor_factory=FakeExecutor,
            ingestor=ingestor,
        )

        self.assertEqual(result["status"], "PASS")
        self.assertNotIn("source_text", result["source_evidence"])

        serialized = json.dumps(result, sort_keys=True)

        self.assertNotIn(
            "Prize opportunity source evidence",
            serialized,
        )


class FastApiBridgeTests(unittest.TestCase):

    def test_endpoint_reuses_injected_bridge_dependencies(self):
        store = MemoryStore()
        created = []

        def executor_factory():
            executor = FakeExecutor()
            created.append(executor)
            return executor

        app = main.create_app(
            store_factory=lambda: store,
            executor_factory=executor_factory,
            primary_source_ingestor=ingestor,
        )

        client = TestClient(app)

        response = client.post(
            "/decision/primary-source",
            json={
                "source_url": "https://example.com/opportunity",
                "opportunity_id": "opp-http",
                "decision_profile": profile(),
            },
        )

        self.assertEqual(response.status_code, 200)

        payload = response.json()

        self.assertEqual(
            payload["scenario"],
            "real-primary-source-decision",
        )

        self.assertEqual(payload["status"], "PASS")

        self.assertEqual(
            payload["outcome"]["disposition"],
            "KILL",
        )

        self.assertEqual(len(created), 1)
        self.assertEqual(len(created[0].calls), 6)

        self.assertNotIn(
            "Prize opportunity source evidence",
            json.dumps(payload),
        )

    def test_invalid_profile_does_not_fetch_or_construct_executor(self):
        intake_calls = []
        executor_calls = []

        def forbidden_ingestor(url):
            intake_calls.append(url)
            raise AssertionError("must validate profile before fetch")

        app = main.create_app(
            store_factory=lambda: MemoryStore(),
            executor_factory=lambda: executor_calls.append(1),
            primary_source_ingestor=forbidden_ingestor,
        )

        client = TestClient(app)

        response = client.post(
            "/decision/primary-source",
            json={
                "source_url": "https://example.com/opportunity",
                "opportunity_id": "opp-invalid",
                "decision_profile": profile(
                    available_capital="-5",
                ),
            },
        )

        self.assertEqual(response.status_code, 200)

        payload = response.json()

        self.assertEqual(payload["status"], "FAIL_CLOSED")
        self.assertEqual(intake_calls, [])
        self.assertEqual(executor_calls, [])


if __name__ == "__main__":
    unittest.main()
