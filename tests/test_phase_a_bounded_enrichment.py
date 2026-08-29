from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import unittest

from opportunity_operator.opportunity_candidate import (
    CandidateOrigin,
    OpportunityCandidate,
)
from opportunity_operator.phase_a_bounded_enrichment import (
    PHASE_A_ALLOWED_ENRICHMENT_FIELDS,
    PHASE_A_TEST_KIND,
    apply_phase_a_bounded_test_evidence,
    build_phase_a_test_plan,
)


PROFILE = {
    "goal":
        "both",

    "country":
        "Bulgaria",

    "available_capital":
        "150",

    "max_cash_spend":
        "25",

    "human_hours_per_week":
        "5",

    "ai_autonomy":
        "maximum",

    "willingness":
        {
            "build_business":
                True,

            "work_with_customers":
                True,

            "sell":
                True,

            "publish_content":
                True,

            "contests_juries":
                True,

            "financial_protocols":
                True,

            "invest_capital":
                True,
        },

    "constraints":
        [],

    "skills_assets":
        [],
}


def candidate() -> OpportunityCandidate:

    return OpportunityCandidate(
        candidate_id=
            "synth-phase-a",

        title=
            "Real-Time Coinbase-Kraken Spread Monitoring and Alerting Service",

        origin=
            CandidateOrigin.SYNTHESIZED,

        mechanism=
            "data product, dataset, monitoring product or intelligence service",

        hypothesis=
            "Evidence-backed monitoring-product hypothesis",

        economic_mechanism=
            "Subscription monitoring product",

        value_source=
            "Potential users of spread monitoring",

        source_ids=
            (
                "coinbase-btcusd-live",
                "kraken-xbtusd-live",
            ),

        canonical_source_url=
            None,

        applicant_feasibility=
            "UNKNOWN",

        capital_required=
            None,

        estimated_human_hours=
            None,

        ai_executability=
            None,

        human_burden=
            None,

        customer_dependency=
            None,

        sales_dependency=
            None,

        external_decision_dependency=
            None,

        time_to_evidence_days=
            None,

        estimated_upside=
            None,

        max_loss=
            None,

        evidence_quality=
            0,

        requires_business_build=
            True,

        requires_customer_work=
            False,

        requires_sales=
            True,

        requires_content=
            False,

        is_contest_or_jury=
            False,

        is_financial_protocol=
            False,
    )


def bounded_test_record(
    *,
    field: str = "ai_executability",
    value: object = 95,
    method: str = "BOUNDED_TEST",
):

    return {
        "candidate_id":
            "synth-phase-a",

        "evidence_id":
            "phase-a-test-001",

        "test_kind":
            PHASE_A_TEST_KIND,

        "measurements":
            [
                {
                    "field":
                        field,

                    "value":
                        value,

                    "method":
                        method,

                    "confidence":
                        95,

                    "evidence_ids":
                        [
                            "phase-a-test-001",
                        ],
                },
            ],
    }


class PhaseAPlanTests(
    unittest.TestCase
):

    def test_plan_is_zero_consequence_and_deterministic(self):

        first = build_phase_a_test_plan(
            candidate()
        )

        second = build_phase_a_test_plan(
            candidate()
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            first[
                "planned_samples"
            ],
            60,
        )

        self.assertEqual(
            first[
                "constraints"
            ],
            {
                "capital_at_risk":
                    0,

                "trades":
                    0,

                "orders":
                    0,

                "public_posting":
                    0,

                "customer_contact":
                    0,

                "model_calls":
                    0,
            },
        )

        self.assertFalse(
            first[
                "evidence_contract"
            ][
                "may_promote"
            ]
        )

        self.assertFalse(
            first[
                "evidence_contract"
            ][
                "may_prove_revenue"
            ]
        )

    def test_plan_allows_only_technical_ai_executability(self):

        plan = build_phase_a_test_plan(
            candidate()
        )

        self.assertEqual(
            PHASE_A_ALLOWED_ENRICHMENT_FIELDS,
            frozenset(
                {
                    "ai_executability",
                }
            ),
        )

        self.assertEqual(
            plan[
                "evidence_contract"
            ][
                "allowed_enrichment_fields"
            ],
            [
                "ai_executability",
            ],
        )

    def test_wrong_candidate_is_rejected(self):

        wrong = replace(
            candidate(),
            source_ids=(
                "coinbase-btcusd-live",
            ),
        )

        with self.assertRaises(
            ValueError
        ):
            build_phase_a_test_plan(
                wrong
            )

    def test_explicit_candidate_is_rejected(self):

        explicit = replace(
            candidate(),
            origin=
                CandidateOrigin.EXPLICIT,
        )

        with self.assertRaises(
            ValueError
        ):
            build_phase_a_test_plan(
                explicit
            )


class PhaseAEnrichmentTests(
    unittest.TestCase
):

    def test_bounded_technical_measurement_fills_only_ai_executability(self):

        original = candidate()

        result = (
            apply_phase_a_bounded_test_evidence(
                PROFILE,
                original,
                bounded_test_record(),
            )
        )

        enriched = result[
            "candidate_after"
        ]

        self.assertEqual(
            enriched.ai_executability,
            95,
        )

        self.assertEqual(
            enriched.applicant_feasibility,
            "UNKNOWN",
        )

        self.assertIsNone(
            enriched.capital_required
        )

        self.assertIsNone(
            enriched.estimated_human_hours
        )

        self.assertIsNone(
            enriched.customer_dependency
        )

        self.assertIsNone(
            enriched.sales_dependency
        )

        self.assertIsNone(
            enriched.estimated_upside
        )

        self.assertIsNone(
            enriched.max_loss
        )

        self.assertEqual(
            original.ai_executability,
            None,
        )

    def test_single_phase_a_measurement_cannot_reach_strong_evidence(self):

        result = (
            apply_phase_a_bounded_test_evidence(
                PROFILE,
                candidate(),
                bounded_test_record(),
            )
        )

        # 95 confidence over eleven enrichment fields:
        # round(95 / 11) == 9.
        self.assertEqual(
            result[
                "evidence_quality_after"
            ],
            9,
        )

        self.assertLess(
            result[
                "evidence_quality_after"
            ],
            70,
        )

        self.assertFalse(
            result[
                "decision_inbox_eligible"
            ]
        )

    def test_phase_a_never_claims_economic_promotion(self):

        result = (
            apply_phase_a_bounded_test_evidence(
                PROFILE,
                candidate(),
                bounded_test_record(),
            )
        )

        economics = result[
            "economic_evidence"
        ]

        self.assertFalse(
            economics[
                "unit_economics_present"
            ]
        )

        self.assertFalse(
            economics[
                "promotion_allowed"
            ]
        )

        self.assertEqual(
            economics[
                "reason_codes"
            ],
            [
                "INSUFFICIENT_ECONOMIC_EVIDENCE",
            ],
        )

    def test_customer_demand_cannot_be_smuggled_through_phase_a(self):

        with self.assertRaises(
            ValueError
        ):
            apply_phase_a_bounded_test_evidence(
                PROFILE,
                candidate(),
                bounded_test_record(
                    field=
                        "customer_dependency",

                    value=
                        20,
                ),
            )

    def test_revenue_or_upside_cannot_be_smuggled_through_phase_a(self):

        with self.assertRaises(
            ValueError
        ):
            apply_phase_a_bounded_test_evidence(
                PROFILE,
                candidate(),
                bounded_test_record(
                    field=
                        "estimated_upside",

                    value=
                        "1000",
                ),
            )

    def test_non_bounded_method_is_rejected(self):

        with self.assertRaises(
            ValueError
        ):
            apply_phase_a_bounded_test_evidence(
                PROFILE,
                candidate(),
                bounded_test_record(
                    method=
                        "MODEL_ASSESSMENT",
                ),
            )

    def test_wrong_evidence_identity_is_rejected(self):

        record = bounded_test_record()

        record[
            "measurements"
        ][0][
            "evidence_ids"
        ] = [
            "some-other-evidence",
        ]

        with self.assertRaises(
            ValueError
        ):
            apply_phase_a_bounded_test_evidence(
                PROFILE,
                candidate(),
                record,
            )

    def test_existing_evidence_id_cannot_pose_as_new_bounded_test(self):

        record = bounded_test_record()

        record[
            "evidence_id"
        ] = (
            "coinbase-btcusd-live"
        )

        record[
            "measurements"
        ][0][
            "evidence_ids"
        ] = [
            "coinbase-btcusd-live",
        ]

        with self.assertRaises(
            ValueError
        ):
            apply_phase_a_bounded_test_evidence(
                PROFILE,
                candidate(),
                record,
            )


if __name__ == "__main__":
    unittest.main()
