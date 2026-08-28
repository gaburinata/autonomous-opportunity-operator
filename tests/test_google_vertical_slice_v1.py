import ast
import copy
import importlib
import os
from pathlib import Path
import re
import threading
import unittest


ROOT = Path(__file__).parents[1]
EXPECTED_PINS = {
    "google-adk==2.6.3",
    "fastapi==0.141.1",
    "uvicorn==0.52.3",
    "google-cloud-firestore==2.28.1",
}
AGENTS = [
    "discovery_agent",
    "primary_source_verification_agent",
    "deterministic_hard_gate_agent",
    "investigation_agent",
    "failure_memory_agent",
    "economic_evidence_agent",
    "final_adjudication_agent",
]
TOOLS = [
    "eligibility_capital_deadline_gate",
    "failure_memory_similarity_check",
    "calculate_unit_economics",
    "final_evidence_safety_adjudication",
]
STAGES = [
    "PRIMARY_SOURCE_VERIFICATION",
    "DETERMINISTIC_HARD_GATE",
    "INVESTIGATION",
    "FAILURE_MEMORY",
    "ECONOMIC_EVIDENCE",
    "FINAL_ADJUDICATION",
]


def import_optional(name):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError:
        return None


store_module = import_optional("opportunity_operator.firestore_workflow_store")
cloud_module = import_optional("opportunity_operator.cloud_vertical_slice")
main_module = import_optional("main")


class FakeSnapshot:
    def __init__(self, value):
        self.exists = value is not None
        self._value = copy.deepcopy(value)

    def to_dict(self):
        return copy.deepcopy(self._value)


class FakeDocument:
    def __init__(self, client, path):
        self.client = client
        self.path = path

    def get(self, transaction=None):
        with self.client.lock:
            return FakeSnapshot(self.client.documents.get(self.path))

    def create(self, value):
        with self.client.lock:
            if self.path in self.client.documents:
                raise FakeAlreadyExists("document exists")
            self.client.documents[self.path] = copy.deepcopy(value)

    def set(self, value, **kwargs):
        with self.client.lock:
            self.client.documents[self.path] = copy.deepcopy(value)


class FakeCollection:
    def __init__(self, client, name):
        self.client, self.name = client, name

    def document(self, key):
        return FakeDocument(self.client, (self.name, key))


class FakeAlreadyExists(Exception):
    pass


class FakeFirestoreClient:
    """In-memory Firestore-shaped fake; it cannot make service calls."""

    def __init__(self):
        self.documents = {}
        self.lock = threading.RLock()

    def collection(self, name):
        return FakeCollection(self, name)


def workflow_events(final_result=None, model_text="The answer is PROMOTE"):
    final_result = final_result or {
        "disposition": "KILL",
        "reason_codes": ["NON_POSITIVE_UNIT_MARGIN"],
    }
    events = [{"author": name, "text": model_text} for name in AGENTS]
    for name in TOOLS[:-1]:
        events.extend((
            {"author": "tool", "tool_call": {"name": name, "arguments": {}}},
            {"author": "tool", "tool_result": {"name": name, "result": {"ok": True}}},
        ))
    events.extend((
        {"author": "tool", "tool_call": {
            "name": "final_evidence_safety_adjudication", "arguments": {}}},
        {"author": "tool", "tool_result": {
            "name": "final_evidence_safety_adjudication", "result": final_result}},
    ))
    return events


class GoogleVerticalSlicePresenceTests(unittest.TestCase):
    def test_required_production_modules_exist(self):
        self.assertIsNotNone(store_module, "firestore_workflow_store.py is absent")
        self.assertIsNotNone(cloud_module, "cloud_vertical_slice.py is absent")
        self.assertIsNotNone(main_module, "main.py is absent")


@unittest.skipIf(store_module is None, "Firestore production slice not implemented")
class FirestoreWorkflowStoreTests(unittest.TestCase):
    def make_store(self, client=None):
        return store_module.FirestoreWorkflowStore(
            collection="offline_workflows", client=client or FakeFirestoreClient()
        )

    def outcome(self, key="key-1"):
        return {
            "event_id": "evt-1", "opportunity_id": "opp-1",
            "idempotency_key": key, "disposition": "KILL",
            "reason_codes": ["NON_POSITIVE_UNIT_MARGIN"],
            "stage_trace": [], "replayed": False,
        }

    def test_claim_is_idempotent_and_atomic(self):
        client = FakeFirestoreClient()
        first = self.make_store(client)
        second = self.make_store(client)
        results = []
        threads = [threading.Thread(target=lambda s=s: results.append(s.claim("same-key")))
                   for s in (first, second)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(results), [False, True])

    def test_load_returns_only_completed_outcomes(self):
        store = self.make_store()
        self.assertIsNone(store.load("key-1"))
        self.assertTrue(store.claim("key-1"))
        self.assertIsNone(store.load("key-1"))
        expected = self.outcome()
        store.complete("key-1", expected)
        self.assertEqual(store.load("key-1"), expected)

    def test_complete_stores_a_copy_without_mutating_caller(self):
        store = self.make_store()
        store.claim("key-1")
        outcome = self.outcome()
        before = copy.deepcopy(outcome)
        store.complete("key-1", outcome)
        self.assertEqual(outcome, before)
        outcome["reason_codes"].append("CALLER_MUTATION")
        self.assertEqual(store.load("key-1"), before)
        loaded = store.load("key-1")
        loaded["reason_codes"].append("LOADED_MUTATION")
        self.assertEqual(store.load("key-1"), before)


@unittest.skipIf(cloud_module is None, "Cloud executor production slice not implemented")
class CloudAdkExecutorTests(unittest.TestCase):
    def test_fake_root_workflow_runs_at_most_once_across_stage_calls(self):
        calls = []

        def fake(event):
            calls.append(copy.deepcopy(event))
            return workflow_events()

        executor = cloud_module.CloudAdkExecutor(workflow=fake)
        results = []
        for stage in STAGES:
            results.append(executor.execute(stage, {"event_id": "evt"}, tuple(results)))
        self.assertEqual(len(calls), 1)
        self.assertEqual(executor.runtime_evidence()["adk_workflow_runs"], 1)
        self.assertEqual(results[-1]["status"], "TERMINAL")

    def test_repeated_stage_calls_reuse_cached_evidence(self):
        calls = []
        executor = cloud_module.CloudAdkExecutor(
            workflow=lambda event: calls.append(event) or workflow_events()
        )
        first = executor.execute("PRIMARY_SOURCE_VERIFICATION", {"event_id": "evt"}, ())
        second = executor.execute("PRIMARY_SOURCE_VERIFICATION", {"event_id": "evt"}, ())
        final = executor.execute("FINAL_ADJUDICATION", {"event_id": "evt"}, (first, second))
        self.assertEqual(len(calls), 1)
        self.assertEqual(final["disposition"], "KILL")
        evidence = executor.runtime_evidence()
        self.assertEqual(evidence["agents_seen"], AGENTS)
        self.assertEqual(evidence["tools_called"], TOOLS)

    def test_authoritative_final_tool_result_overrides_model_optimism(self):
        executor = cloud_module.CloudAdkExecutor(
            workflow=lambda event: workflow_events(model_text="PROMOTE immediately")
        )
        result = executor.execute("FINAL_ADJUDICATION", {"event_id": "evt"}, ())
        self.assertEqual(result, {
            "status": "TERMINAL", "disposition": "KILL",
            "reason_codes": ["NON_POSITIVE_UNIT_MARGIN"],
        })

    def test_missing_or_malformed_authoritative_final_evidence_fails_closed(self):
        malformed_streams = [
            workflow_events()[:-1],
            workflow_events({"disposition": "PROMOTE", "reason_codes": []}),
            workflow_events({"disposition": "PROCESS", "reason_codes": ["MADE_UP"]}),
        ]
        for stream in malformed_streams:
            with self.subTest(stream=stream[-1:]):
                executor = cloud_module.CloudAdkExecutor(workflow=lambda event, s=stream: s)
                result = executor.execute("FINAL_ADJUDICATION", {"event_id": "evt"}, ())
                self.assertEqual(result["status"], "TERMINAL")
                self.assertEqual(result["disposition"], "KILL")
                self.assertTrue(result["reason_codes"])


@unittest.skipIf(main_module is None, "FastAPI proof service not implemented")
class ProofServiceTests(unittest.TestCase):
    def setUp(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError as exc:
            self.skipTest(str(exc))
        self.TestClient = TestClient
        self.fake_client = FakeFirestoreClient()
        self.workflow_calls = []

        def store_factory():
            return store_module.FirestoreWorkflowStore(
                collection="proof_records", client=self.fake_client
            )

        def executor_factory():
            return cloud_module.CloudAdkExecutor(
                workflow=lambda event: self.workflow_calls.append(copy.deepcopy(event))
                or workflow_events()
            )

        env = {
            "AOO_SOURCE_SHA256": "a" * 64,
            "AOO_MODEL_ID": "gemini-test",
            "K_REVISION": "revision-test",
            "AOO_FIRESTORE_DATABASE": "(default)",
            "AOO_FIRESTORE_COLLECTION": "proof_records",
        }
        self.client = self.TestClient(main_module.create_app(
            store_factory=store_factory, executor_factory=executor_factory, environ=env
        ))

    def test_discovered_first_call_runs_once_and_identical_replay_runs_zero(self):
        first = self.client.post("/proof/discovered", json={"wave_id": "wave-001"})
        self.assertEqual(first.status_code, 200, first.text)
        first_body = first.json()
        self.assertEqual(first_body["outcome"]["disposition"], "KILL")
        self.assertIn("NON_POSITIVE_UNIT_MARGIN", first_body["outcome"]["reason_codes"])
        self.assertEqual(first_body["runtime_evidence"]["adk_workflow_runs"], 1)
        self.assertEqual(len(self.workflow_calls), 1)

        second = self.client.post("/proof/discovered", json={"wave_id": "wave-001"})
        self.assertEqual(second.status_code, 200, second.text)
        self.assertTrue(second.json()["outcome"]["replayed"])
        self.assertEqual(second.json()["runtime_evidence"]["adk_workflow_runs"], 0)
        self.assertEqual(len(self.workflow_calls), 1)

    def test_human_gate_never_executes_workflow(self):
        response = self.client.post("/proof/human-gate", json={"wave_id": "human-001"})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["outcome"]["disposition"], "DECISION_REQUIRED")
        self.assertIn("HUMAN_AUTHORIZATION_REQUIRED", body["outcome"]["reason_codes"])
        self.assertEqual(body["outcome"]["stage_trace"], [])
        self.assertEqual(body["runtime_evidence"]["adk_workflow_runs"], 0)
        self.assertEqual(self.workflow_calls, [])

    def test_health_and_provenance_fields(self):
        self.assertEqual(self.client.get("/health").json()["status"], "ok")
        self.assertTrue(self.client.get("/health").json()["proof_mode"])
        provenance = self.client.get("/provenance").json()
        self.assertEqual(provenance, {
            "source_sha256": "a" * 64, "model_id": "gemini-test",
            "revision": "revision-test", "firestore_database": "(default)",
            "firestore_collection": "proof_records",
        })

    def test_wave_id_is_strictly_bounded(self):
        invalid = ["", "-bad", "bad-", "has space", "../escape", "é", "a" * 65, 7, None]
        for wave_id in invalid:
            with self.subTest(wave_id=wave_id):
                response = self.client.post("/proof/discovered", json={"wave_id": wave_id})
                self.assertEqual(response.status_code, 422)
        self.assertEqual(
            self.client.post("/proof/discovered", json={"wave_id": "ok", "extra": 1}).status_code,
            422,
        )
        self.assertEqual(self.workflow_calls, [])


class StaticBoundaryAndBuildTests(unittest.TestCase):
    def test_no_wallet_trading_payment_or_submission_implementation(self):
        candidates = [
            ROOT / "src/opportunity_operator/firestore_workflow_store.py",
            ROOT / "src/opportunity_operator/cloud_vertical_slice.py",
            ROOT / "main.py",
        ]
        forbidden_defs = re.compile(
            r"^\s*(?:async\s+)?def\s+.*(?:wallet|trad(?:e|ing)|payment|submit|submission)",
            re.IGNORECASE | re.MULTILINE,
        )
        for path in candidates:
            if not path.exists():
                continue
            source = path.read_text(encoding="utf-8")
            self.assertIsNone(forbidden_defs.search(source), path.name)
            tree = ast.parse(source)
            route_literals = {
                node.value for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
                and node.value.startswith("/")
            }
            self.assertFalse(any(any(word in route.lower() for word in
                                     ("prompt", "wallet", "trade", "payment", "submit"))
                                 for route in route_literals), route_literals)

    def test_exact_dependency_pins_are_present_in_both_manifests(self):
        requirements = {
            line.strip() for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertTrue(EXPECTED_PINS.issubset(requirements))
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        for pin in EXPECTED_PINS:
            self.assertIn(f'"{pin}"', pyproject)
        for package in ("google-adk", "fastapi", "uvicorn", "google-cloud-firestore"):
            self.assertNotRegex(pyproject, rf'"{re.escape(package)}\s*(?:>=|~=|\^|>|\*)')

    def test_python_version_is_exactly_312(self):
        version_file = ROOT / ".python-version"
        self.assertTrue(version_file.is_file())
        self.assertEqual(version_file.read_text(encoding="utf-8").rstrip("\n"), "3.12")


if __name__ == "__main__":
    unittest.main()
