import importlib.util
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def discovery():
    path = (
        ROOT
        / "src"
        / "opportunity_operator"
        / "discovery.py"
    )

    spec = importlib.util.spec_from_file_location(
        "devpost_api_connector_test",
        path,
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


FIXTURE = {
    "hackathons": [
        {
            "id": 30845,
            "title": "All Things Agentic Hackathon",
            "organization_name": "Google",
            "url":
                "https://allthingsagentichackathon.devpost.com/",
            "open_state": "open",
            "time_left_to_submission": "17 days left",
            "submission_period_dates": "Aug 04 - 31, 2026",
            "themes": [
                {"id": 21, "name": "Enterprise"},
                {"id": 6, "name": "Machine Learning/AI"},
                {"id": 11, "name": "Productivity"},
            ],
            "prize_amount":
                "$<span data-currency-value>180,000</span>",
            "registrations_count": 2645,
            "invite_only": False,
            "featured": True,
        },
        {
            "id": 1,
            "title": "Unrelated Cooking Event",
            "organization_name": "Food Org",
            "url":
                "https://cooking-event.devpost.com/",
            "open_state": "open",
            "time_left_to_submission": "20 days left",
            "submission_period_dates": "Aug 01 - Sep 01, 2026",
            "themes": [
                {"id": 1, "name": "Food"},
            ],
            "prize_amount":
                "$<span data-currency-value>1,000</span>",
            "registrations_count": 10,
            "invite_only": False,
            "featured": False,
        },
    ],
    "meta": {
        "total_count": 2,
        "per_page": 9,
        "fuzzy": False,
    },
}


class DevpostOfficialApiConnectorTests(unittest.TestCase):

    def test_api_payload_yields_relevant_candidate(self):
        m = discovery()

        items = m.discover_devpost_from_api(
            FIXTURE,
            search_terms=[
                "AI agents",
                "automation",
            ],
            observed_at="2026-08-14T00:00:00Z",
        )

        self.assertEqual(len(items), 1)

        item = items[0]

        self.assertEqual(
            item["title"],
            "All Things Agentic Hackathon",
        )

        self.assertEqual(
            item["organizer"],
            "Google",
        )

        self.assertEqual(
            item["canonical_source_url"],
            "https://allthingsagentichackathon.devpost.com/",
        )

        self.assertEqual(
            item["decision"],
            "WATCH",
        )

        self.assertIn(
            "PRIMARY_SOURCE_DEEP_VERIFICATION_PENDING",
            item["reason_codes"],
        )

    def test_api_prize_markup_is_cleaned(self):
        m = discovery()

        items = m.discover_devpost_from_api(
            FIXTURE,
            search_terms=["AI"],
            observed_at="2026-08-14T00:00:00Z",
        )

        self.assertIn(
            "$180,000",
            items[0]["economic_mechanism"],
        )

        self.assertNotIn(
            "<span",
            items[0]["economic_mechanism"],
        )

    def test_invite_only_and_closed_items_are_rejected(self):
        m = discovery()

        fixture = {
            "hackathons": [
                {
                    "id": 1,
                    "title": "AI Closed",
                    "organization_name": "X",
                    "url": "https://closed-ai.devpost.com/",
                    "open_state": "closed",
                    "themes": [{"name": "Machine Learning/AI"}],
                    "invite_only": False,
                },
                {
                    "id": 2,
                    "title": "AI Invite",
                    "organization_name": "X",
                    "url": "https://invite-ai.devpost.com/",
                    "open_state": "open",
                    "themes": [{"name": "Machine Learning/AI"}],
                    "invite_only": True,
                },
                {
                    "id": 3,
                    "title": "AI Open",
                    "organization_name": "X",
                    "url": "https://open-ai.devpost.com/",
                    "open_state": "open",
                    "themes": [{"name": "Machine Learning/AI"}],
                    "invite_only": False,
                },
            ]
        }

        items = m.discover_devpost_from_api(
            fixture,
            search_terms=["AI"],
            observed_at="2026-08-14T00:00:00Z",
        )

        self.assertEqual(
            [
                x["canonical_source_url"]
                for x in items
            ],
            [
                "https://open-ai.devpost.com/",
            ],
        )

    def test_nlnet_current_markup_extracts_deadline_and_amount(self):
        m = discovery()

        document = '''
        <html>
          New calls will open up September
          3<sup>rd</sup> 2026 with a deadline
          of November 3<sup>rd</sup> 2026
          12:00 CEST.

          <input
            placeholder="between 5,000 and 50,000"
          >
        </html>
        '''

        items = m.discover_nlnet_from_html(
            document,
            observed_at="2026-08-14T00:00:00Z",
        )

        self.assertEqual(len(items), 1)

        item = items[0]

        self.assertEqual(
            item["external_deadline"],
            "2026-11-03T10:00:00Z",
        )

        self.assertIn(
            "€5,000",
            item["economic_mechanism"],
        )

        self.assertIn(
            "€50,000",
            item["economic_mechanism"],
        )


if __name__ == "__main__":
    unittest.main()
