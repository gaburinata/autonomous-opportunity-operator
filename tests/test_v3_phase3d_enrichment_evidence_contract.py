from __future__ import annotations

from decimal import Decimal
import unittest

from opportunity_operator.enrichment_evidence import (
    EnrichmentMeasurement,
    apply_enrichment_evidence,
    evidence_quality_from_measurements,
    validate_enrichment_evidence,
)
from opportunity_operator.opportunity_candidate import (
    CandidateOrigin,
    OpportunityCandidate,
)


def candidate() -> OpportunityCandidate:
    return OpportunityCandidate(
        candidate_id="synth-test",
        title="Synthesized test",
        origin=CandidateOrigin.SYNTHESIZED,
        mechanism="Machine mechanism",
        hypothesis="Evidence-backed hypothesis",
        economic_mechanism="Economic mechanism",
        value_source="Value source",
        source_ids=("source-a", "source-b"),
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


def payload():
    return {
        "candidate_id": "synth-test",
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
                "method": "DETERMINISTIC_TOOL",
                "confidence": 100,
                "evidence_ids": ["source-a"],
            },
            {
                "field": "ai_executability",
                "value": 90,
                "method": "BOUNDED_TEST",
                "confidence": 90,
                "evidence_ids": ["source-b"],
            },
        ],
    }


class Phase3DEnrichmentEvidenceTests(unittest.TestCase):

    def test_valid_evidence_normalizes_types(self):
        result = validate_enrichment_evidence(
            payload(),
            candidate_id="synth-test",
            allowed_evidence_ids=(
                "source-a",
                "source-b",
            ),
        )

        self.assertEqual(
            len(result),
            3,
        )

        self.assertEqual(
            result[1].value,
            Decimal("0"),
        )

        self.assertEqual(
            result[2].value,
            90,
        )

    def test_model_narrative_cannot_become_authoritative_measurement(self):
        value = payload()

        value["measurements"][2]["method"] = (
            "MODEL_ASSESSMENT"
        )

        with self.assertRaises(ValueError):
            validate_enrichment_evidence(
                value,
                candidate_id="synth-test",
                allowed_evidence_ids=(
                    "source-a",
                    "source-b",
                ),
            )

    def test_unknown_provenance_fails_closed(self):
        value = payload()

        value["measurements"][0]["evidence_ids"] = [
            "invented-source"
        ]

        with self.assertRaises(ValueError):
            validate_enrichment_evidence(
                value,
                candidate_id="synth-test",
                allowed_evidence_ids=(
                    "source-a",
                    "source-b",
                ),
            )

    def test_duplicate_field_fails_closed(self):
        value = payload()

        value["measurements"].append(
            dict(value["measurements"][0])
        )

        with self.assertRaises(ValueError):
            validate_enrichment_evidence(
                value,
                candidate_id="synth-test",
                allowed_evidence_ids=(
                    "source-a",
                    "source-b",
                ),
            )

    def test_apply_fills_unknowns_without_mutating_original(self):
        original = candidate()

        measurements = validate_enrichment_evidence(
            payload(),
            candidate_id=original.candidate_id,
            allowed_evidence_ids=original.source_ids,
        )

        enriched = apply_enrichment_evidence(
            original,
            measurements,
        )

        self.assertEqual(
            original.applicant_feasibility,
            "UNKNOWN",
        )

        self.assertIsNone(
            original.capital_required,
        )

        self.assertIsNone(
            original.ai_executability,
        )

        self.assertEqual(
            enriched.applicant_feasibility,
            "ELIGIBLE",
        )

        self.assertEqual(
            enriched.capital_required,
            Decimal("0"),
        )

        self.assertEqual(
            enriched.ai_executability,
            90,
        )

        self.assertGreater(
            enriched.evidence_quality,
            0,
        )

    def test_conflicting_known_fact_cannot_be_overwritten(self):
        original = candidate()

        first = validate_enrichment_evidence(
            payload(),
            candidate_id=original.candidate_id,
            allowed_evidence_ids=original.source_ids,
        )

        enriched = apply_enrichment_evidence(
            original,
            first,
        )

        conflicting_payload = {
            "candidate_id": "synth-test",
            "measurements": [
                {
                    "field": "capital_required",
                    "value": "50",
                    "method": "PRIMARY_SOURCE",
                    "confidence": 100,
                    "evidence_ids": ["source-a"],
                }
            ],
        }

        conflicting = validate_enrichment_evidence(
            conflicting_payload,
            candidate_id=enriched.candidate_id,
            allowed_evidence_ids=enriched.source_ids,
        )

        with self.assertRaises(ValueError):
            apply_enrichment_evidence(
                enriched,
                conflicting,
            )

    def test_evidence_quality_is_coverage_weighted(self):
        one = (
            EnrichmentMeasurement(
                field="ai_executability",
                value=100,
                method="BOUNDED_TEST",
                confidence=100,
                evidence_ids=("source-a",),
            ),
        )

        quality = evidence_quality_from_measurements(
            one
        )

        self.assertGreater(
            quality,
            0,
        )

        self.assertLess(
            quality,
            20,
        )


if __name__ == "__main__":
    unittest.main()
