import ast
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from opportunity_operator.workflow_coordinator import coordinate_opportunity_event


STAGES = [
    "PRIMARY_SOURCE_VERIFICATION",
    "DETERMINISTIC_HARD_GATE",
    "INVESTIGATION",
    "FAILURE_MEMORY",
    "ECONOMIC_EVIDENCE",
    "FINAL_ADJUDICATION",
]


class MemoryStore:
    def __init__(self):
        self.records = {}
        self.claims = set()
        self.calls = []

    def load(self, key):
        self.calls.append(("load", key))
        value = self.records.get(key)
        return copy.deepcopy(value) if value is not None else None

    def claim(self, key):
        self.calls.append(("claim", key))
        if key in self.claims:
            return False
        self.claims.add(key)
        return True

    def complete(self, key, outcome):
        self.calls.append(("complete", key))
        self.records[key] = copy.deepcopy(outcome)


class ScriptedExecutor:
    def __init__(self, terminal="PROMOTE", stop_at="FINAL_ADJUDICATION"):
        self.calls = []
        self.terminal = terminal
        self.stop_at = stop_at

    def execute(self, stage, event, prior_results):
        self.calls.append((stage, copy.deepcopy(event), copy.deepcopy(prior_results)))
        if stage == self.stop_at:
            return {
                "status": "TERMINAL",
                "disposition": self.terminal,
                "reason_codes": ["SCRIPTED_TERMINAL"],
            }
        return {"status": "CONTINUE", "reason_codes": ["SCRIPTED_CONTINUE"]}


class EventWorkflowCoordinatorV1Tests(unittest.TestCase):
    def event(self, **overrides):
        event = {
            "event_id": "evt-001",
            "event_type": "opportunity.discovered",
            "opportunity_id": "opp-001",
            "payload": {"sources": ["primary"]},
        }
        event.update(overrides)
        return event

    def test_process_runs_ordered_stages_to_terminal_and_traces_order(self):
        executor = ScriptedExecutor()
        result = coordinate_opportunity_event(self.event(), MemoryStore(), executor)

        self.assertEqual([call[0] for call in executor.calls], STAGES)
        self.assertEqual([entry["stage"] for entry in result["stage_trace"]], STAGES)
        self.assertEqual([entry["sequence"] for entry in result["stage_trace"]], list(range(1, 7)))
        self.assertEqual(result["disposition"], "PROMOTE")
        self.assertEqual(result["reason_codes"], ["SCRIPTED_TERMINAL"])
        self.assertFalse(result["replayed"])

    def test_router_is_called_once_and_its_later_stage_is_authoritative(self):
        route = {
            "event_id": "router-event",
            "opportunity_id": "router-opportunity",
            "idempotency_key": "router-key",
            "disposition": "PROCESS",
            "next_stage": "ECONOMIC_EVIDENCE",
            "reason_codes": ["ROUTER_REASON"],
        }
        executor = ScriptedExecutor()
        with patch(
            "opportunity_operator.workflow_coordinator.route_opportunity_event",
            return_value=route,
        ) as router:
            result = coordinate_opportunity_event(self.event(), MemoryStore(), executor)

        router.assert_called_once()
        self.assertEqual(router.call_args.args[0], self.event())
        self.assertEqual([call[0] for call in executor.calls], STAGES[-2:])
        self.assertEqual(result["event_id"], "router-event")
        self.assertEqual(result["opportunity_id"], "router-opportunity")
        self.assertEqual(result["idempotency_key"], "router-key")

    def test_replay_returns_stable_copy_without_executing_again(self):
        store = MemoryStore()
        executor = ScriptedExecutor(terminal="KILL", stop_at="DETERMINISTIC_HARD_GATE")
        first = coordinate_opportunity_event(self.event(), store, executor)
        calls_after_first = len(executor.calls)
        second = coordinate_opportunity_event(self.event(), store, executor)

        self.assertEqual(len(executor.calls), calls_after_first)
        self.assertFalse(first["replayed"])
        self.assertTrue(second["replayed"])
        self.assertEqual(first["disposition"], second["disposition"])
        self.assertEqual(first["reason_codes"], second["reason_codes"])
        self.assertEqual(first["stage_trace"], second["stage_trace"])
        self.assertFalse(store.records[first["idempotency_key"]]["replayed"])

    def test_human_action_is_persisted_decision_required_without_execution(self):
        store = MemoryStore()
        executor = ScriptedExecutor()
        event = self.event(action_class="EXTERNAL_SUBMISSION")

        first = coordinate_opportunity_event(event, store, executor)
        second = coordinate_opportunity_event(event, store, executor)

        self.assertEqual(first["disposition"], "DECISION_REQUIRED")
        self.assertEqual(first["reason_codes"], ["HUMAN_AUTHORIZATION_REQUIRED"])
        self.assertEqual(first["stage_trace"], [])
        self.assertEqual(executor.calls, [])
        self.assertTrue(second["replayed"])

    def test_intermediate_decision_required_stops_and_is_preserved(self):
        executor = ScriptedExecutor(terminal="DECISION_REQUIRED", stop_at="DETERMINISTIC_HARD_GATE")
        result = coordinate_opportunity_event(self.event(), MemoryStore(), executor)

        self.assertEqual([call[0] for call in executor.calls], STAGES[:2])
        self.assertEqual(result["disposition"], "DECISION_REQUIRED")
        self.assertEqual(result["reason_codes"], ["SCRIPTED_TERMINAL"])

    def test_invalid_router_result_fails_closed_without_store_or_executor(self):
        store = MemoryStore()
        executor = ScriptedExecutor()
        invalid_route = {
            "event_id": "evt-001",
            "opportunity_id": "opp-001",
            "idempotency_key": "key",
            "disposition": "PROCESS",
            "next_stage": "MADE_UP_STAGE",
            "reason_codes": ["BAD"],
        }
        with patch(
            "opportunity_operator.workflow_coordinator.route_opportunity_event",
            return_value=invalid_route,
        ):
            result = coordinate_opportunity_event(self.event(), store, executor)

        self.assertEqual(result["disposition"], "KILL")
        self.assertEqual(result["reason_codes"], ["INVALID_ROUTER_RESULT"])
        self.assertEqual(store.calls, [])
        self.assertEqual(executor.calls, [])

    def test_invalid_stage_envelopes_fail_closed(self):
        invalid_results = [
            None,
            {"status": "CONTINUE", "reason_codes": []},
            {"status": "CONTINUE", "disposition": "PROMOTE", "reason_codes": ["X"]},
            {"status": "TERMINAL", "reason_codes": ["X"]},
            {"status": "TERMINAL", "disposition": "PROCESS", "reason_codes": ["X"]},
            {"status": "CONTINUE", "reason_codes": ["X"], "extra": True},
        ]
        for invalid in invalid_results:
            with self.subTest(invalid=invalid):
                executor = unittest.mock.Mock()
                executor.execute.return_value = invalid
                result = coordinate_opportunity_event(self.event(), MemoryStore(), executor)
                self.assertEqual(result["disposition"], "KILL")
                self.assertEqual(result["reason_codes"], ["INVALID_STAGE_RESULT"])
                self.assertEqual(result["stage_trace"][0]["status"], "FAILED")
                executor.execute.assert_called_once()

    def test_executor_exception_fails_closed_without_exception_text(self):
        executor = unittest.mock.Mock()
        executor.execute.side_effect = RuntimeError("secret remote detail")
        result = coordinate_opportunity_event(self.event(), MemoryStore(), executor)

        self.assertEqual(result["disposition"], "KILL")
        self.assertEqual(result["reason_codes"], ["WORKFLOW_EXECUTION_FAILED"])
        self.assertEqual(result["stage_trace"][0]["status"], "FAILED")
        self.assertNotIn("secret remote detail", repr(result))

    def test_hard_transition_bound_stops_before_next_invocation(self):
        executor = ScriptedExecutor()
        result = coordinate_opportunity_event(
            self.event(), MemoryStore(), executor, max_transitions=5
        )

        self.assertEqual([call[0] for call in executor.calls], STAGES[:5])
        self.assertEqual(result["disposition"], "KILL")
        self.assertEqual(result["reason_codes"], ["MAX_TRANSITIONS_EXCEEDED"])
        self.assertEqual(len(result["stage_trace"]), 5)

    def test_event_is_deeply_unmodified_even_if_executor_mutates_its_copy(self):
        event = self.event()
        before = copy.deepcopy(event)

        class MutatingExecutor(ScriptedExecutor):
            def execute(self, stage, received_event, prior_results):
                received_event["payload"]["sources"].append("mutated")
                return super().execute(stage, received_event, prior_results)

        coordinate_opportunity_event(event, MemoryStore(), MutatingExecutor())
        self.assertEqual(event, before)

    def test_module_has_no_external_or_model_cloud_integrations(self):
        module_path = Path(__file__).parents[1] / "src/opportunity_operator/workflow_coordinator.py"
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        forbidden_imports = {
            "google", "requests", "httpx", "boto3", "openai", "anthropic",
            "vertexai", "firebase_admin", "google_cloud", "subprocess",
        }
        self.assertTrue(imports.isdisjoint(forbidden_imports), imports & forbidden_imports)
        lowered = source.lower()
        for forbidden in ("firestore", "cloud run", "pub/sub", "root_agent", "gemini"):
            self.assertNotIn(forbidden, lowered)


if __name__ == "__main__":
    unittest.main()
