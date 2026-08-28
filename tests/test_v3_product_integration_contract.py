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
        "skills_assets": [
            "Python",
            "automation",
        ],
        "constraints": [
            "No leverage",
        ],
    }


def feed():
    return {
        "status": "PASS",
        "raw_candidate_count": 2,
        "shortlist_count": 2,
        "items": [
            {
                "opportunity_id": "challenge-1",
                "title": "Agent Challenge",
                "organizer": "Devpost",
                "decision": "WATCH",
                "eligibility": "UNKNOWN",
                "canonical_source_url":
                    "https://example.devpost.com/",
                "external_deadline":
                    "2026-08-31T23:59:00Z",
                "estimated_effort_hours": 5,
                "economic_mechanism": "Prize",
                "asset_fit": "Automation stack",
                "confidence": 0.8,
                "reason_codes": [],
                "discovered_via": "Devpost official API",
            },
            {
                "opportunity_id": "grant-1",
                "title": "Open Technology Fund",
                "organizer": "Example Foundation",
                "decision": "WATCH",
                "eligibility": "UNKNOWN",
                "canonical_source_url":
                    "https://example.org/fund",
                "external_deadline":
                    "2026-09-30T23:59:00Z",
                "estimated_effort_hours": 3,
                "economic_mechanism": "Grant",
                "asset_fit": "Software",
                "confidence": 0.7,
                "reason_codes": [],
                "discovered_via": "Official source",
            },
        ],
    }


def synthesized():
    return OpportunityCandidate(
        candidate_id="synth-1",
        title="Automated data mechanism",
        origin=CandidateOrigin.SYNTHESIZED,
        mechanism="data_product",
        hypothesis="Observed condition supports a bounded economic test.",
        economic_mechanism="Usage payment",
        value_source="Documented buyer demand",
        source_ids=("source-1",),
        canonical_source_url=None,
        applicant_feasibility="UNKNOWN",
        capital_required=Decimal("0"),
        estimated_human_hours=Decimal("2"),
        ai_executability=95,
        human_burden=5,
        customer_dependency=0,
        sales_dependency=0,
        external_decision_dependency=0,
        time_to_evidence_days=3,
        estimated_upside=None,
        max_loss=None,
        evidence_quality=80,
        requires_business_build=True,
        requires_customer_work=False,
        requires_sales=False,
        requires_content=False,
        is_contest_or_jury=False,
        is_financial_protocol=False,
    )


def load_main():
    spec = importlib.util.spec_from_file_location(
        "aoo_v3_phase2_main",
        ROOT / "main.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProductIntegrationTests(unittest.TestCase):

    def test_devpost_explicit_candidate_is_challenge(self):
        candidate = adapt_explicit_feed_item(
            feed()["items"][0]
        )

        self.assertEqual(
            candidate.origin,
            CandidateOrigin.EXPLICIT,
        )
        self.assertTrue(
            candidate.is_contest_or_jury
        )

    def test_noncontest_grant_is_not_challenge(self):
        candidate = adapt_explicit_feed_item(
            feed()["items"][1]
        )

        self.assertFalse(
            candidate.is_contest_or_jury
        )

    def test_product_view_has_four_distinct_surfaces(self):
        view = build_product_view(
            profile(),
            feed(),
            (synthesized(),),
        )

        self.assertEqual(
            set(
                (
                    "decision_inbox",
                    "build_operate",
                    "open_opportunities",
                    "challenges_competitions",
                )
            ).issubset(view),
            True,
        )

        self.assertEqual(
            [x["candidate_id"]
             for x in view["build_operate"]],
            ["synth-1"],
        )

        self.assertEqual(
            [x["candidate_id"]
             for x in view["challenges_competitions"]],
            ["challenge-1"],
        )

        self.assertEqual(
            [x["candidate_id"]
             for x in view["open_opportunities"]],
            ["grant-1"],
        )

    def test_challenge_never_appears_in_open_opportunities(self):
        view = build_product_view(
            profile(),
            feed(),
        )

        open_ids = {
            x["candidate_id"]
            for x in view["open_opportunities"]
        }

        challenge_ids = {
            x["candidate_id"]
            for x in view["challenges_competitions"]
        }

        self.assertNotIn(
            "challenge-1",
            open_ids,
        )
        self.assertIn(
            "challenge-1",
            challenge_ids,
        )

    def test_decision_inbox_is_bounded_and_deterministic(self):
        first = build_product_view(
            profile(),
            feed(),
            (synthesized(),),
        )
        second = build_product_view(
            profile(),
            feed(),
            (synthesized(),),
        )

        self.assertEqual(
            first["decision_inbox"],
            second["decision_inbox"],
        )

        self.assertLessEqual(
            len(first["decision_inbox"]),
            3,
        )

        # The fixture's synthesized candidate is numerically attractive
        # but still lacks decision-critical evidence. A bounded,
        # deterministic Inbox is allowed to be empty.
        self.assertEqual(
            first["decision_inbox"],
            [],
        )

    def test_human_view_does_not_expose_raw_score(self):
        view = build_product_view(
            profile(),
            feed(),
            (synthesized(),),
        )

        for lane in (
            "decision_inbox",
            "build_operate",
            "open_opportunities",
            "challenges_competitions",
        ):
            for item in view[lane]:
                self.assertNotIn(
                    "score",
                    item,
                )

    def test_unknown_fields_are_explicit_not_invented(self):
        view = build_product_view(
            profile(),
            feed(),
        )

        challenge = view[
            "challenges_competitions"
        ][0]

        self.assertEqual(
            challenge["applicant_feasibility"],
            "UNKNOWN",
        )

        self.assertIn(
            "unknowns",
            challenge,
        )


class ProductHomePhase2Tests(unittest.TestCase):

    def client(self):
        main = load_main()
        main.load_opportunity_feed = feed

        def forbidden():
            raise AssertionError(
                "model workflow must not be constructed"
            )

        return TestClient(
            main.create_app(
                store_factory=forbidden,
                executor_factory=forbidden,
            )
        )

    def test_homepage_is_profile_first(self):
        page = self.client().get("/").text

        self.assertIn(
            "build, operate, or pursue for you",
            page,
        )
        self.assertIn(
            "Find what AI can do for me",
            page,
        )
        self.assertIn(
            "Your profile is the primary query.",
            page,
        )

        self.assertIn(
            "Available capital",
            page,
        )
        self.assertIn(
            "Max human hours",
            page,
        )

    def test_homepage_has_distinct_product_sections(self):
        page = self.client().get("/").text

        self.assertIn("Decision Inbox", page)
        self.assertIn("Build &amp; Operate", page)
        self.assertIn("Open Opportunities", page)
        self.assertIn(
            "Challenges &amp; Competitions",
            page,
        )

    def test_advanced_search_is_secondary(self):
        page = self.client().get("/").text

        self.assertIn(
            "Advanced search",
            page,
        )
        self.assertIn(
            "Find new opportunities",
            page,
        )

    def test_no_automatic_deep_investigation(self):
        page = self.client().get("/").text

        self.assertIn(
            "Investigate with 7-agent team",
            page,
        )

        self.assertIn(
            'addEventListener("click"',
            page,
        )

        self.assertNotIn(
            "autoInvestigate",
            page,
        )

    def test_investigation_identity_is_not_clock_based(self):
        page = self.client().get("/").text

        self.assertNotIn(
            "Date.now()",
            page,
        )

    def test_judge_console_remains_separate(self):
        page = self.client().get(
            "/judge-console"
        ).text

        self.assertIn(
            "Workflow trace",
            page,
        )


class PersonalizedEndpointTests(unittest.TestCase):

    def test_personalized_endpoint_is_model_free(self):
        main = load_main()
        main.load_opportunity_feed = feed

        def forbidden():
            raise AssertionError(
                "personalization must be model-free"
            )

        client = TestClient(
            main.create_app(
                store_factory=forbidden,
                executor_factory=forbidden,
            )
        )

        response = client.post(
            "/opportunities/personalized",
            json=profile(),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertIn(
            "decision_inbox",
            data,
        )
        self.assertIn(
            "challenges_competitions",
            data,
        )

    def test_invalid_profile_fails_safely(self):
        main = load_main()
        main.load_opportunity_feed = feed

        client = TestClient(
            main.create_app()
        )

        response = client.post(
            "/opportunities/personalized",
            json={"goal": "money please"},
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["status"],
            "INVALID",
        )

        self.assertIn(
            "INVALID_USER_PROFILE",
            response.json()["reason_codes"],
        )


if __name__ == "__main__":
    unittest.main()
