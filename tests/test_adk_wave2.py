from datetime import timedelta
import inspect
import unittest
from unittest.mock import patch

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool

from opportunity_operator.agent import MODEL, root_agent
from opportunity_operator.adk_tools import (
    ECONOMICS_STATE_KEY, FAILURE_STATE_KEY, GATE_STATE_KEY,
    calculate_unit_economics, eligibility_capital_deadline_gate,
    failure_memory_similarity_check, final_evidence_safety_adjudication,
)
from opportunity_operator.fixtures import FIXTURE_NOW, contest_opportunity
from opportunity_operator.models import State
from opportunity_operator.pipeline import OpportunityPipeline


class FakeToolContext:
    def __init__(self):
        self.state = {}
        self.function_call_id = "offline-test-call"


class AdkWave2Tests(unittest.TestCase):
    def setUp(self):
        self.context = FakeToolContext()

    def gate(self, context=None, **changes):
        values = {"eligible": True, "deadline_utc": None,
                  "evaluated_at_utc": FIXTURE_NOW.isoformat(), "capital_required": "0",
                  "tool_context": context or self.context}
        values.update(changes)
        return eligibility_capital_deadline_gate(**values)

    def failure(self, context=None, records=None):
        return failure_memory_similarity_check([], records or [], context or self.context)

    def economics(self, revenue="1", cost="0.2", confidence=".99", context=None):
        return calculate_unit_economics(revenue, cost, confidence, ["e1"], context or self.context)

    def final(self, context=None, sequence=1):
        return final_evidence_safety_adjudication("test", ["e1"], sequence,
                                                  context or self.context)

    def populate(self, gate_changes=None, economics_args=None, failure_records=None):
        self.gate(**(gate_changes or {}))
        self.economics(**(economics_args or {}))
        self.failure(records=failure_records)

    def test_root_agent_is_genuine_adk_topology(self):
        self.assertIsInstance(root_agent, SequentialAgent)
        self.assertEqual(len(root_agent.sub_agents), 7)
        self.assertTrue(all(isinstance(agent, LlmAgent) for agent in root_agent.sub_agents))
        self.assertTrue(all(agent.model == MODEL for agent in root_agent.sub_agents))
        self.assertEqual(MODEL, "gemini-3.5-flash")

    def test_expected_native_function_tools_are_present(self):
        tool_names = {getattr(tool, "name", getattr(tool, "__name__", ""))
                      for agent in root_agent.sub_agents for tool in agent.tools}
        self.assertEqual(tool_names, {"eligibility_capital_deadline_gate", "calculate_unit_economics",
                                     "failure_memory_similarity_check", "final_evidence_safety_adjudication"})

    def test_constructing_and_importing_topology_never_calls_model(self):
        with patch("google.adk.models.google_llm.Gemini.generate_content_async",
                   side_effect=AssertionError("live model call")) as generate:
            self.assertEqual(root_agent.name, "autonomous_opportunity_operator")
            generate.assert_not_called()

    def test_final_schema_has_no_model_supplied_intermediate_results(self):
        parameters = inspect.signature(final_evidence_safety_adjudication).parameters
        for forbidden in ("gate_result", "economics_result", "failure_result"):
            self.assertNotIn(forbidden, parameters)
        final_tool = FunctionTool(final_evidence_safety_adjudication)
        schema = final_tool._get_declaration().model_dump()
        schema_text = str(schema)
        for forbidden in ("gate_result", "economics_result", "failure_result", "tool_context"):
            self.assertNotIn(forbidden, schema_text)

    def test_negative_margin_with_qualitative_confidence_is_authoritative(self):
        result = self.economics("0.01", "0.20", "HIGH")
        self.assertEqual(result["disposition"], "KILL")
        self.assertIn("NON_POSITIVE_UNIT_MARGIN", result["reason_codes"])
        self.assertNotIn("error", result)

    def test_positive_margin_with_malformed_confidence_watches(self):
        result = self.economics("1", ".20", "HIGH")
        self.assertEqual(result["disposition"], "WATCH")
        self.assertEqual(result["reason_codes"], ["MALFORMED_OR_MISSING_CONFIDENCE"])

    def test_tools_write_exact_returned_result_to_state(self):
        gate = self.gate()
        economics = self.economics()
        failure = self.failure()
        self.assertIs(self.context.state[GATE_STATE_KEY], gate)
        self.assertIs(self.context.state[ECONOMICS_STATE_KEY], economics)
        self.assertIs(self.context.state[FAILURE_STATE_KEY], failure)

    def test_final_reads_state_and_preserves_economics_kill_reason(self):
        self.populate(economics_args={"revenue": ".01", "cost": ".20", "confidence": "HIGH"})
        result = self.final()
        self.assertEqual(result["disposition"], "KILL")
        self.assertIn("NON_POSITIVE_UNIT_MARGIN", result["reason_codes"])

    def test_fake_promote_cannot_bypass_authoritative_economics_kill(self):
        self.populate(economics_args={"revenue": "1", "cost": "2"})
        with self.assertRaises(TypeError):
            final_evidence_safety_adjudication("test", [], 1, self.context,
                                               economics_result={"disposition": "PROMOTE"})
        self.assertEqual(self.final()["disposition"], "KILL")

    def test_missing_authoritative_economics_fails_closed(self):
        self.gate()
        self.failure()
        result = self.final()
        self.assertEqual(result["disposition"], "KILL")
        self.assertEqual(result["reason_codes"], ["MISSING_AUTHORITATIVE_ECONOMICS_RESULT"])

    def test_invalid_authoritative_state_fails_closed(self):
        self.populate()
        self.context.state[ECONOMICS_STATE_KEY] = {"disposition": "PROMOTE"}
        self.assertEqual(self.final()["reason_codes"], ["INVALID_AUTHORITATIVE_STATE"])

    def test_ineligibility_deadline_and_hard_gate_precedence(self):
        for changes in ({"eligible": False},
                        {"deadline_utc": (FIXTURE_NOW - timedelta(seconds=1)).isoformat()},
                        {"capital_required": "1"}):
            context = FakeToolContext()
            self.gate(context, **changes)
            self.economics(context=context)
            self.failure(context=context)
            result = self.final(context)
            expected = "DECISION_REQUIRED" if "capital_required" in changes else "KILL"
            self.assertEqual(result["disposition"], expected)

    def test_failure_warning_forces_watch_with_positive_economics(self):
        failure = {"memory_id": "synthetic-1", "hypothesis": "x", "environment": "test",
                   "parameter_regime": {}, "failure_class": "TEST_FAILURE",
                   "evidence": [{"source_id": "synthetic:e1", "digest": "abc123"}],
                   "similarity_signature": ["crowded", "tail-risk"],
                   "reconsideration_conditions": ["new evidence"]}
        self.gate()
        self.economics()
        failure_memory_similarity_check(["crowded", "tail-risk"], [failure], self.context)
        result = self.final(sequence=4)
        self.assertEqual(result["disposition"], "WATCH")
        self.assertIn("KNOWN_FAILURE_SIMILARITY", result["reason_codes"])

    def test_provenance_survives_and_digest_is_stable(self):
        self.populate()
        first = self.final(sequence=9)
        second = self.final(sequence=9)
        self.assertEqual(first, second)
        self.assertEqual(first["source_identity"], "test")
        self.assertEqual(len(first["stable_digest"]), 64)

    def test_malformed_external_failure_evidence_is_rejected(self):
        malformed = {"memory_id": "bad", "hypothesis": "x", "environment": "x",
                     "parameter_regime": {}, "failure_class": "x", "evidence": [],
                     "similarity_signature": ["x"], "reconsideration_conditions": []}
        result = failure_memory_similarity_check(["x"], [malformed], self.context)
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["rejected_records"][0]["reason_code"], "MALFORMED_FAILURE_EVIDENCE")

    def test_wave0_pipeline_remains_authoritative(self):
        result = OpportunityPipeline().run(contest_opportunity(eligible=False), FIXTURE_NOW)
        self.assertEqual(result.final_state, State.KILL)


if __name__ == "__main__":
    unittest.main()
