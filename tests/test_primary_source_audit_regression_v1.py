import hashlib
import unittest
from copy import deepcopy
from unittest.mock import patch

import opportunity_operator.primary_source_intake as intake
from opportunity_operator.primary_source_intake import (
    build_discovered_event,
    ingest_primary_source,
)


PUBLIC_IP = "93.184.216.34"


def resolver_public(host):
    return [PUBLIC_IP]


def fake_fetch(
    body,
    *,
    content_type="text/plain; charset=utf-8",
    status_code=200,
    final_url="https://example.com/source",
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


def valid_document():
    body = b"Primary source evidence for an opportunity."

    result = ingest_primary_source(
        "https://example.com/source",
        fetcher=fake_fetch(body),
        resolver=resolver_public,
    )

    if result["status"] != "PASS":
        raise AssertionError("test fixture did not produce PASS")

    return result


class BinaryTextRegressionTests(unittest.TestCase):

    def test_png_magic_and_nul_bytes_mislabeled_text_plain_fail_closed(self):
        body = b"\x89PNG\x00\x00binary"

        result = ingest_primary_source(
            "https://example.com/source",
            fetcher=fake_fetch(
                body,
                content_type="text/plain",
            ),
            resolver=resolver_public,
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(result["text"], "")
        self.assertEqual(result["text_length"], 0)
        self.assertEqual(result["text_sha256"], "")

    def test_invalid_text_cannot_be_normalized_with_replacement_characters(self):
        body = b"\xff\xfe\xfa\x00not-text"

        result = ingest_primary_source(
            "https://example.com/source",
            fetcher=fake_fetch(
                body,
                content_type="text/plain; charset=utf-8",
            ),
            resolver=resolver_public,
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertNotIn("\ufffd", result["text"])


class DNSPinningRegressionTests(unittest.TestCase):

    def test_default_transport_connects_to_validated_ip_not_hostname(self):
        resolution_calls = []

        def resolver(host):
            resolution_calls.append(host)

            # A second hostname resolution would model rebinding.
            if len(resolution_calls) == 1:
                return [PUBLIC_IP]

            return ["127.0.0.1"]

        connect_targets = []

        def stop_at_connect(address, *args, **kwargs):
            connect_targets.append(address)
            raise OSError("intentional test stop before network")

        with patch.object(
            intake.socket,
            "create_connection",
            side_effect=stop_at_connect,
        ):
            result = ingest_primary_source(
                "https://example.com/source",
                resolver=resolver,
                timeout_seconds=1,
            )

        self.assertEqual(result["status"], "FAIL_CLOSED")

        self.assertTrue(
            connect_targets,
            "default fetch never reached socket connection",
        )

        connected_host = connect_targets[0][0]

        self.assertEqual(
            connected_host,
            PUBLIC_IP,
            "transport must connect to validated numeric IP, not hostname",
        )

        self.assertNotEqual(
            connected_host,
            "example.com",
        )

        self.assertEqual(
            resolution_calls,
            ["example.com"],
            "initial no-redirect hop must not re-resolve the hostname before connect",
        )


class IntakeDocumentIntegrityRegressionTests(unittest.TestCase):

    def assert_rejected(self, document):
        before = deepcopy(document)

        with self.assertRaises(ValueError):
            build_discovered_event(
                document,
                "audit-regression-opportunity",
            )

        self.assertEqual(document, before)

    def test_reason_code_must_be_canonical(self):
        doc = valid_document()
        doc["reason_codes"] = ["PRIMARY_SOURCE_CAPTURED", "FAKE"]

        self.assert_rejected(doc)

    def test_text_length_must_match_text(self):
        doc = valid_document()
        doc["text_length"] += 1

        self.assert_rejected(doc)

    def test_text_hash_must_match_text(self):
        doc = valid_document()
        doc["text_sha256"] = "0" * 64

        self.assert_rejected(doc)

    def test_source_hash_must_be_lowercase_sha256(self):
        doc = valid_document()
        doc["source_sha256"] = "not-a-sha256"

        self.assert_rejected(doc)

    def test_byte_length_must_be_positive_integer(self):
        doc = valid_document()
        doc["byte_length"] = "42"

        self.assert_rejected(doc)

    def test_redirect_chain_must_be_a_sequence_of_https_urls(self):
        doc = valid_document()
        doc["redirect_chain"] = "https://example.com/not-a-list"

        self.assert_rejected(doc)

    def test_text_must_be_nonempty_string(self):
        doc = valid_document()
        doc["text"] = ""

        self.assert_rejected(doc)

    def test_extra_fabricated_fields_do_not_define_successful_intake_document(self):
        doc = valid_document()
        doc["fabricated_authority"] = "PROMOTE"

        self.assert_rejected(doc)


if __name__ == "__main__":
    unittest.main()
