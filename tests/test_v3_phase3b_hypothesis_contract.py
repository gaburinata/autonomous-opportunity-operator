from __future__ import annotations

import unittest

from opportunity_operator.opportunity_synthesis import (
    SynthesisObservation,
    build_synthesized_candidate,
)


class Phase3BHypothesisContractTests(unittest.TestCase):

    def _observation(self) -> SynthesisObservation:
        return SynthesisObservation(
            observation_id="obs-regression",
            observed_condition="Observed condition " + ("O" * 205),
            economic_mechanism="Economic mechanism " + ("E" * 260),
            value_source="Value source " + ("V" * 125),
            why_ai_changes_feasibility=(
                "AI feasibility " + ("A" * 240)
            ),
            assumptions=(
                "A" * 110,
                "B" * 131,
                "C" * 142,
            ),
            cheap_test="Cheap test " + ("T" * 315),
            evidence_required=(
                "E" * 33,
                "F" * 88,
                "G" * 104,
            ),
            source_ids=(
                "source-one",
                "source-two",
            ),
            mechanism_hint="Mechanism hint " + ("M" * 200),
        )

    def test_long_valid_synthesis_builds_candidate(self) -> None:
        candidate = build_synthesized_candidate(
            self._observation(),
            candidate_id="synth-regression",
            title="Regression candidate",
        )

        self.assertEqual(
            candidate.candidate_id,
            "synth-regression",
        )

        self.assertLessEqual(
            len(candidate.hypothesis),
            1000,
        )

        self.assertTrue(
            candidate.hypothesis.strip(),
        )

    def test_hypothesis_remains_testable_and_structured(self) -> None:
        candidate = build_synthesized_candidate(
            self._observation(),
            candidate_id="synth-regression",
            title="Regression candidate",
        )

        hypothesis = candidate.hypothesis

        self.assertIn(
            "Observed condition:",
            hypothesis,
        )
        self.assertIn(
            "Economic mechanism:",
            hypothesis,
        )
        self.assertIn(
            "Value source:",
            hypothesis,
        )
        self.assertIn(
            "Cheap test:",
            hypothesis,
        )

    def test_build_is_deterministic(self) -> None:
        observation = self._observation()

        first = build_synthesized_candidate(
            observation,
            candidate_id="synth-regression",
            title="Regression candidate",
        )

        second = build_synthesized_candidate(
            observation,
            candidate_id="synth-regression",
            title="Regression candidate",
        )

        self.assertEqual(
            first,
            second,
        )


if __name__ == "__main__":
    unittest.main()
