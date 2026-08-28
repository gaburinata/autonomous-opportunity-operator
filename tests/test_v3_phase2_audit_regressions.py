from __future__ import annotations

from decimal import Decimal
import importlib.util
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from opportunity_operator.opportunity_candidate import (
    CandidateOrigin,
    OpportunityCandidate,
)
from opportunity_operator.personalized_ranking import (
    score_candidate,
)
from opportunity_operator.product_integration import (
    adapt_explicit_feed_item,
    build_product_view,
)


ROOT = Path(__file__).resolve().parents[1]


def profile():
    return {
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


def candidate(
    candidate_id,
    *,
    eligibility="ELIGIBLE",
    capital_required=None,
    ai_executability=90,
    human_burden=10,
    evidence_quality=80,
):
    return OpportunityCandidate(
        candidate_id=candidate_id,
        title="Candidate " + candidate_id,
        origin=CandidateOrigin.SYNTHESIZED,
        mechanism="test",
        hypothesis="Evidence-backed bounded hypothesis.",
        economic_mechanism="Usage payment",
        value_source="Documented payer",
        source_ids=("source-1",),
        canonical_source_url=None,
        applicant_feasibility=eligibility,
        capital_required=capital_required,
        estimated_human_hours=Decimal("1"),
        ai_executability=ai_executability,
        human_burden=human_burden,
        customer_dependency=0,
        sales_dependency=0,
        external_decision_dependency=0,
        time_to_evidence_days=3,
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


def explicit_feed():
    return {
        "status": "PASS",
        "raw_candidate_count": 3,
        "shortlist_count": 3,
        "items": [
            {
                "opportunity_id": "bad-first",
                "title": "Rejected first item",
                "organizer": "Example",
                "decision": "KILL",
                "eligibility": "INELIGIBLE",
                "canonical_source_url":
                    "https://example.org/bad",
                "external_deadline": None,
                "estimated_effort_hours": 1,
                "economic_mechanism": "Grant",
                "asset_fit": "",
                "confidence": 0.9,
                "reason_codes": ["INELIGIBLE"],
                "discovered_via": "Official source",
            },
            {
                "opportunity_id": "good-second",
                "title": "Good second item",
                "organizer": "Example",
                "decision": "WATCH",
                "eligibility": "ELIGIBLE",
                "canonical_source_url":
                    "https://example.org/good",
                "external_deadline": None,
                "estimated_effort_hours": 1,
                "economic_mechanism": "Grant",
                "asset_fit": "",
                "confidence": 0.9,
                "reason_codes": [],
                "discovered_via": "Official source",
            },
            {
                "opportunity_id": "unknown-capital",
                "title": "Unknown capital item",
                "organizer": "Example",
                "decision": "WATCH",
                "eligibility": "UNKNOWN",
                "canonical_source_url":
                    "https://example.org/unknown",
                "external_deadline": None,
                "estimated_effort_hours": 2,
                "economic_mechanism": "Grant",
                "asset_fit": "",
                "confidence": 0.5,
                "reason_codes": [],
                "discovered_via": "Official source",
            },
        ],
    }


def load_main():
    spec = importlib.util.spec_from_file_location(
        "aoo_phase2_repair_main",
        ROOT / "main.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UnknownCapitalTests(unittest.TestCase):

    def test_candidate_allows_unknown_capital(self):
        value = candidate(
            "unknown",
            capital_required=None,
        )

        self.assertIsNone(
            value.capital_required
        )

    def test_unknown_capital_is_not_treated_as_zero(self):
        value = candidate(
            "unknown",
            capital_required=None,
        )

        result = score_candidate(
            profile(),
            value,
        )

        self.assertFalse(
            result.hard_reject
        )

        self.assertIn(
            "CAPITAL_REQUIRED_UNKNOWN",
            result.reason_codes,
        )

    def test_known_overbudget_remains_hard_reject(self):
        value = candidate(
            "expensive",
            capital_required=Decimal("1"),
        )

        result = score_candidate(
            profile(),
            value,
        )

        self.assertTrue(
            result.hard_reject
        )

        self.assertIn(
            "CAPITAL_EXCEEDS_MAX_SPEND",
            result.reason_codes,
        )

    def test_missing_feed_capital_stays_none(self):
        item = explicit_feed()["items"][2]

        value = adapt_explicit_feed_item(
            item
        )

        self.assertIsNone(
            value.capital_required
        )

    def test_human_view_marks_unknown_capital(self):
        view = build_product_view(
            profile(),
            explicit_feed(),
        )

        items = (
            view["open_opportunities"]
            + view["challenges_competitions"]
        )

        target = next(
            x for x in items
            if x["candidate_id"] == "unknown-capital"
        )

        self.assertIsNone(
            target["capital_required"]
        )

        self.assertIn(
            "capital_required",
            target["unknowns"],
        )


class DecisionInboxTests(unittest.TestCase):

    def test_ineligible_first_source_item_never_enters_inbox(self):
        view = build_product_view(
            profile(),
            explicit_feed(),
        )

        ids = [
            item["candidate_id"]
            for item in view["decision_inbox"]
        ]

        self.assertNotIn(
            "bad-first",
            ids,
        )

        self.assertIn(
            "good-second",
            ids,
        )

    def test_decision_inbox_is_not_source_order_slice(self):
        view = build_product_view(
            profile(),
            explicit_feed(),
        )

        ids = [
            item["candidate_id"]
            for item in view["decision_inbox"]
        ]

        self.assertNotEqual(
            ids[:1],
            ["bad-first"],
        )

    def test_inbox_is_deterministic_and_bounded(self):
        first = build_product_view(
            profile(),
            explicit_feed(),
        )
        second = build_product_view(
            profile(),
            explicit_feed(),
        )

        self.assertEqual(
            first["decision_inbox"],
            second["decision_inbox"],
        )

        self.assertLessEqual(
            len(first["decision_inbox"]),
            3,
        )


class FunctionalProfileHomeTests(unittest.TestCase):

    def client(self):
        main = load_main()
        main.load_opportunity_feed = explicit_feed

        def forbidden():
            raise AssertionError(
                "profile personalization must not construct model runtime"
            )

        return TestClient(
            main.create_app(
                store_factory=forbidden,
                executor_factory=forbidden,
            )
        )

    def test_home_has_actual_profile_form(self):
        page = self.client().get("/").text

        self.assertIn(
            'id="profileForm"',
            page,
        )

        self.assertIn(
            'addEventListener("submit"',
            page,
        )

    def test_profile_submit_calls_personalized_endpoint(self):
        page = self.client().get("/").text

        self.assertIn(
            'fetch("/opportunities/personalized"',
            page,
        )

        self.assertIn(
            "preventDefault()",
            page,
        )

    def test_personalized_response_re_renders_product_lanes(self):
        page = self.client().get("/").text

        self.assertIn(
            "renderProductView",
            page,
        )

        for token in (
            "decision_inbox",
            "build_operate",
            "open_opportunities",
            "challenges_competitions",
        ):
            self.assertIn(
                token,
                page,
            )

    def test_no_clock_identity_or_auto_investigation(self):
        page = self.client().get("/").text

        self.assertNotIn(
            "Date.now()",
            page,
        )

        self.assertNotIn(
            "autoInvestigate",
            page,
        )

        self.assertIn(
            "Investigate with 7-agent team",
            page,
        )


if __name__ == "__main__":
    unittest.main()
