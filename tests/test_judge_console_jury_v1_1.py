import importlib.util
import pathlib
import unittest

from fastapi.testclient import TestClient


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_main():
    spec = importlib.util.spec_from_file_location(
        "aoo_main_jury_v11_repair_test",
        ROOT / "main.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JudgeConsoleJuryV11Tests(unittest.TestCase):

    def setUp(self):
        main = load_main()

        def forbidden():
            raise AssertionError(
                "GET judge console must not execute workflow"
            )

        self.client = TestClient(
            main.create_app(
                store_factory=forbidden,
                executor_factory=forbidden,
            )
        )
        self.page = self.client.get("/judge-console").text

    def test_value_proposition_is_immediate(self):
        self.assertIn(
            "From messy opportunity to",
            self.page,
        )
        self.assertIn(
            "evidence-backed decision.",
            self.page,
        )

    def test_console_explicitly_says_not_a_chatbot(self):
        self.assertIn(
            "Not a chatbot.",
            self.page,
        )
        self.assertIn(
            "auditable workflow",
            self.page,
        )

    def test_final_outcome_is_hero_not_latency(self):
        self.assertIn(
            "FINAL OUTCOME",
            self.page,
        )
        self.assertIn(
            "DECISION REQUIRED",
            self.page,
        )
        self.assertNotIn(
            '<div class="proof-number">',
            self.page,
        )

    def test_human_value_metrics_are_primary(self):
        for value in [
            "47,306",
            "source characters verified",
            "specialist agents",
            "deterministic checks",
            "consequential actions without approval",
        ]:
            self.assertIn(value, self.page)

    def test_machine_reason_codes_are_visually_secondary(self):
        self.assertIn(
            'class="machine-code"',
            self.page,
        )
        self.assertIn(
            "Registration requires your approval",
            self.page,
        )
        self.assertIn(
            "Cloud resource creation requires your approval",
            self.page,
        )
        self.assertIn(
            "External submission requires your approval",
            self.page,
        )

    def test_latency_proof_is_still_preserved(self):
        self.assertIn("94.3s", self.page)
        self.assertIn("300s timeout", self.page)

    def test_live_empty_state_explains_the_workflow(self):
        self.assertIn(
            "What the team will do",
            self.page,
        )
        self.assertIn(
            "Read &amp; verify",
            self.page,
        )
        self.assertIn(
            "Test &amp; remember",
            self.page,
        )
        self.assertIn(
            "Decide &amp; stop safely",
            self.page,
        )

    def test_existing_live_action_remains_explicit(self):
        self.assertIn(
            "Run live 7-agent analysis",
            self.page,
        )
        self.assertNotIn(
            "runLive();",
            self.page,
        )


if __name__ == "__main__":
    unittest.main()
