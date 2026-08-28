from __future__ import annotations

import unittest

from opportunity_operator.enrichment_runtime import (
    enrich_and_rerank_candidate,
)
from opportunity_operator.opportunity_candidate import (
    CandidateOrigin,
    OpportunityCandidate,
)


PROFILE = {
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
        "contests_juries": False,
        "financial_protocols": True,
    },
    "skills_assets": [
        "AI-assisted development",
        "automation",
    ],
    "constraints": [
        "No leverage",
        "Minimize recurring human work",
    ],
}


def candidate() -> OpportunityCandidate:
    return OpportunityCandidate(
        candidate_id="synth-runtime",
        title="Runtime candidate",
        origin=CandidateOrigin.SYNTHESIZED,
        mechanism="Machine mechanism",
        hypothesis="Evidence-backed hypothesis",
        economic_mechanism="Economic mechanism",
        value_source="Value source",
        source_ids=("source-a", "test-a"),
        canonical_source_url=None,
        applicant_feasibility="UNKNOWN",
        capital_required=None,
        estimated_human_hours=None,
        ai_executability=None,
        human_burden=None,
        customer_dependency=None,
        sales_dependency=None,
        external_decision_dependency=None,
        time_to_evidence_days=None,
        estimated_upside=None,
        max_loss=None,
        evidence_quality=0,
        requires_business_build=False,
        requires_customer_work=False,
        requires_sales=False,
        requires_content=False,
        is_contest_or_jury=False,
        is_financial_protocol=False,
    )


def strong_measurements():
    return {
        "candidate_id": "synth-runtime",
        "measurements": [
            {
                "field": "applicant_feasibility",
                "value": "ELIGIBLE",
                "method": "PRIMARY_SOURCE",
                "confidence": 100,
                "evidence_ids": ["source-a"],
            },
            {
                "field": "capital_required",
                "value": "0",
                "method": "BOUNDED_TEST",
                "confidence": 100,
                "evidence_ids": ["test-a"],
            },
            {
                "field": "ai_executability",
                "value": 90,
                "method": "BOUNDED_TEST",
                "confidence": 90,
                "evidence_ids": ["test-a"],
            },
            {
                "field": "human_burden",
                "value": 10,
                "method": "BOUNDED_TEST",
                "confidence": 90,
                "evidence_ids": ["test-a"],
            },
            {
                "field": "time_to_evidence_days",
                "value": 5,
                "method": "BOUNDED_TEST",
                "confidence": 90,
                "evidence_ids": ["test-a"],
            },
        ],
    }


class EnrichmentRuntimeTests(unittest.TestCase):

    def test_valid_measurements_can_change_fit_without_mutating_original(self):
        original = candidate()

        result = enrich_and_rerank_candidate(
            PROFILE,
            original,
            strong_measurements(),
            allowed_evidence_ids=original.source_ids,
        )

        self.assertEqual(
            result["status"],
            "PASS",
        )

        self.assertEqual(
            result["ranking_before"]["fit_band"],
            "LOW",
        )

        self.assertIn(
            result["ranking_after"]["fit_band"],
            {"MEDIUM", "HIGH"},
        )

        self.assertEqual(
            original.applicant_feasibility,
            "UNKNOWN",
        )

        self.assertIsNone(
            original.ai_executability,
        )

    def test_result_is_json_safe(self):
        result = enrich_and_rerank_candidate(
            PROFILE,
            candidate(),
            strong_measurements(),
            allowed_evidence_ids=(
                "source-a",
                "test-a",
            ),
        )

        self.assertEqual(
            result["candidate_after"]["capital_required"],
            "0",
        )

        self.assertIsInstance(
            result["candidate_after"]["source_ids"],
            list,
        )

    def test_model_assessment_is_rejected_before_ranking_change(self):
        payload = strong_measurements()

        payload["measurements"][2]["method"] = "MODEL_ASSESSMENT"

        with self.assertRaises(ValueError):
            enrich_and_rerank_candidate(
                PROFILE,
                candidate(),
                payload,
                allowed_evidence_ids=(
                    "source-a",
                    "test-a",
                ),
            )

    def test_unknown_evidence_is_rejected(self):
        payload = strong_measurements()

        payload["measurements"][2]["evidence_ids"] = [
            "invented"
        ]

        with self.assertRaises(ValueError):
            enrich_and_rerank_candidate(
                PROFILE,
                candidate(),
                payload,
                allowed_evidence_ids=(
                    "source-a",
                    "test-a",
                ),
            )

    def test_conflicting_known_fact_is_rejected(self):
        first = enrich_and_rerank_candidate(
            PROFILE,
            candidate(),
            strong_measurements(),
            allowed_evidence_ids=(
                "source-a",
                "test-a",
            ),
        )

        self.assertEqual(
            first["candidate_after"]["capital_required"],
            "0",
        )

        original = candidate()

        from opportunity_operator.enrichment_evidence import (
            apply_enrichment_evidence,
            validate_enrichment_evidence,
        )

        measurements = validate_enrichment_evidence(
            strong_measurements(),
            candidate_id=original.candidate_id,
            allowed_evidence_ids=original.source_ids,
        )

        enriched = apply_enrichment_evidence(
            original,
            measurements,
        )

        conflict = {
            "candidate_id": "synth-runtime",
            "measurements": [
                {
                    "field": "capital_required",
                    "value": "50",
                    "method": "BOUNDED_TEST",
                    "confidence": 100,
                    "evidence_ids": ["test-a"],
                }
            ],
        }

        with self.assertRaises(ValueError):
            enrich_and_rerank_candidate(
                PROFILE,
                enriched,
                conflict,
                allowed_evidence_ids=(
                    "source-a",
                    "test-a",
                ),
            )


if __name__ == "__main__":
    unittest.main()
