import unittest

from fastapi.testclient import (
    TestClient,
)

import judge_app


class PublicV5HomeTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(
            judge_app.app
        )

    def test_home_is_simple_v5_front_door(self):
        response = self.client.get(
            "/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        text = response.text

        self.assertIn(
            "Let AI find ways to make you",
            text,
        )

        self.assertIn(
            "Where do you legally live?",
            text,
        )

        self.assertIn(
            "Citizenship",
            text,
        )

        self.assertIn(
            'id="currency"',
            text,
        )

        self.assertIn(
            "Max cash AOO may spend or put at risk",
            text,
        )

        self.assertIn(
            "Find my best opportunities",
            text,
        )

        self.assertNotIn(
            "Max pursuit budget",
            text,
        )

        self.assertNotIn(
            "Available capital (€)",
            text,
        )

    def test_v5_personalization_is_model_free_and_bounded(self):
        response = self.client.post(
            "/opportunities/personalized",
            json={
                "profile_version":
                    "5",
                "goal":
                    "both",
                "residence_country":
                    "Bulgaria",
                "citizenships":
                    ["Bulgaria"],
                "currency":
                    "EUR",
                "available_money":
                    "150",
                "max_cash_spend_or_risk":
                    "25",
                "human_hours_per_week":
                    "5",
                "exclusions":
                    [],
                "skills_assets":
                    [],
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        data = response.json()

        self.assertEqual(
            data["status"],
            "PASS",
        )

        self.assertEqual(
            data["model_calls"],
            0,
        )

        self.assertEqual(
            data[
                "external_actions_taken"
            ],
            0,
        )

        self.assertLessEqual(
            len(
                data[
                    "recommendations"
                ]
            ),
            3,
        )

    def test_contest_exclusion_changes_real_snapshot_view(self):
        base = {
            "profile_version":
                "5",
            "goal":
                "both",
            "residence_country":
                "Bulgaria",
            "citizenships":
                ["Bulgaria"],
            "currency":
                "EUR",
            "available_money":
                "150",
            "max_cash_spend_or_risk":
                "25",
            "human_hours_per_week":
                "5",
            "exclusions":
                [],
            "skills_assets":
                [],
        }

        first = self.client.post(
            "/opportunities/personalized",
            json=base,
        ).json()

        second_payload = dict(
            base
        )

        second_payload[
            "exclusions"
        ] = [
            "competitions"
        ]

        second = self.client.post(
            "/opportunities/personalized",
            json=second_payload,
        ).json()

        first_titles = [
            item["title"]
            for item in first[
                "recommendations"
            ]
        ]

        second_titles = [
            item["title"]
            for item in second[
                "recommendations"
            ]
        ]

        self.assertNotEqual(
            first_titles,
            second_titles,
        )


if __name__ == "__main__":
    unittest.main()
