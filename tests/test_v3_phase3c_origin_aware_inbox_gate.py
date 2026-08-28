from __future__ import annotations

from decimal import Decimal
import unittest

from opportunity_operator.opportunity_candidate import (
    CandidateOrigin,
    OpportunityCandidate,
)
from opportunity_operator.product_integration import build_product_view

from tests.test_v3_phase2_audit_regressions import (
    explicit_feed,
    profile,
)


def synthesized_candidate(
    candidate_id: str,
    *,
    applicant_feasibility: str = "UNKNOWN",
    capital_required: Decimal | None = None,
    ai_executability: int | None = None,
    human_burden: int | None = None,
    evidence_quality: int = 0,
    time_to_evidence_days: int | None = None,
) -> OpportunityCandidate:
    return OpportunityCandidate(
        candidate_id=candidate_id,
        title="Synthesized " + candidate_id,
        origin=CandidateOrigin.SYNTHESIZED,
        mechanism="Machine-executable mechanism",
        hypothesis="Evidence-backed testable hypothesis",
        economic_mechanism="Machine-executable economic mechanism",
        value_source="Defined economic value source",
        source_ids=("source-a",),
        canonical_source_url=None,
        applicant_feasibility=applicant_feasibility,
        capital_required=capital_required,
        estimated_human_hours=None,
        ai_executability=ai_executability,
        human_burden=human_burden,
        customer_dependency=None,
        sales_dependency=None,
        external_decision_dependency=None,
        time_to_evidence_days=time_to_evidence_days,
        estimated_upside=None,
        max_loss=None,
        evidence_quality=evidence_quality,
        requires_business_build=False,
        requires_customer_work=False,
        requires_sales=False,
        requires_content=False,
        is_contest_or_jury=False,
        is_financial_protocol=False,
    )


class OriginAwareDecisionInboxTests(unittest.TestCase):

    def test_legacy_strong_explicit_low_fit_remains_admissible(self):
        view = build_product_view(
            profile(),
            explicit_feed(),
        )

        ids = {
            item["candidate_id"]
            for item in view["decision_inbox"]
        }

        self.assertIn(
            "good-second",
            ids,
        )

    def test_unknown_eligibility_explicit_low_fit_is_not_inbox_worthy(self):
        view = build_product_view(
            profile(),
            explicit_feed(),
        )

        ids = {
            item["candidate_id"]
            for item in view["decision_inbox"]
        }

        self.assertNotIn(
            "unknown-capital",
            ids,
        )

    def test_synthesized_low_fit_remains_lane_only(self):
        candidate = synthesized_candidate(
            "synth-low",
        )

        view = build_product_view(
            profile(),
            {"items": []},
            (candidate,),
        )

        self.assertEqual(
            view["build_operate"][0]["candidate_id"],
            "synth-low",
        )

        self.assertEqual(
            view["build_operate"][0]["fit_band"],
            "LOW",
        )

        self.assertEqual(
            view["decision_inbox"],
            [],
        )

    def test_synthesized_high_fit_without_complete_evidence_stays_out_of_inbox(self):
        candidate = synthesized_candidate(
            "synth-high",
            applicant_feasibility="ELIGIBLE",
            capital_required=Decimal("0"),
            ai_executability=100,
            human_burden=0,
            evidence_quality=100,
            time_to_evidence_days=0,
        )

        view = build_product_view(
            profile(),
            {"items": []},
            (candidate,),
        )

        # Ranking and evidence readiness are intentionally separate.
        # This candidate is numerically HIGH but still lacks several
        # decision-critical measurements.
        self.assertEqual(
            view["build_operate"][0]["fit_band"],
            "HIGH",
        )

        self.assertEqual(
            view["decision_inbox"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
