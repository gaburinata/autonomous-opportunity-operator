from datetime import timezone
from decimal import Decimal
import unittest

from opportunity_operator.fixtures import (FIXTURE_NOW, contest_opportunity,
    failure_like_trading_opportunity, historical_trading_failure, terrible_api_opportunity)
from opportunity_operator.models import State
from opportunity_operator.pipeline import OpportunityPipeline


NOW = FIXTURE_NOW


class PipelineTests(unittest.TestCase):
    def test_ineligible_is_killed_before_expensive_investigation(self):
        result = OpportunityPipeline().run(contest_opportunity(eligible=False), NOW)
        self.assertEqual(result.final_state, State.KILL)
        self.assertFalse(result.expensive_investigation_started)
        self.assertIn("INELIGIBLE", result.events[2].payload["reasons"])

    def test_bad_machine_unit_economics_is_killed(self):
        result = OpportunityPipeline().run(terrible_api_opportunity(), NOW)
        self.assertEqual(result.final_state, State.KILL)
        self.assertEqual(result.economic_decision.margin_per_unit, Decimal("-0.19"))
        self.assertIn("NON_POSITIVE_UNIT_MARGIN", result.economic_decision.reason_codes)

    def test_known_failure_triggers_anti_repeat_warning(self):
        result = OpportunityPipeline((historical_trading_failure(),)).run(failure_like_trading_opportunity(), NOW)
        self.assertTrue(result.failure_matches[0].warning)
        self.assertEqual(result.failure_matches[0].score, Decimal("1"))
        self.assertEqual(result.final_state, State.WATCH)
        self.assertIn("KNOWN_FAILURE_SIMILARITY", result.economic_decision.reason_codes)

    def test_capital_action_requires_human_decision(self):
        result = OpportunityPipeline().run(contest_opportunity(capital="25"), NOW)
        self.assertEqual(result.final_state, State.DECISION_REQUIRED)
        self.assertFalse(result.expensive_investigation_started)

    def test_provenance_is_retained_and_payload_is_immutable(self):
        opportunity = contest_opportunity()
        result = OpportunityPipeline().run(opportunity, NOW)
        self.assertEqual(result.events[0].source_ref, "primary:contest-rules")
        self.assertEqual(result.events[0].payload["all_source_ids"], ("primary:contest-rules",))
        self.assertEqual(len(result.events[0].payload_sha256), 64)
        with self.assertRaises(TypeError):
            result.events[0].payload["title"] = "tampered"
        with self.assertRaises(TypeError):
            result.events[0].payload["all_source_ids"][0] = "tampered"


if __name__ == "__main__":
    unittest.main()
