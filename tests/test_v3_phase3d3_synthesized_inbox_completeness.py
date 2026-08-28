from __future__ import annotations

import unittest

from opportunity_operator.enrichment_evidence import (
    apply_enrichment_evidence,
    validate_enrichment_evidence,
)
from opportunity_operator.personalized_ranking import score_candidate
from opportunity_operator.product_integration import build_product_view

from tests.test_v3_phase3d2_enrichment_runtime import (
    PROFILE,
    candidate,
    strong_measurements,
)


def complete_measurements(confidence: int = 90):
    return {
        "candidate_id": "synth-runtime",
        "measurements": [
            {
                "field": "applicant_feasibility",
                "value": "ELIGIBLE",
                "method": "PRIMARY_SOURCE",
                "confidence": confidence,
                "evidence_ids": ["source-a"],
            },
            {
                "field": "capital_required",
                "value": "0",
                "method": "BOUNDED_TEST",
                "confidence": confidence,
                "evidence_ids": ["test-a"],
            },
            {
                "field": "estimated_human_hours",
                "value": "1",
                "method": "BOUNDED_TEST",
                "confidence": confidence,
                "evidence_ids": ["test-a"],
            },
            {
                "field": "ai_executability",
                "value": 90,
                "method": "BOUNDED_TEST",
                "confidence": confidence,
                "evidence_ids": ["test-a"],
            },
            {
                "field": "human_burden",
                "value": 10,
                "method": "BOUNDED_TEST",
                "confidence": confidence,
                "evidence_ids": ["test-a"],
            },
            {
                "field": "customer_dependency",
                "value": 0,
                "method": "BOUNDED_TEST",
                "confidence": confidence,
                "evidence_ids": ["test-a"],
            },
            {
                "field": "sales_dependency",
                "value": 0,
                "method": "BOUNDED_TEST",
                "confidence": confidence,
                "evidence_ids": ["test-a"],
            },
            {
                "field": "external_decision_dependency",
                "value": 0,
                "method": "BOUNDED_TEST",
                "confidence": confidence,
                "evidence_ids": ["test-a"],
            },
            {
                "field": "time_to_evidence_days",
                "value": 5,
                "method": "BOUNDED_TEST",
                "confidence": confidence,
                "evidence_ids": ["test-a"],
            },
            {
                "field": "estimated_upside",
                "value": "100",
                "method": "BOUNDED_TEST",
                "confidence": confidence,
                "evidence_ids": ["test-a"],
            },
            {
                "field": "max_loss",
                "value": "0",
                "method": "BOUNDED_TEST",
                "confidence": confidence,
                "evidence_ids": ["test-a"],
            },
        ],
    }


def enrich(payload):
    original = candidate()

    measurements = validate_enrichment_evidence(
        payload,
        candidate_id=original.candidate_id,
        allowed_evidence_ids=original.source_ids,
    )

    return apply_enrichment_evidence(
        original,
        measurements,
    )


class SynthesizedInboxCompletenessTests(unittest.TestCase):

    def test_high_score_partial_candidate_cannot_enter_inbox(self):
        current = enrich(
            strong_measurements()
        )

        ranking = score_candidate(
            PROFILE,
            current,
        )

        self.assertEqual(
            ranking.fit_band,
            "HIGH",
        )

        view = build_product_view(
            PROFILE,
            {"items": []},
            (current,),
        )

        self.assertEqual(
            view["decision_inbox"],
            [],
        )

    def test_complete_high_confidence_candidate_can_enter_inbox(self):
        current = enrich(
            complete_measurements(90)
        )

        self.assertGreaterEqual(
            current.evidence_quality,
            70,
        )

        ranking = score_candidate(
            PROFILE,
            current,
        )

        self.assertIn(
            ranking.fit_band,
            {"MEDIUM", "HIGH"},
        )

        view = build_product_view(
            PROFILE,
            {"items": []},
            (current,),
        )

        self.assertEqual(
            [
                item["candidate_id"]
                for item in view["decision_inbox"]
            ],
            ["synth-runtime"],
        )

    def test_complete_low_confidence_candidate_does_not_enter_inbox(self):
        current = enrich(
            complete_measurements(10)
        )

        self.assertLess(
            current.evidence_quality,
            70,
        )

        ranking = score_candidate(
            PROFILE,
            current,
        )

        self.assertIn(
            ranking.fit_band,
            {"MEDIUM", "HIGH"},
        )

        view = build_product_view(
            PROFILE,
            {"items": []},
            (current,),
        )

        self.assertEqual(
            view["decision_inbox"],
            [],
        )

    def test_one_missing_critical_field_blocks_inbox(self):
        payload = complete_measurements(90)

        payload["measurements"] = [
            item
            for item in payload["measurements"]
            if item["field"] != "max_loss"
        ]

        current = enrich(payload)

        self.assertIsNone(
            current.max_loss,
        )

        view = build_product_view(
            PROFILE,
            {"items": []},
            (current,),
        )

        self.assertEqual(
            view["decision_inbox"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
