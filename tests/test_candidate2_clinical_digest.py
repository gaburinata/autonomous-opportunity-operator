from __future__ import annotations

import copy
import unittest

from opportunity_operator.candidate2_clinical_digest import (
    ClinicalDigestContractError,
    DISCLAIMER,
    PROTOTYPE_KIND,
    build_digest_generation_request,
    normalize_source_records,
    validate_digest_output,
)


def records():
    return [
        {
            "source_id":
                f"openalex-W{i}",

            "title":
                f"Pediatric dentistry research paper {i}",

            "publication_date":
                f"2026-08-{10 + i:02d}",

            "abstract":
                (
                    "This research abstract contains enough source-grounded "
                    "content to support a bounded professional synthesis "
                    f"example for pediatric dentistry paper {i}."
                ),

            "source_url":
                f"https://openalex.org/W{i}",
        }
        for i in range(1, 7)
    ]


def valid_output():
    return {
        "prototype_kind":
            PROTOTYPE_KIND,

        "digest_title":
            "Monday Morning Pediatric Dentistry Research Review",

        "audience":
            "Licensed pediatric dentists",

        "executive_summary":
            (
                "Three recent research themes deserve professional review; "
                "none is treated here as a stand-alone change to standard care."
            ),

        "items":
            [
                {
                    "source_ids":
                        [
                            "openalex-W1",
                            "openalex-W2",
                        ],

                    "topic":
                        "Preventive care evidence",

                    "what_changed":
                        (
                            "Two recent reports add evidence relevant to "
                            "preventive-care decision making."
                        ),

                    "why_it_matters":
                        (
                            "The findings may be useful when reviewing "
                            "current preventive-care protocols."
                        ),

                    "practice_review_question":
                        (
                            "Does the new evidence justify reviewing any "
                            "existing preventive-care assumptions?"
                        ),

                    "evidence_review":
                        "REVIEW_NOW",

                    "caveats":
                        (
                            "Abstract-level synthesis only; study design "
                            "and full-text limitations require review."
                        ),
                },
                {
                    "source_ids":
                        [
                            "openalex-W3",
                        ],

                    "topic":
                        "Behavior management",

                    "what_changed":
                        (
                            "A recent report adds evidence related to "
                            "behavior-management outcomes."
                        ),

                    "why_it_matters":
                        (
                            "It may inform which questions deserve closer "
                            "full-text review by clinicians."
                        ),

                    "practice_review_question":
                        (
                            "Is this evidence consistent with the assumptions "
                            "behind current behavior-management protocols?"
                        ),

                    "evidence_review":
                        "WATCH",

                    "caveats":
                        (
                            "Single-source signal and no independent "
                            "replication established here."
                        ),
                },
                {
                    "source_ids":
                        [
                            "openalex-W4",
                            "openalex-W5",
                        ],

                    "topic":
                        "Restorative outcomes",

                    "what_changed":
                        (
                            "Two papers report findings relevant to "
                            "restorative outcome assessment."
                        ),

                    "why_it_matters":
                        (
                            "The combined signal can prioritize which "
                            "full papers merit professional review."
                        ),

                    "practice_review_question":
                        (
                            "Which outcome assumptions should be checked "
                            "against these full-text studies?"
                        ),

                    "evidence_review":
                        "BACKGROUND",

                    "caveats":
                        (
                            "No claim is made that these studies establish "
                            "a new treatment standard."
                        ),
                },
            ],

        "limitations":
            [
                "Based on admitted source records rather than complete literature.",
                "Full-text methodology and applicability require professional review.",
            ],

        "disclaimer":
            DISCLAIMER,
    }


class SourceContractTests(
    unittest.TestCase
):

    def test_source_normalization_is_deterministic(self):

        first = normalize_source_records(
            records()
        )

        second = normalize_source_records(
            copy.deepcopy(
                records()
            )
        )

        self.assertEqual(
            first,
            second,
        )

    def test_generation_request_is_deterministic(self):

        first = build_digest_generation_request(
            records()
        )

        second = build_digest_generation_request(
            records()
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            first["source_count"],
            6,
        )

        self.assertEqual(
            len(
                first[
                    "source_digest"
                ]
            ),
            64,
        )

    def test_too_few_sources_fail_closed(self):

        with self.assertRaises(
            ClinicalDigestContractError
        ):
            normalize_source_records(
                records()[:4]
            )

    def test_duplicate_source_id_fails_closed(self):

        sample = records()

        sample[1][
            "source_id"
        ] = sample[0][
            "source_id"
        ]

        with self.assertRaises(
            ClinicalDigestContractError
        ):
            normalize_source_records(
                sample
            )


class OutputContractTests(
    unittest.TestCase
):

    def admitted(self):
        return [
            item["source_id"]
            for item in records()
        ]

    def test_valid_differentiated_digest_passes(self):

        result = validate_digest_output(
            valid_output(),
            admitted_source_ids=
                self.admitted(),
        )

        self.assertGreaterEqual(
            result[
                "represented_source_count"
            ],
            3,
        )

        self.assertFalse(
            result[
                "economic_claims"
            ][
                "promotion_allowed"
            ]
        )

        self.assertFalse(
            result[
                "economic_claims"
            ][
                "customer_demand_proven"
            ]
        )

    def test_unknown_source_citation_fails_closed(self):

        payload = valid_output()

        payload[
            "items"
        ][0][
            "source_ids"
        ] = [
            "invented-source"
        ]

        with self.assertRaises(
            ClinicalDigestContractError
        ):
            validate_digest_output(
                payload,
                admitted_source_ids=
                    self.admitted(),
            )

    def test_insufficient_source_coverage_fails(self):

        payload = valid_output()

        for item in payload["items"]:
            item[
                "source_ids"
            ] = [
                "openalex-W1"
            ]

        with self.assertRaises(
            ClinicalDigestContractError
        ):
            validate_digest_output(
                payload,
                admitted_source_ids=
                    self.admitted(),
            )

    def test_treatment_command_fails_closed(self):

        payload = valid_output()

        payload[
            "items"
        ][0][
            "why_it_matters"
        ] = (
            "Prescribe this intervention "
            "for patients immediately."
        )

        with self.assertRaises(
            ClinicalDigestContractError
        ):
            validate_digest_output(
                payload,
                admitted_source_ids=
                    self.admitted(),
            )

    def test_review_prompt_must_be_question(self):

        payload = valid_output()

        payload[
            "items"
        ][0][
            "practice_review_question"
        ] = (
            "Review the protocol immediately"
        )

        with self.assertRaises(
            ClinicalDigestContractError
        ):
            validate_digest_output(
                payload,
                admitted_source_ids=
                    self.admitted(),
            )

    def test_disclaimer_is_authoritative(self):

        payload = valid_output()

        payload[
            "disclaimer"
        ] = "No disclaimer needed."

        with self.assertRaises(
            ClinicalDigestContractError
        ):
            validate_digest_output(
                payload,
                admitted_source_ids=
                    self.admitted(),
            )

    def test_generic_newsletter_cannot_claim_economics(self):

        result = validate_digest_output(
            valid_output(),
            admitted_source_ids=
                self.admitted(),
        )

        economics = result[
            "economic_claims"
        ]

        self.assertEqual(
            economics,
            {
                "customer_demand_proven":
                    False,

                "willingness_to_pay_proven":
                    False,

                "revenue_proven":
                    False,

                "unit_economics_proven":
                    False,

                "profitability_proven":
                    False,

                "promotion_allowed":
                    False,
            },
        )



class AuthorityLiteralSchemaTests(
    unittest.TestCase
):

    def test_prototype_kind_is_schema_enforced_constant(self):

        request = (
            build_digest_generation_request(
                records()
            )
        )

        schema = request[
            "response_schema"
        ]

        prototype = (
            schema[
                "properties"
            ][
                "prototype_kind"
            ]
        )

        self.assertEqual(
            prototype[
                "type"
            ],
            "string",
        )

        self.assertEqual(
            prototype[
                "enum"
            ],
            [
                PROTOTYPE_KIND,
            ],
        )


    def test_disclaimer_is_schema_enforced_constant(self):

        request = (
            build_digest_generation_request(
                records()
            )
        )

        schema = request[
            "response_schema"
        ]

        disclaimer = (
            schema[
                "properties"
            ][
                "disclaimer"
            ]
        )

        self.assertEqual(
            disclaimer[
                "type"
            ],
            "string",
        )

        self.assertEqual(
            disclaimer[
                "enum"
            ],
            [
                DISCLAIMER,
            ],
        )


if __name__ == "__main__":
    unittest.main()
