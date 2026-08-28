import hashlib
import unittest
from copy import deepcopy

from fastapi.testclient import TestClient

import main
from opportunity_operator.primary_source_intake import (
    build_discovered_event,
    ingest_primary_source,
)


PUBLIC_RESOLVER = lambda host: ["93.184.216.34"]


def fake_fetch(
    body,
    *,
    content_type="text/html; charset=utf-8",
    status_code=200,
    final_url="https://example.com/opportunity",
    redirect_chain=None,
):
    def inner(url, timeout_seconds, max_bytes):
        return {
            "status_code": status_code,
            "headers": {
                "content-type": content_type,
            },
            "body": body,
            "final_url": final_url,
            "redirect_chain": list(redirect_chain or []),
        }
    return inner


class RealPrimarySourceIntakeV1Tests(unittest.TestCase):

    def test_html_capture_has_exact_provenance_and_visible_text(self):
        body = (
            b"<html><head>"
            b"<style>.secret{display:none}</style>"
            b"<script>do_not_keep()</script>"
            b"</head><body>"
            b"<h1>Opportunity &amp; Prize</h1>"
            b"<p>Deadline: 31 August 2026</p>"
            b"</body></html>"
        )

        result = ingest_primary_source(
            "https://example.com/opportunity",
            fetcher=fake_fetch(body),
            resolver=PUBLIC_RESOLVER,
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            result["reason_codes"],
            ["PRIMARY_SOURCE_CAPTURED"],
        )

        self.assertEqual(
            result["source_sha256"],
            hashlib.sha256(body).hexdigest(),
        )

        self.assertIn("Opportunity & Prize", result["text"])
        self.assertIn("Deadline: 31 August 2026", result["text"])

        self.assertNotIn("do_not_keep", result["text"])
        self.assertNotIn("display:none", result["text"])

        self.assertEqual(
            result["text_sha256"],
            hashlib.sha256(
                result["text"].encode("utf-8")
            ).hexdigest(),
        )

        self.assertEqual(result["byte_length"], len(body))
        self.assertEqual(result["text_length"], len(result["text"]))

    def test_http_url_fails_before_fetch(self):
        calls = []

        def fetcher(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("fetcher must not be called")

        result = ingest_primary_source(
            "http://example.com/opportunity",
            fetcher=fetcher,
            resolver=PUBLIC_RESOLVER,
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(result["reason_codes"], ["INVALID_SOURCE_URL"])
        self.assertEqual(calls, [])

    def test_localhost_fails_before_fetch(self):
        calls = []

        def fetcher(*args, **kwargs):
            calls.append(1)
            raise AssertionError("fetcher must not be called")

        result = ingest_primary_source(
            "https://localhost/test",
            fetcher=fetcher,
            resolver=lambda host: ["127.0.0.1"],
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(result["reason_codes"], ["NON_PUBLIC_SOURCE"])
        self.assertEqual(calls, [])

    def test_private_ip_fails_before_fetch(self):
        result = ingest_primary_source(
            "https://10.0.0.7/test",
            fetcher=fake_fetch(b"should not matter"),
            resolver=lambda host: ["10.0.0.7"],
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(result["reason_codes"], ["NON_PUBLIC_SOURCE"])

    def test_credentials_in_url_are_rejected(self):
        result = ingest_primary_source(
            "https://user:pass@example.com/test",
            fetcher=fake_fetch(b"x"),
            resolver=PUBLIC_RESOLVER,
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(result["reason_codes"], ["INVALID_SOURCE_URL"])

    def test_non_443_explicit_port_rejected(self):
        result = ingest_primary_source(
            "https://example.com:8443/test",
            fetcher=fake_fetch(b"x"),
            resolver=PUBLIC_RESOLVER,
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(result["reason_codes"], ["INVALID_SOURCE_URL"])

    def test_redirect_to_private_destination_fails_closed(self):
        body = b"<html><body>hello</body></html>"

        result = ingest_primary_source(
            "https://example.com/start",
            fetcher=fake_fetch(
                body,
                final_url="https://127.0.0.1/secret",
                redirect_chain=[
                    "https://127.0.0.1/secret",
                ],
            ),
            resolver=lambda host: (
                ["127.0.0.1"]
                if host == "127.0.0.1"
                else ["93.184.216.34"]
            ),
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(result["reason_codes"], ["NON_PUBLIC_SOURCE"])

    def test_oversized_body_fails_closed(self):
        body = b"x" * 101

        result = ingest_primary_source(
            "https://example.com/test",
            fetcher=fake_fetch(
                body,
                content_type="text/plain",
            ),
            resolver=PUBLIC_RESOLVER,
            max_bytes=100,
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(result["reason_codes"], ["SOURCE_TOO_LARGE"])
        self.assertEqual(result["text"], "")

    def test_binary_media_type_fails_closed(self):
        result = ingest_primary_source(
            "https://example.com/file",
            fetcher=fake_fetch(
                b"\x89PNG",
                content_type="image/png",
            ),
            resolver=PUBLIC_RESOLVER,
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(
            result["reason_codes"],
            ["UNSUPPORTED_CONTENT_TYPE"],
        )

    def test_non_2xx_status_fails_closed(self):
        result = ingest_primary_source(
            "https://example.com/missing",
            fetcher=fake_fetch(
                b"not found",
                content_type="text/plain",
                status_code=404,
            ),
            resolver=PUBLIC_RESOLVER,
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(
            result["reason_codes"],
            ["SOURCE_HTTP_STATUS_REJECTED"],
        )

    def test_empty_visible_text_fails_closed(self):
        result = ingest_primary_source(
            "https://example.com/empty",
            fetcher=fake_fetch(
                b"<html><script>only_script()</script></html>",
            ),
            resolver=PUBLIC_RESOLVER,
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(
            result["reason_codes"],
            ["SOURCE_TEXT_EMPTY"],
        )

    def test_event_is_deterministic_and_does_not_mutate_document(self):
        document = ingest_primary_source(
            "https://example.com/opportunity",
            fetcher=fake_fetch(
                b"<html><body>Prize opportunity</body></html>"
            ),
            resolver=PUBLIC_RESOLVER,
        )

        before = deepcopy(document)

        first = build_discovered_event(document, "opp-real-001")
        second = build_discovered_event(document, "opp-real-001")

        expected_digest = hashlib.sha256(
            (
                "opp-real-001"
                + "\x00"
                + document["text_sha256"]
            ).encode("utf-8")
        ).hexdigest()

        self.assertEqual(first, second)
        self.assertEqual(document, before)

        self.assertEqual(
            first["event_id"],
            "source-" + expected_digest,
        )

        self.assertEqual(
            first["event_type"],
            "opportunity.discovered",
        )

        self.assertEqual(
            first["opportunity_id"],
            "opp-real-001",
        )

        payload = first["payload"]

        self.assertEqual(
            payload["source_sha256"],
            document["source_sha256"],
        )
        self.assertEqual(
            payload["text_sha256"],
            document["text_sha256"],
        )
        self.assertEqual(
            payload["source_text"],
            document["text"],
        )

    def test_build_event_rejects_failed_document(self):
        failed = ingest_primary_source(
            "http://example.com",
            resolver=PUBLIC_RESOLVER,
        )

        with self.assertRaises(ValueError):
            build_discovered_event(failed, "opp-1")

    def test_http_route_returns_compact_evidence_not_full_text(self):
        def ingestor(url):
            body = b"<html><body>Real opportunity primary source</body></html>"
            return ingest_primary_source(
                url,
                fetcher=fake_fetch(
                    body,
                    final_url=url,
                ),
                resolver=PUBLIC_RESOLVER,
            )

        app = main.create_app(
            store_factory=lambda: None,
            executor_factory=lambda: None,
            primary_source_ingestor=ingestor,
        )

        client = TestClient(app)

        response = client.post(
            "/intake/primary-source",
            json={
                "source_url": "https://example.com/opportunity",
                "opportunity_id": "real-demo-001",
            },
        )

        self.assertEqual(response.status_code, 200)

        payload = response.json()

        self.assertEqual(
            payload["scenario"],
            "primary-source-intake",
        )
        self.assertEqual(payload["status"], "PASS")

        self.assertIn("event_id", payload)
        self.assertIn("source_sha256", payload)
        self.assertIn("text_sha256", payload)
        self.assertIn("text_length", payload)

        serialized = str(payload)

        self.assertNotIn(
            "Real opportunity primary source",
            serialized,
        )

    def test_http_route_does_not_construct_model_executor(self):
        executor_calls = []

        def executor_factory():
            executor_calls.append(1)
            raise AssertionError("executor must not be created")

        def ingestor(url):
            return ingest_primary_source(
                url,
                fetcher=fake_fetch(
                    b"<html><body>Opportunity</body></html>",
                    final_url=url,
                ),
                resolver=PUBLIC_RESOLVER,
            )

        app = main.create_app(
            store_factory=lambda: None,
            executor_factory=executor_factory,
            primary_source_ingestor=ingestor,
        )

        client = TestClient(app)

        response = client.post(
            "/intake/primary-source",
            json={
                "source_url": "https://example.com/x",
                "opportunity_id": "opp-x",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(executor_calls, [])


if __name__ == "__main__":
    unittest.main()
