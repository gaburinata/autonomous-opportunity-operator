import ast
import pathlib
import unittest

from opportunity_operator.agent import root_agent


EXPECTED = [
    "discovery_agent",
    "primary_source_verification_agent",
    "deterministic_hard_gate_agent",
    "investigation_agent",
    "failure_memory_agent",
    "economic_evidence_agent",
    "final_adjudication_agent",
]

OUTPUT_KEYS = {
    "discovery_agent": "discovery_brief",
    "primary_source_verification_agent": "verification_brief",
    "deterministic_hard_gate_agent": "hard_gate_brief",
    "investigation_agent": "investigation_brief",
    "failure_memory_agent": "failure_memory_brief",
    "economic_evidence_agent": "economic_brief",
    "final_adjudication_agent": "final_brief",
}


class ContextCompactionV11Tests(unittest.TestCase):

    def agents(self):
        return list(root_agent.sub_agents)

    def test_exact_seven_agent_topology_is_preserved(self):
        agents = self.agents()

        self.assertEqual(
            [x.name for x in agents],
            EXPECTED,
        )

        self.assertEqual(len(agents), 7)

    def test_all_llm_agents_disable_conversation_history(self):
        for agent in self.agents():
            self.assertEqual(
                agent.include_contents,
                "none",
                agent.name,
            )

    def test_every_agent_has_explicit_state_output_key(self):
        for agent in self.agents():
            self.assertEqual(
                agent.output_key,
                OUTPUT_KEYS[agent.name],
                agent.name,
            )

    def test_only_first_two_agents_receive_full_source_text(self):
        agents = {
            x.name: str(x.instruction)
            for x in self.agents()
        }

        self.assertIn(
            "{source_text}",
            agents["discovery_agent"],
        )

        self.assertIn(
            "{source_text}",
            agents["primary_source_verification_agent"],
        )

        for name in EXPECTED[2:]:
            self.assertNotIn(
                "{source_text}",
                agents[name],
                name,
            )

    def test_later_agents_use_compact_prior_state(self):
        agents = {
            x.name: str(x.instruction)
            for x in self.agents()
        }

        self.assertIn(
            "{verification_brief}",
            agents["deterministic_hard_gate_agent"],
        )

        self.assertIn(
            "{verification_brief}",
            agents["investigation_agent"],
        )

        self.assertIn(
            "{investigation_brief}",
            agents["failure_memory_agent"],
        )

        self.assertIn(
            "{investigation_brief}",
            agents["economic_evidence_agent"],
        )

        final = agents["final_adjudication_agent"]

        for token in (
            "{verification_brief}",
            "{hard_gate_brief}",
            "{investigation_brief}",
            "{failure_memory_brief}",
            "{economic_brief}",
        ):
            self.assertIn(token, final)

    def test_cloud_executor_semantically_uses_state_and_compact_message(self):
        path = pathlib.Path(
            "src/opportunity_operator/cloud_vertical_slice.py"
        )

        source = path.read_text()
        tree = ast.parse(source)

        create_session_with_state = False
        source_text_in_initial_state = False
        old_full_event_message = False

        string_constants = []

        for node in ast.walk(tree):

            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
            ):
                string_constants.append(node.value)

            if isinstance(node, ast.Call):

                # Detect create_session(..., state=initial_state)
                func = node.func

                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "create_session"
                ):
                    for kw in node.keywords:
                        if (
                            kw.arg == "state"
                            and isinstance(kw.value, ast.Name)
                            and kw.value.id == "initial_state"
                        ):
                            create_session_with_state = True

                # Reject old str(event) user-message construction.
                if (
                    isinstance(func, ast.Name)
                    and func.id == "str"
                    and len(node.args) == 1
                    and isinstance(node.args[0], ast.Name)
                    and node.args[0].id == "event"
                ):
                    old_full_event_message = True

            if isinstance(node, ast.Dict):

                keys = []

                for key in node.keys:
                    if (
                        isinstance(key, ast.Constant)
                        and isinstance(key.value, str)
                    ):
                        keys.append(key.value)

                if "source_text" in keys:
                    source_text_in_initial_state = True

        all_strings = " ".join(string_constants)

        self.assertTrue(
            create_session_with_state
        )

        self.assertTrue(
            source_text_in_initial_state
        )

        self.assertFalse(
            old_full_event_message
        )

        self.assertIn(
            "Execute the AOO decision workflow using",
            all_strings,
        )

        self.assertIn(
            "authoritative session state.",
            all_strings,
        )


if __name__ == "__main__":
    unittest.main()
