import importlib.util
import pathlib
import unittest

from fastapi.testclient import TestClient


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_main():
    spec = importlib.util.spec_from_file_location(
        "aoo_main_judge_console_test",
        ROOT / "main.py",
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


class JudgeConsoleV1Tests(unittest.TestCase):

    def setUp(self):
        self.main = load_main()

    def client_without_model(self):

        def forbidden_executor():
            raise AssertionError(
                "console GET must not construct model executor"
            )

        def forbidden_store():
            raise AssertionError(
                "console GET must not construct workflow store"
            )

        return TestClient(
            self.main.create_app(
                store_factory=forbidden_store,
                executor_factory=forbidden_executor,
                environ={
                    "AOO_SOURCE_SHA256": "source-fingerprint-test",
                    "AOO_MODEL_ID": "gemini-3.5-flash",
                    "K_REVISION": "revision-test",
                    "AOO_FIRESTORE_DATABASE": "(default)",
                    "AOO_FIRESTORE_COLLECTION":
                        "aoo_proof_workflows",
                },
            )
        )

    def test_root_serves_judge_console_without_model_execution(self):
        response = self.client_without_model().get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Autonomous Opportunity Operator",
            response.text,
        )

    def test_named_console_route_serves_same_product(self):
        response = self.client_without_model().get(
            "/judge-console"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Verified Reference Run",
            response.text,
        )
        self.assertIn(
            "Live Analysis",
            response.text,
        )

    def test_all_seven_agents_are_visible(self):
        page = self.client_without_model().get(
            "/judge-console"
        ).text

        expected = [
            "Discovery",
            "Primary Source Verification",
            "Deterministic Hard Gate",
            "Investigation",
            "Failure Memory",
            "Economic Evidence",
            "Final Adjudication",
        ]

        for name in expected:
            self.assertIn(name, page)

    def test_all_four_authoritative_tools_are_visible(self):
        page = self.client_without_model().get(
            "/judge-console"
        ).text

        expected = [
            "Eligibility · Capital · Deadline Gate",
            "Failure Memory Similarity Check",
            "Unit Economics",
            "Final Evidence &amp; Safety Adjudication",
        ]

        for name in expected:
            self.assertIn(name, page)

    def test_verified_reference_run_is_clearly_labeled(self):
        page = self.client_without_model().get(
            "/judge-console"
        ).text

        self.assertIn(
            "Verified Reference Run",
            page,
        )
        self.assertIn(
            "94.3s",
            page,
        )
        self.assertIn(
            "DECISION_REQUIRED",
            page,
        )
        self.assertIn(
            "0 additional ADK workflows",
            page,
        )

    def test_live_action_is_explicit_not_automatic(self):
        page = self.client_without_model().get(
            "/judge-console"
        ).text

        self.assertIn(
            "Run live 7-agent analysis",
            page,
        )

        self.assertIn(
            '"/decision/primary-source"',
            page,
        )

        self.assertNotIn(
            "window.onload = runLive",
            page,
        )

        self.assertNotIn(
            "runLive();",
            page,
        )

    def test_provenance_and_intake_endpoints_are_used(self):
        page = self.client_without_model().get(
            "/judge-console"
        ).text

        self.assertIn(
            '"/provenance"',
            page,
        )

        self.assertIn(
            '"/intake/primary-source"',
            page,
        )

    def test_existing_health_and_provenance_contracts_remain(self):
        client = self.client_without_model()

        health = client.get("/health")

        self.assertEqual(
            health.status_code,
            200,
        )

        self.assertEqual(
            health.json()["status"],
            "ok",
        )

        provenance = client.get(
            "/provenance"
        ).json()

        self.assertEqual(
            provenance["model_id"],
            "gemini-3.5-flash",
        )


if __name__ == "__main__":
    unittest.main()
