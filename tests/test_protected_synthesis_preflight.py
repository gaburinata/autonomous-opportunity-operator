from __future__ import annotations

import unittest

from opportunity_operator.protected_synthesis_preflight import (
    run_protected_synthesis_executor_preflight,
)


class ProtectedSynthesisPreflightTests(
    unittest.TestCase
):

    def test_success_constructs_executor_without_invoking_it(self):

        calls = {
            "builder":
                0,

            "executor":
                0,
        }

        def builder():

            calls[
                "builder"
            ] += 1

            def executor(
                prompt,
                schema,
            ):
                calls[
                    "executor"
                ] += 1

                raise AssertionError(
                    "preflight must never invoke executor"
                )

            return executor

        result = (
            run_protected_synthesis_executor_preflight(
                builder=builder,
            )
        )

        self.assertEqual(
            result[
                "status"
            ],
            "PASS",
        )

        self.assertTrue(
            result[
                "executor_constructed"
            ]
        )

        self.assertFalse(
            result[
                "model_call"
            ]
        )

        self.assertEqual(
            calls,
            {
                "builder":
                    1,

                "executor":
                    0,
            },
        )

    def test_factory_exception_is_sanitized_and_returned(self):

        def builder():
            raise RuntimeError(
                "factory exploded "
                "Bearer SUPERSECRET "
                "access_token=ALSOSECRET"
            )

        result = (
            run_protected_synthesis_executor_preflight(
                builder=builder,
            )
        )

        self.assertEqual(
            result[
                "status"
            ],
            "FAIL_CLOSED",
        )

        self.assertFalse(
            result[
                "executor_constructed"
            ]
        )

        self.assertFalse(
            result[
                "model_call"
            ]
        )

        diagnostic = result[
            "diagnostic"
        ]

        self.assertIn(
            "STAGE=EXECUTOR_FACTORY",
            diagnostic,
        )

        self.assertIn(
            "TYPE=RuntimeError",
            diagnostic,
        )

        self.assertNotIn(
            "SUPERSECRET",
            diagnostic,
        )

        self.assertNotIn(
            "ALSOSECRET",
            diagnostic,
        )

    def test_non_callable_factory_result_fails_closed(self):

        result = (
            run_protected_synthesis_executor_preflight(
                builder=lambda: object(),
            )
        )

        self.assertEqual(
            result[
                "status"
            ],
            "FAIL_CLOSED",
        )

        self.assertFalse(
            result[
                "model_call"
            ]
        )


if __name__ == "__main__":
    unittest.main()
