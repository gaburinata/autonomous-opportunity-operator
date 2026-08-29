import unittest

from opportunity_operator.public_v5_operator import (
    build_public_v5_view,
    canonicalize_v5_profile,
)


def profile(**changes):
    value = {
        "profile_version": "5",
        "goal": "both",
        "residence_country": "Bulgaria",
        "citizenships": ["Bulgaria"],
        "currency": "EUR",
        "available_money": "150",
        "max_cash_spend_or_risk": "25",
        "human_hours_per_week": "5",
        "exclusions": [],
        "skills_assets": [],
    }
    value.update(changes)
    return value


def candidate(
    *,
    title,
    category="opportunity",
    capital=None,
    capital_currency=None,
):
    value = {
        "opportunity_id":
            title.lower().replace(
                " ",
                "-",
            ),
        "title":
            title,
        "category":
            category,
        "canonical_source_url":
            "https://example.com/opportunity",
        "confidence":
            0.8,
        "eligibility":
            "UNKNOWN",
    }

    if capital is not None:
        value[
            "capital_required"
        ] = capital

    if capital_currency is not None:
        value[
            "capital_currency"
        ] = capital_currency

    return value


class PublicV5OperatorTests(
    unittest.TestCase
):

    def test_profile_preserves_residence_citizenship_currency(self):
        result = canonicalize_v5_profile(
            profile(
                residence_country="Philippines",
                citizenships=[
                    "Philippines",
                    "United States",
                ],
                currency="PHP",
            )
        )

        self.assertEqual(
            result[
                "residence_country"
            ],
            "Philippines",
        )

        self.assertEqual(
            result["citizenships"],
            [
                "Philippines",
                "United States",
            ],
        )

        self.assertEqual(
            result["currency"],
            "PHP",
        )

    def test_spend_cannot_exceed_available_money(self):
        with self.assertRaises(
            ValueError
        ):
            canonicalize_v5_profile(
                profile(
                    available_money="10",
                    max_cash_spend_or_risk="11",
                )
            )

    def test_output_is_bounded_to_three(self):
        items = [
            candidate(
                title=f"Opportunity {i}"
            )
            for i in range(8)
        ]

        result = build_public_v5_view(
            profile(),
            items=items,
        )

        self.assertLessEqual(
            len(
                result[
                    "recommendations"
                ]
            ),
            3,
        )

    def test_competition_exclusion_changes_output(self):
        items = [
            candidate(
                title="Build AI Hackathon",
                category="hackathon",
            ),
            candidate(
                title="Open Source Grant",
                category="grant",
            ),
        ]

        baseline = build_public_v5_view(
            profile(),
            items=items,
        )

        excluded = build_public_v5_view(
            profile(
                exclusions=[
                    "competitions"
                ]
            ),
            items=items,
        )

        baseline_titles = {
            item["title"]
            for item in baseline[
                "recommendations"
            ]
        }

        excluded_titles = {
            item["title"]
            for item in excluded[
                "recommendations"
            ]
        }

        self.assertIn(
            "Build AI Hackathon",
            baseline_titles,
        )

        self.assertNotIn(
            "Build AI Hackathon",
            excluded_titles,
        )

    def test_financial_opportunity_is_allowed_unless_excluded(self):
        item = candidate(
            title=(
                "Systematic arbitrage "
                "research opportunity"
            ),
            category="trading",
        )

        allowed = build_public_v5_view(
            profile(),
            items=[item],
        )

        blocked = build_public_v5_view(
            profile(
                exclusions=[
                    "financial_trading"
                ]
            ),
            items=[item],
        )

        self.assertEqual(
            len(
                allowed[
                    "recommendations"
                ]
            ),
            1,
        )

        self.assertEqual(
            len(
                blocked[
                    "recommendations"
                ]
            ),
            0,
        )

    def test_same_currency_over_budget_is_rejected(self):
        item = candidate(
            title="Capital-heavy tool",
            capital="50",
            capital_currency="EUR",
        )

        result = build_public_v5_view(
            profile(
                max_cash_spend_or_risk="25",
            ),
            items=[item],
        )

        self.assertEqual(
            result["recommendations"],
            [],
        )

    def test_different_currency_is_not_false_compared(self):
        item = candidate(
            title="PHP-denominated candidate",
            capital="150",
            capital_currency="PHP",
        )

        result = build_public_v5_view(
            profile(
                currency="EUR",
                max_cash_spend_or_risk="25",
            ),
            items=[item],
        )

        self.assertEqual(
            len(
                result[
                    "recommendations"
                ]
            ),
            1,
        )

    def test_traditional_job_is_not_primary_scope(self):
        item = candidate(
            title=(
                "Full-time role "
                "job vacancy"
            )
        )

        result = build_public_v5_view(
            profile(),
            items=[item],
        )

        self.assertEqual(
            result["recommendations"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
