import importlib.util
import pathlib
import tempfile
import json
import unittest

from fastapi.testclient import TestClient


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_main():
    spec = importlib.util.spec_from_file_location(
        "aoo_main_product_v1_test",
        ROOT / "main.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProductHomeV1Tests(unittest.TestCase):

    def fixture_feed(self):
        return {
            "status": "PASS",
            "scan_id": "fixture-scan",
            "scanned_at": "2026-08-14T00:00:00Z",
            "raw_candidate_count": 20,
            "shortlist_count": 2,
            "items": [
                {
                    "opportunity_id": "opp-1",
                    "title": "Fixture Opportunity One",
                    "organizer": "Fixture Org",
                    "decision": "WATCH",
                    "eligibility": "UNKNOWN",
                    "canonical_source_url":
                        "https://example.com/one",
                    "external_deadline": "2026-08-31",
                    "estimated_effort_hours": 8,
                    "economic_mechanism": "Prize",
                    "asset_fit": "Existing agent stack",
                    "reason_codes": [
                        "APPLICANT_JURISDICTION_NOT_CONFIRMED"
                    ],
                },
                {
                    "opportunity_id": "opp-2",
                    "title": "Fixture Opportunity Two",
                    "organizer": "Other Org",
                    "decision": "PROMOTE",
                    "eligibility": "ELIGIBLE",
                    "canonical_source_url":
                        "https://example.com/two",
                    "external_deadline": "2026-09-10",
                    "estimated_effort_hours": 3,
                    "economic_mechanism": "Grant",
                    "asset_fit": "High",
                    "reason_codes": [],
                },
            ],
        }

    def client(self):
        main = load_main()
        main.load_opportunity_feed = self.fixture_feed

        def forbidden():
            raise AssertionError(
                "Product GET must not construct model workflow"
            )

        return TestClient(
            main.create_app(
                store_factory=forbidden,
                executor_factory=forbidden,
            )
        )

    def test_root_is_product_not_judge_console(self):
        page = self.client().get("/").text
        self.assertIn("Opportunity Inbox", page)
        self.assertIn("Fixture Opportunity One", page)
        self.assertNotIn("Workflow trace", page)

    def test_product_explains_itself_without_registration(self):
        page = self.client().get("/").text
        self.assertIn("No sign-up needed", page)
        self.assertIn("How opportunities get here", page)

    def test_real_candidate_cards_are_primary(self):
        page = self.client().get("/").text
        self.assertIn("Fixture Opportunity One", page)
        self.assertIn("Fixture Opportunity Two", page)
        self.assertIn("Investigate with 7-agent team", page)

    def test_technical_runtime_proof_is_not_on_product_home(self):
        page = self.client().get("/").text
        self.assertNotIn("94.3s", page)
        self.assertNotIn("300s timeout", page)
        self.assertNotIn("SHA-256", page)

    def test_proof_console_still_exists(self):
        page = self.client().get("/judge-console").text
        self.assertIn("Verified Reference Run", page)
        self.assertIn("Workflow trace", page)

    def test_opportunities_endpoint_is_model_free(self):
        response = self.client().get("/opportunities")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["shortlist_count"], 2)
        self.assertEqual(len(data["items"]), 2)

    def test_deep_analysis_requires_explicit_click(self):
        page = self.client().get("/").text
        self.assertIn("data-investigate", page)
        self.assertIn('addEventListener("click"', page)
        self.assertNotIn("autoInvestigate", page)

    def test_user_profile_is_clear_and_not_registration(self):
        page = self.client().get("/").text
        self.assertIn("Decision profile", page)
        self.assertIn("Jurisdiction", page)
        self.assertIn("Available capital", page)
        self.assertIn("Max human hours", page)

    def test_source_link_remains_available(self):
        page = self.client().get("/").text
        self.assertIn("View primary source", page)
        self.assertIn("https://example.com/one", page)

    def test_product_uses_human_reason_language(self):
        page = self.client().get("/").text
        self.assertIn(
            "Applicant jurisdiction not confirmed",
            page,
        )

    def test_feed_loader_accepts_items_container(self):
        module_path = (
            ROOT
            / "src"
            / "opportunity_operator"
            / "opportunity_feed.py"
        )

        self.assertTrue(module_path.exists())

        spec = importlib.util.spec_from_file_location(
            "opportunity_feed_product_test",
            module_path,
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        payload = {
            "scan_id": "x",
            "scanned_at": "now",
            "raw_candidate_count": 20,
            "shortlist_count": 1,
            "items": [
                {
                    "opportunity_id": "x",
                    "title": "X",
                    "decision": "WATCH",
                    "eligibility": "UNKNOWN",
                    "canonical_source_url":
                        "https://example.com/x",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "feed.json"
            path.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            result = module.load_opportunity_feed(path)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["shortlist_count"], 1)
        self.assertEqual(len(result["items"]), 1)


if __name__ == "__main__":
    unittest.main()
