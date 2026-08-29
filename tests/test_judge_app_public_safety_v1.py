from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

import judge_app


class JudgeAppPublicSafetyV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(
            judge_app.app
        )

    def test_public_product_is_available(self):
        response = self.client.get("/")

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "Public judge demo",
            response.text,
        )

        self.assertIn(
            "Find my best opportunities",
            response.text,
        )

    def test_public_judge_console_is_available(self):
        response = self.client.get(
            "/judge-console"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "Public judge demo",
            response.text,
        )

        self.assertIn(
            "Google ADK",
            response.text,
        )

    def test_health_declares_safe_public_mode(self):
        response = self.client.get(
            "/health"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertTrue(
            data[
                "public_judge_mode"
            ]
        )

        self.assertFalse(
            data[
                "anonymous_model_execution"
            ]
        )

    def test_provenance_declares_locked_cost_routes(self):
        response = self.client.get(
            "/provenance"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertTrue(
            data[
                "public_judge_mode"
            ]
        )

        self.assertEqual(
            data[
                "anonymous_cost_bearing_routes"
            ],
            "LOCKED",
        )

    def test_deterministic_personalization_remains_public(self):
        response = self.client.post(
            "/opportunities/personalized",
            json={
                "goal": "both",
                "country": "Germany",
                "available_capital": "150",
                "max_cash_spend": "0",
                "human_hours_per_week": "5",
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
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotEqual(
            response.json().get(
                "status"
            ),
            "JUDGE_DEMO_LOCKED",
        )

    def test_cost_bearing_routes_are_locked(self):
        blocked = [
            "/discover/refresh",
            "/opportunities/synthesize",
            "/proof/discovered",
            "/proof/human-gate",
            "/intake/primary-source",
            "/decision/primary-source",
        ]

        for path in blocked:
            with self.subTest(
                path=path
            ):
                response = (
                    self.client.post(
                        path,
                        json={},
                    )
                )

                self.assertEqual(
                    response.status_code,
                    403,
                )

                data = response.json()

                self.assertEqual(
                    data["status"],
                    "JUDGE_DEMO_LOCKED",
                )

                self.assertIn(
                    "ANONYMOUS_COST_BEARING_ACTION_DISABLED",
                    data[
                        "reason_codes"
                    ],
                )

    def test_unknown_mutating_route_fails_closed(self):
        response = self.client.post(
            "/anything/new",
            json={},
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertEqual(
            response.json()[
                "status"
            ],
            "JUDGE_DEMO_LOCKED",
        )


if __name__ == "__main__":
    unittest.main()
