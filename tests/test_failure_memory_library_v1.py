from __future__ import annotations

import inspect
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from google.adk.tools import FunctionTool

from opportunity_operator.agent import root_agent
from opportunity_operator.failure_memory_library import (
    FailureMemoryLibraryError,
    append_failure_record,
    load_failure_records,
)


class FailureMemoryLibraryV1Tests(
    unittest.TestCase
):

    def _failure_tool(self):
        agent = next(
            item
            for item in root_agent.sub_agents
            if item.name
            == "failure_memory_agent"
        )

        self.assertEqual(
            len(agent.tools),
            1,
        )

        return agent.tools[0]

    def test_production_adk_schema_excludes_failure_records(self):
        raw_tool = self._failure_tool()

        self.assertEqual(
            getattr(
                raw_tool,
                "__name__",
                "",
            ),
            "failure_memory_similarity_check",
        )

        wrapped = FunctionTool(
            raw_tool
        )

        declaration = (
            wrapped._get_declaration()
            .model_dump()
        )

        rendered = json.dumps(
            declaration,
            sort_keys=True,
        )

        self.assertIn(
            "candidate_signature",
            rendered,
        )

        self.assertNotIn(
            "failure_records",
            rendered,
        )

        self.assertNotIn(
            "tool_context",
            rendered,
        )

    def test_python_signature_excludes_failure_records(self):
        raw_tool = self._failure_tool()

        parameters = inspect.signature(
            raw_tool
        ).parameters

        self.assertIn(
            "candidate_signature",
            parameters,
        )

        self.assertNotIn(
            "failure_records",
            parameters,
        )

    def test_default_library_contains_ted_kill(self):
        records = load_failure_records()

        ted = next(
            item
            for item in records
            if item["memory_id"]
            == "failure-ted-tender-to-ticker-v1"
        )

        self.assertEqual(
            ted["failure_class"],
            "STALE_SIGNAL_AND_DIRECT_TRADABILITY_MAPPING_FAILURE",
        )

        self.assertEqual(
            len(ted["evidence"]),
            4,
        )

        self.assertIn(
            "ticker-mapping",
            ted["similarity_signature"],
        )

    def test_malformed_library_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = (
                Path(tmp)
                / "bad.jsonl"
            )

            path.write_text(
                '{"memory_id":"bad"}\n',
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "AOO_FAILURE_MEMORY_PATH":
                        str(path),
                },
                clear=False,
            ):
                with self.assertRaises(
                    FailureMemoryLibraryError
                ):
                    load_failure_records()

    def test_append_is_idempotent_and_conflict_safe(self):
        record = {
            "memory_id":
                "m1",
            "hypothesis":
                "x",
            "environment":
                "test",
            "parameter_regime":
                {},
            "failure_class":
                "TEST_FAILURE",
            "evidence": [
                {
                    "source_id":
                        "e1",
                    "digest":
                        "a" * 64,
                }
            ],
            "similarity_signature": [
                "alpha",
                "beta",
            ],
            "reconsideration_conditions": [
                "new evidence",
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = (
                Path(tmp)
                / "memory.jsonl"
            )

            self.assertEqual(
                append_failure_record(
                    record,
                    path,
                ),
                "APPENDED",
            )

            self.assertEqual(
                append_failure_record(
                    record,
                    path,
                ),
                "UNCHANGED",
            )

            changed = dict(record)

            changed[
                "hypothesis"
            ] = "different"

            with self.assertRaises(
                FailureMemoryLibraryError
            ):
                append_failure_record(
                    changed,
                    path,
                )


if __name__ == "__main__":
    unittest.main()
