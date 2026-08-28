from __future__ import annotations

import unittest

from opportunity_operator.real_source_decision import (
    canonicalize_decision_profile,
)
from opportunity_operator.user_profile import (
    canonicalize_user_profile,
    to_decision_profile,
)
from opportunity_operator.opportunity_synthesis import (
    SynthesisObservation,
    build_synthesized_candidate,
)


def profile(**changes):
    value = {
        "goal": "both",
        "country": "Bulgaria",
        "available_capital": "150",
        "max_cash_spend": "0",
        "human_hours_per_week": "8",
        "ai_autonomy": "maximum",
        "willingness": {
            "build_business": True,
            "work_with_customers": False,
            "sell": False,
            "publish_content": False,
            "invest_capital": False,
            "contests_juries": True,
            "financial_protocols": True,
        },
        "skills_assets": [],
        "constraints": [],
    }
    value.update(changes)
    return value


class V3AuditRegressionTests(unittest.TestCase):

    def test_country_boundary_matches_legacy_contract(self):
        good = canonicalize_user_profile(
            profile(country="B" * 128)
        )
        legacy = to_decision_profile(good)

        self.assertEqual(
            canonicalize_decision_profile(legacy),
            legacy,
        )

        with self.assertRaises(ValueError):
            canonicalize_user_profile(
                profile(country="B" * 129)
            )

    def test_goal_and_autonomy_are_trimmed_before_validation(self):
        result = canonicalize_user_profile(
            profile(
                goal="  both  ",
                ai_autonomy="  maximum  ",
            )
        )

        self.assertEqual(result["goal"], "both")
        self.assertEqual(
            result["ai_autonomy"],
            "maximum",
        )

    def test_optional_synthesis_assumptions_and_hint_may_be_empty(self):
        observation = SynthesisObservation(
            observation_id="obs-empty-optionals",
            observed_condition="A verified technical condition exists.",
            economic_mechanism="Payment can occur for useful output.",
            value_source="A documented external value source.",
            why_ai_changes_feasibility="Automation reduces execution cost.",
            assumptions=(),
            cheap_test="Run a bounded feasibility test.",
            evidence_required=(
                "Primary-source evidence",
            ),
            source_ids=(
                "source-1",
            ),
            mechanism_hint="",
        )

        result = build_synthesized_candidate(
            observation,
            candidate_id="synth-empty-optionals",
            title="Evidence-backed synthesis hypothesis",
        )

        self.assertEqual(
            result.source_ids,
            ("source-1",),
        )
        self.assertTrue(result.mechanism.strip())

        # Missing mechanism knowledge must be represented neutrally,
        # not fabricated as a specific economic mechanism.
        self.assertEqual(
            result.mechanism,
            "unspecified",
        )


if __name__ == "__main__":
    unittest.main()
