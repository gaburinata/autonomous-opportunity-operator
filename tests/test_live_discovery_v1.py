import importlib.util
import json
import pathlib
import tempfile
import unittest

from fastapi.testclient import TestClient


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LiveDiscoveryV1Tests(unittest.TestCase):

    def discovery(self):
        return load_module(
            "discovery_v1_test",
            ROOT / "src" / "opportunity_operator" / "discovery.py",
        )

    def test_devpost_listing_extracts_real_candidate_links(self):
        m = self.discovery()

        html = """
        <a href="https://alpha-ai.devpost.com/">
          Alpha AI Challenge
        </a>
        <a href="https://secure.devpost.com/login">Login</a>
        <a href="https://evil.example/">Bad</a>
        """

        items = m.discover_devpost_from_html(
            html,
            search_term="AI",
            observed_at="2026-08-14T00:00:00Z",
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(
            items[0]["canonical_source_url"],
            "https://alpha-ai.devpost.com/",
        )
        self.assertEqual(
            items[0]["title"],
            "Alpha AI Challenge",
        )

    def test_devpost_discovery_is_primary_verification_pending(self):
        m = self.discovery()

        items = m.discover_devpost_from_html(
            '<a href="https://agent-prize.devpost.com/">Agent Prize</a>',
            search_term="agent",
            observed_at="2026-08-14T00:00:00Z",
        )

        self.assertEqual(items[0]["decision"], "WATCH")
        self.assertEqual(items[0]["eligibility"], "UNKNOWN")
        self.assertIn(
            "PRIMARY_SOURCE_DEEP_VERIFICATION_PENDING",
            items[0]["reason_codes"],
        )

    def test_nlnet_page_becomes_real_opportunity_signal(self):
        m = self.discovery()

        items = m.discover_nlnet_from_html(
            """
            Calls will reopen September 3rd 2026
            with a deadline of November 3rd 2026
            12:00 CEST.
            Requested Amount between 5000 and 50000.
            """,
            observed_at="2026-08-14T00:00:00Z",
        )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["organizer"], "NLnet Foundation")
        self.assertEqual(
            items[0]["external_deadline"],
            "2026-11-03T10:00:00Z",
        )

    def test_search_terms_are_bounded(self):
        m = self.discovery()

        self.assertEqual(
            m.normalize_search_terms("AI, agent, automation"),
            ["AI", "agent", "automation"],
        )

        with self.assertRaises(ValueError):
            m.normalize_search_terms(
                ",".join(["x"] * 20)
            )

    def test_fetch_url_policy_rejects_unapproved_hosts(self):
        m = self.discovery()

        m.validate_fetch_url(
            "https://devpost.com/hackathons?search=AI"
        )
        m.validate_fetch_url(
            "https://nlnet.nl/propose/"
        )

        with self.assertRaises(ValueError):
            m.validate_fetch_url("https://example.com/")

        with self.assertRaises(ValueError):
            m.validate_fetch_url("http://devpost.com/hackathons")

    def test_discovery_run_deduplicates_and_writes_snapshot(self):
        m = self.discovery()

        def fetcher(url):
            if "devpost.com" in url:
                return """
                <a href="https://same.devpost.com/">Same Event</a>
                <a href="https://same.devpost.com/">Same Event</a>
                """
            if "nlnet.nl" in url:
                return """
                Calls will reopen September 3rd 2026
                with a deadline of November 3rd 2026
                12:00 CEST.
                """
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "latest.json"

            result = m.run_live_discovery(
                "AI",
                fetcher=fetcher,
                snapshot_path=path,
                now="2026-08-14T00:00:00Z",
            )

            stored = json.loads(
                path.read_text(encoding="utf-8")
            )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["shortlist_count"], 2)
        self.assertEqual(stored["scan_id"], result["scan_id"])

    def test_feed_merges_live_discovery_with_stored_radar(self):
        m = load_module(
            "feed_merge_test",
            ROOT / "src" / "opportunity_operator" / "opportunity_feed.py",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)

            radar = tmp / "radar.json"
            live = tmp / "live.json"

            radar.write_text(
                json.dumps({
                    "scan_id": "old",
                    "scanned_at": "old",
                    "raw_candidate_count": 20,
                    "items": [{
                        "opportunity_id": "old-1",
                        "title": "Stored Candidate",
                        "decision": "WATCH",
                        "eligibility": "UNKNOWN",
                        "canonical_source_url":
                            "https://stored.example/item",
                    }],
                }),
                encoding="utf-8",
            )

            live.write_text(
                json.dumps({
                    "status": "PASS",
                    "scan_id": "live",
                    "scanned_at": "new",
                    "raw_candidate_count": 3,
                    "items": [{
                        "opportunity_id": "live-1",
                        "title": "Live Candidate",
                        "decision": "WATCH",
                        "eligibility": "UNKNOWN",
                        "canonical_source_url":
                            "https://live.example/item",
                    }],
                }),
                encoding="utf-8",
            )

            m.DEFAULT_RADAR_PATH = radar
            m.DEFAULT_DISCOVERY_PATH = live

            result = m.load_opportunity_feed()

        titles = {x["title"] for x in result["items"]}

        self.assertEqual(
            titles,
            {"Stored Candidate", "Live Candidate"},
        )
        self.assertEqual(result["scan_id"], "live")

    def test_product_has_explicit_find_action_and_human_deadline(self):
        m = load_module(
            "product_home_discovery_test",
            ROOT / "src" / "opportunity_operator" / "product_home.py",
        )

        page = m.render_product_home({
            "raw_candidate_count": 1,
            "items": [{
                "opportunity_id": "x",
                "title": "X",
                "decision": "WATCH",
                "eligibility": "UNKNOWN",
                "canonical_source_url":
                    "https://x.devpost.com/",
                "external_deadline":
                    "2026-08-25T15:00:00Z",
            }],
        })

        self.assertIn("Find new opportunities", page)
        self.assertIn("Aug 25, 2026 · 15:00 UTC", page)
        self.assertIn("Available capital (€)", page)
        self.assertNotIn("expensive deep analysis", page)

    def test_root_page_never_runs_discovery_automatically(self):
        main = load_module(
            "main_discovery_get_test",
            ROOT / "main.py",
        )

        def forbidden():
            raise AssertionError("GET must not construct workflow")

        def forbidden_discovery(*args, **kwargs):
            raise AssertionError("GET must not run discovery")

        main.run_live_discovery = forbidden_discovery

        client = TestClient(
            main.create_app(
                store_factory=forbidden,
                executor_factory=forbidden,
            )
        )

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Find new opportunities", response.text)

    def test_refresh_endpoint_runs_only_when_explicitly_posted(self):
        main = load_module(
            "main_discovery_post_test",
            ROOT / "main.py",
        )

        calls = []

        def fake_discovery(search_terms):
            calls.append(search_terms)
            return {
                "status": "PASS",
                "scan_id": "fixture",
                "shortlist_count": 2,
                "items": [],
            }

        main.run_live_discovery = fake_discovery

        client = TestClient(main.create_app())

        self.assertEqual(calls, [])

        response = client.post(
            "/discover/refresh",
            json={"search_terms": "AI, agent"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, ["AI, agent"])
        self.assertEqual(
            response.json()["scan_id"],
            "fixture",
        )


if __name__ == "__main__":
    unittest.main()
