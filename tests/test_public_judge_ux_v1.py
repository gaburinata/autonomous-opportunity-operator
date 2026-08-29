from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

import judge_app


class PublicJudgeUxV1Tests(
    unittest.TestCase
):

    def client(self):
        return TestClient(
            judge_app.app
        )

    def test_home_is_unmistakably_product_front_door(
        self,
    ):
        page = self.client().get("/")

        self.assertEqual(
            page.status_code,
            200,
        )

        text = page.text

        self.assertIn(
            "Start here",
            text,
        )

        self.assertIn(
            "This is the Autonomous Opportunity Operator.",
            text,
        )

        self.assertIn(
            "Find what AI can do for me",
            text,
        )

        self.assertIn(
            'href="#frontdoor"',
            text,
        )

        self.assertIn(
            'href="/judge-console"',
            text,
        )

        self.assertIn(
            "View verified 7-agent proof",
            text,
        )

    def test_console_is_explicitly_read_only(
        self,
    ):
        page = self.client().get(
            "/judge-console"
        )

        self.assertEqual(
            page.status_code,
            200,
        )

        text = page.text

        self.assertIn(
            "Technical proof — not the product interface.",
            text,
        )

        self.assertIn(
            "Read-only technical proof",
            text,
        )

        self.assertIn(
            'href="/"',
            text,
        )

        self.assertIn(
            'id="preflightButton" disabled hidden',
            text,
        )

        self.assertIn(
            'id="liveButton" disabled hidden',
            text,
        )

        self.assertIn(
            'id="verified-proof"',
            text,
        )

    def test_personalization_remains_public_and_model_free(
        self,
    ):
        payload = {
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

        response = self.client().post(
            "/opportunities/personalized",
            json=payload,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertIsInstance(
            data,
            dict,
        )


if __name__ == "__main__":
    unittest.main()
