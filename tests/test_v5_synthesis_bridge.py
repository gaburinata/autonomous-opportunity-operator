from __future__ import annotations

import unittest

from opportunity_operator.v5_synthesis_bridge import (
    build_v5_synthesis_policy,
    build_v5_synthesis_prompt,
    execute_v5_evidence_backed_synthesis,
    permitted_latent_families,
    to_v3_synthesis_profile,
)


def profile(
    *,
    exclusions=None,
):
    return {
        "profile_version":
            "5",

        "goal":
            "both",

        "residence_country":
            "Bulgaria",

        "citizenships":
            [
                "Bulgaria",
            ],

        "currency":
            "EUR",

        "available_money":
            "150",

        "max_cash_spend_or_risk":
            "25",

        "human_hours_per_week":
            "5",

        "exclusions":
            exclusions or [],

        "skills_assets":
            [
                "Python",
            ],
    }


def evidence():
    return [
        {
            "source_id":
                "source-api",

            "source_url":
                "https://example.org/api",

            "title":
                "Official API documentation",

            "excerpt":
                (
                    "The documented API exposes machine-readable "
                    "records suitable for repeated automated use."
                ),
        },
        {
            "source_id":
                "source-pricing",

            "source_url":
                "https://example.org/pricing",

            "title":
                "Official pricing documentation",

            "excerpt":
                (
                    "The service documents paid repeated access "
                    "and measurable usage pricing."
                ),
        },
        {
            "source_id":
                "source-market",

            "source_url":
                "https://example.org/market",

            "title":
                "Observed market data",

            "excerpt":
                (
                    "Machine-readable market observations contain "
                    "repeatable price and liquidity measurements."
                ),
        },
    ]


def fake_response():
    return {
        "observations": [
            {
                "title":
                    "Build a niche monitoring SaaS",

                "observed_condition":
                    (
                        "The supplied sources expose repeatable "
                        "machine-readable information and documented "
                        "paid access."
                    ),

                "economic_mechanism":
                    (
                        "Build a narrow subscription monitoring "
                        "product that transforms the source data "
                        "into a recurring user-facing signal."
                    ),

                "value_source":
                    (
                        "Users who value repeated monitoring rather "
                        "than manually checking the raw source."
                    ),

                "why_ai_changes_feasibility":
                    (
                        "AI can automate ingestion, classification, "
                        "summarization, alert generation and much of "
                        "ongoing operation."
                    ),

                "assumptions": [
                    "A paying user segment exists."
                ],

                "cheap_test":
                    (
                        "Build a bounded read-only prototype and test "
                        "whether target users repeatedly use the output."
                    ),

                "evidence_required": [
                    "Observed user demand",
                    "Measured delivery cost",
                ],

                "source_ids": [
                    "source-api",
                    "source-pricing",
                ],

                "mechanism_hint":
                    "niche_saas",
            },
            {
                "title":
                    "Test a systematic market-data mechanism",

                "observed_condition":
                    (
                        "The supplied market source exposes repeated "
                        "machine-readable price and liquidity observations."
                    ),

                "economic_mechanism":
                    (
                        "Test whether a bounded systematic signal can "
                        "produce positive net economics after measured "
                        "costs rather than assuming a trading edge."
                    ),

                "value_source":
                    (
                        "A reproducible market inefficiency, if one "
                        "survives fees, slippage and validation."
                    ),

                "why_ai_changes_feasibility":
                    (
                        "AI can automate data inspection, hypothesis "
                        "generation, experiment construction and monitoring."
                    ),

                "assumptions": [
                    "A measurable repeatable effect may exist."
                ],

                "cheap_test":
                    (
                        "Run a zero-capital historical/replay test and "
                        "kill the mechanism if costs erase the effect."
                    ),

                "evidence_required": [
                    "Out-of-sample market evidence",
                    "Execution-cost measurements",
                ],

                "source_ids": [
                    "source-market",
                ],

                "mechanism_hint":
                    "systematic_market_test",
            },
        ]
    }


class V5SynthesisBridgeTests(
    unittest.TestCase
):

    def test_adapter_preserves_v5_person_context(self):
        adapted = (
            to_v3_synthesis_profile(
                profile()
            )
        )

        self.assertEqual(
            adapted["country"],
            "Bulgaria",
        )

        self.assertEqual(
            adapted[
                "available_capital"
            ],
            "150",
        )

        self.assertEqual(
            adapted[
                "max_cash_spend"
            ],
            "25",
        )

        joined = " ".join(
            adapted["constraints"]
        )

        self.assertIn(
            "Citizenship(s): Bulgaria",
            joined,
        )

        self.assertIn(
            "EUR",
            joined,
        )

    def test_default_scope_includes_build_and_financial_mechanisms(self):
        families = (
            permitted_latent_families(
                profile()
            )
        )

        joined = " ".join(
            families
        ).lower()

        for token in (
            "saas",
            "api",
            "automation",
            "data product",
            "trading",
            "arbitrage",
        ):
            self.assertIn(
                token,
                joined,
            )

    def test_financial_exclusion_removes_financial_families(self):
        families = (
            permitted_latent_families(
                profile(
                    exclusions=[
                        "financial_trading"
                    ]
                )
            )
        )

        joined = " ".join(
            families
        ).lower()

        self.assertNotIn(
            "trading",
            joined,
        )

        self.assertNotIn(
            "arbitrage",
            joined,
        )

        adapted = (
            to_v3_synthesis_profile(
                profile(
                    exclusions=[
                        "financial_trading"
                    ]
                )
            )
        )

        self.assertFalse(
            adapted[
                "willingness"
            ][
                "invest_capital"
            ]
        )

        self.assertFalse(
            adapted[
                "willingness"
            ][
                "financial_protocols"
            ]
        )

    def test_policy_says_not_to_default_to_app(self):
        policy = (
            build_v5_synthesis_policy(
                profile()
            )
        )

        self.assertIn(
            "DO NOT DEFAULT TO 'BUILD AN APP'.",
            policy,
        )

        self.assertIn(
            "No category has a preferred status.",
            policy,
        )

        self.assertIn(
            "Traditional jobs",
            policy,
        )

    def test_combined_prompt_contains_existing_evidence_discipline_and_v5_scope(self):
        prompt = (
            build_v5_synthesis_prompt(
                profile(),
                evidence(),
            )
        )

        lower = prompt.lower()

        for token in (
            "economic mechanism",
            "value source",
            "why ai changes feasibility",
            "cheap",
            "evidence required",
            "source-api",
            "v5 latent opportunity policy",
            "saas",
            "automation",
            "systematic trading",
        ):
            self.assertIn(
                token,
                lower,
            )

    def test_existing_runtime_accepts_materially_different_latent_mechanisms(self):
        calls = []

        def executor(
            prompt_text,
            schema,
        ):
            calls.append(
                (
                    prompt_text,
                    schema,
                )
            )

            return fake_response()

        result = (
            execute_v5_evidence_backed_synthesis(
                profile(),
                evidence(),
                executor,
            )
        )

        self.assertEqual(
            result["status"],
            "PASS",
        )

        self.assertEqual(
            len(calls),
            1,
        )

        self.assertEqual(
            len(
                result[
                    "candidates"
                ]
            ),
            2,
        )

        mechanisms = {
            item["mechanism"]
            for item in result[
                "candidates"
            ]
        }

        self.assertEqual(
            mechanisms,
            {
                "niche_saas",
                "systematic_market_test",
            },
        )

    def test_bridge_does_not_invent_economics(self):
        def executor(
            prompt_text,
            schema,
        ):
            return fake_response()

        result = (
            execute_v5_evidence_backed_synthesis(
                profile(),
                evidence(),
                executor,
            )
        )

        for candidate in result[
            "candidates"
        ]:
            self.assertIsNone(
                candidate["capital_required"]
            )

            self.assertIsNone(
                candidate["estimated_human_hours"]
            )

            self.assertIsNone(
                candidate["ai_executability"]
            )

            self.assertIsNone(
                candidate["estimated_upside"]
            )

            self.assertIsNone(
                candidate["max_loss"]
            )

            self.assertEqual(
                candidate["evidence_quality"],
                0,
            )


if __name__ == "__main__":
    unittest.main()
