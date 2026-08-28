import unittest
from copy import deepcopy

from opportunity_operator.primary_source_intake import (
    build_discovered_event,
    ingest_primary_source,
)


PUBLIC = lambda host: ["93.184.216.34"]


def fetch(body, content_type="text/plain"):
    def inner(url, timeout_seconds, max_bytes):
        return {
            "status_code": 200,
            "headers": {"content-type": content_type},
            "body": body,
            "final_url": url,
            "redirect_chain": [],
        }
    return inner


def valid_document():
    return ingest_primary_source(
        "https://example.com/source",
        fetcher=fetch(b"Legitimate primary source evidence."),
        resolver=PUBLIC,
    )


class DecodableBinarySignatureRegressionTests(unittest.TestCase):

    def test_pdf_magic_mislabeled_text_plain_fails_closed(self):
        result = ingest_primary_source(
            "https://example.com/document",
            fetcher=fetch(
                b"%PDF-1.7\n1 0 obj\nbinary-ish-content",
                "text/plain",
            ),
            resolver=PUBLIC,
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(result["text"], "")
        self.assertEqual(result["text_length"], 0)
        self.assertEqual(result["text_sha256"], "")

    def test_gif_magic_mislabeled_text_plain_fails_closed(self):
        result = ingest_primary_source(
            "https://example.com/image",
            fetcher=fetch(
                b"GIF89a0123456789",
                "text/plain",
            ),
            resolver=PUBLIC,
        )

        self.assertEqual(result["status"], "FAIL_CLOSED")
        self.assertEqual(result["text"], "")


class RedirectProvenanceRegressionTests(unittest.TestCase):

    def assert_rejected(self, doc):
        before = deepcopy(doc)

        with self.assertRaises(ValueError):
            build_discovered_event(doc, "opp-final-audit")

        self.assertEqual(doc, before)

    def test_no_redirect_requires_source_and_final_url_to_match(self):
        doc = valid_document()

        self.assertEqual(doc["redirect_chain"], [])

        doc["final_url"] = "https://different.example/source"

        self.assert_rejected(doc)

    def test_redirect_chain_last_target_must_match_final_url(self):
        doc = valid_document()

        doc["redirect_chain"] = [
            "https://redirect.example/step",
        ]
        doc["final_url"] = "https://different.example/final"

        self.assert_rejected(doc)


if __name__ == "__main__":
    unittest.main()
