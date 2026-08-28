from __future__ import annotations

import ast
import copy
from dataclasses import FrozenInstanceError
from decimal import Decimal
from pathlib import Path
import unittest

from opportunity_operator.real_source_decision import (
    canonicalize_decision_profile,
)

from opportunity_operator.user_profile import (
    canonicalize_user_profile,
    to_decision_profile,
)

from opportunity_operator.opportunity_candidate import (
    CandidateOrigin,
    OpportunityCandidate,
)

from opportunity_operator.personalized_ranking import (
    RankingResult,
    rank_candidates,
    score_candidate,
)

from opportunity_operator.opportunity_synthesis import (
    SynthesisObservation,
    build_synthesized_candidate,
)


ROOT = Path(__file__).resolve().parents[1]


def base_profile(**changes):
    value = {
        "goal": "both",
        "country": "Bulgaria",
        "available_capital": "150.00",
        "max_cash_spend": "0.00",
        "human_hours_per_week": "8.0",
        "ai_autonomy": "maximum",
        "willingness": {
            "build_business": True,
            "work_with_customers": False,
            "sell": False,
            "publish_content": False,
            "invest_capital": False,
            "contests_juries": True,
            "financial_protocols": True,
        },
        "skills_assets": [
            "Python",
            "Hetzner CX33",
        ],
        "constraints": [
            "No leverage",
            "No borrowing",
        ],
    }
    value.update(changes)
    return value


def candidate(
    candidate_id,
    *,
    applicant_feasibility="ELIGIBLE",
    capital_required="0",
    estimated_human_hours="2",
    ai_executability=90,
    human_burden=10,
    customer_dependency=0,
    sales_dependency=0,
    external_decision_dependency=20,
    time_to_evidence_days=7,
    evidence_quality=80,
    requires_business_build=False,
    requires_customer_work=False,
    requires_sales=False,
    requires_content=False,
    is_contest_or_jury=False,
    is_financial_protocol=False,
):
    return OpportunityCandidate(
        candidate_id=candidate_id,
        title="Candidate " + candidate_id,
        origin=CandidateOrigin.EXPLICIT,
        mechanism="test-mechanism",
        hypothesis="Test hypothesis",
        economic_mechanism="Explicit value exchange",
        value_source="Known payer/value source",
        source_ids=("source-1",),
        canonical_source_url="https://example.com/opportunity",
        applicant_feasibility=applicant_feasibility,
        capital_required=Decimal(capital_required),
        estimated_human_hours=(
            None
            if estimated_human_hours is None
            else Decimal(estimated_human_hours)
        ),
        ai_executability=ai_executability,
        human_burden=human_burden,
        customer_dependency=customer_dependency,
        sales_dependency=sales_dependency,
        external_decision_dependency=external_decision_dependency,
        time_to_evidence_days=time_to_evidence_days,
        estimated_upside=None,
        max_loss=None,
        evidence_quality=evidence_quality,
        requires_business_build=requires_business_build,
        requires_customer_work=requires_customer_work,
        requires_sales=requires_sales,
        requires_content=requires_content,
        is_contest_or_jury=is_contest_or_jury,
        is_financial_protocol=is_financial_protocol,
    )


class UserProfileTests(unittest.TestCase):

    def test_profile_canonicalization_is_deterministic_and_nonmutating(self):
        raw = base_profile()
        before = copy.deepcopy(raw)

        first = canonicalize_user_profile(raw)
        second = canonicalize_user_profile(raw)

        self.assertEqual(first, second)
        self.assertEqual(raw, before)
        self.assertEqual(first["available_capital"], "150")
        self.assertEqual(first["max_cash_spend"], "0")
        self.assertEqual(first["human_hours_per_week"], "8")
        self.assertEqual(first["country"], "Bulgaria")
        self.assertEqual(first["goal"], "both")
        self.assertEqual(first["ai_autonomy"], "maximum")

    def test_profile_rejects_extra_bad_numeric_and_overspend(self):
        bad = []

        extra = base_profile()
        extra["unexpected"] = True
        bad.append(extra)

        bad.append(base_profile(available_capital="-1"))
        bad.append(base_profile(max_cash_spend="NaN"))
        bad.append(
            base_profile(
                available_capital="10",
                max_cash_spend="11",
            )
        )

        malformed_willingness = base_profile()
        malformed_willingness["willingness"] = {
            "sell": False
        }
        bad.append(malformed_willingness)

        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    canonicalize_user_profile(value)

    def test_v3_profile_adapts_to_frozen_decision_profile(self):
        canonical = canonicalize_user_profile(base_profile())
        legacy = to_decision_profile(canonical)

        self.assertEqual(
            set(legacy),
            {
                "operator_jurisdiction",
                "available_capital",
                "max_cash_spend",
                "max_human_hours",
                "objective",
            },
        )

        self.assertEqual(legacy["operator_jurisdiction"], "Bulgaria")
        self.assertEqual(legacy["available_capital"], "150")
        self.assertEqual(legacy["max_cash_spend"], "0")
        self.assertEqual(legacy["max_human_hours"], "8")
        self.assertIn("both", legacy["objective"].lower())
        self.assertIn("maximum", legacy["objective"].lower())

        accepted = canonicalize_decision_profile(legacy)
        self.assertEqual(accepted, legacy)


class CandidateModelTests(unittest.TestCase):

    def test_candidate_supports_explicit_and_synthesized_origin(self):
        explicit = candidate("explicit-1")

        self.assertEqual(
            explicit.origin,
            CandidateOrigin.EXPLICIT,
        )

        synthesized = OpportunityCandidate(
            candidate_id="synth-1",
            title="Synthesized",
            origin=CandidateOrigin.SYNTHESIZED,
            mechanism="api",
            hypothesis="A testable hypothesis",
            economic_mechanism="Usage payment",
            value_source="API buyer",
            source_ids=("observation-source",),
            canonical_source_url=None,
            applicant_feasibility="UNKNOWN",
            capital_required=Decimal("0"),
            estimated_human_hours=None,
            ai_executability=None,
            human_burden=None,
            customer_dependency=None,
            sales_dependency=None,
            external_decision_dependency=None,
            time_to_evidence_days=None,
            estimated_upside=None,
            max_loss=None,
            evidence_quality=20,
            requires_business_build=True,
            requires_customer_work=False,
            requires_sales=False,
            requires_content=False,
            is_contest_or_jury=False,
            is_financial_protocol=False,
        )

        self.assertEqual(
            synthesized.origin,
            CandidateOrigin.SYNTHESIZED,
        )

    def test_candidate_validates_ranges_and_provenance(self):
        with self.assertRaises(ValueError):
            candidate(
                "bad-range",
                ai_executability=101,
            )

        with self.assertRaises(ValueError):
            OpportunityCandidate(
                candidate_id="no-source",
                title="No source",
                origin=CandidateOrigin.EXPLICIT,
                mechanism="x",
                hypothesis="x",
                economic_mechanism="x",
                value_source="x",
                source_ids=(),
                canonical_source_url=None,
                applicant_feasibility="ELIGIBLE",
                capital_required=Decimal("0"),
                estimated_human_hours=None,
                ai_executability=None,
                human_burden=None,
                customer_dependency=None,
                sales_dependency=None,
                external_decision_dependency=None,
                time_to_evidence_days=None,
                estimated_upside=None,
                max_loss=None,
                evidence_quality=0,
                requires_business_build=False,
                requires_customer_work=False,
                requires_sales=False,
                requires_content=False,
                is_contest_or_jury=False,
                is_financial_protocol=False,
            )

    def test_candidate_is_immutable(self):
        value = candidate("frozen")

        with self.assertRaises(FrozenInstanceError):
            value.title = "changed"


class PersonalizedRankingTests(unittest.TestCase):

    def setUp(self):
        self.profile = canonicalize_user_profile(
            base_profile()
        )

    def test_gabi_style_profile_prefers_machine_heavy_low_human_candidate(self):
        machine = candidate(
            "machine",
            ai_executability=95,
            human_burden=5,
            customer_dependency=0,
            sales_dependency=0,
            time_to_evidence_days=5,
            evidence_quality=85,
        )

        human = candidate(
            "human",
            ai_executability=45,
            human_burden=80,
            customer_dependency=90,
            sales_dependency=90,
            time_to_evidence_days=30,
            evidence_quality=85,
            requires_customer_work=True,
            requires_sales=True,
        )

        result = rank_candidates(
            self.profile,
            [human, machine],
        )

        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0].candidate_id, "machine")
        self.assertEqual(result[1].candidate_id, "human")
        self.assertGreater(result[0].score, result[1].score)

    def test_user_preferences_change_ranking_not_global_rules(self):
        human = candidate(
            "human-sales",
            ai_executability=70,
            human_burden=50,
            customer_dependency=75,
            sales_dependency=80,
            evidence_quality=90,
            requires_customer_work=True,
            requires_sales=True,
        )

        restricted = score_candidate(
            self.profile,
            human,
        )

        willing_raw = base_profile()
        willing_raw["willingness"]["work_with_customers"] = True
        willing_raw["willingness"]["sell"] = True

        willing = score_candidate(
            canonicalize_user_profile(willing_raw),
            human,
        )

        self.assertGreater(
            willing.score,
            restricted.score,
        )

    def test_ineligible_and_overbudget_are_hard_rejected(self):
        ineligible = candidate(
            "ineligible",
            applicant_feasibility="INELIGIBLE",
        )

        overbudget = candidate(
            "overbudget",
            capital_required="1",
        )

        a = score_candidate(
            self.profile,
            ineligible,
        )
        b = score_candidate(
            self.profile,
            overbudget,
        )

        self.assertTrue(a.hard_reject)
        self.assertTrue(b.hard_reject)
        self.assertIn(
            "APPLICANT_INELIGIBLE",
            a.reason_codes,
        )
        self.assertIn(
            "CAPITAL_EXCEEDS_MAX_SPEND",
            b.reason_codes,
        )

    def test_unknown_eligibility_is_not_optimistically_equal_to_eligible(self):
        eligible = candidate(
            "eligible",
            applicant_feasibility="ELIGIBLE",
        )

        unknown = candidate(
            "unknown",
            applicant_feasibility="UNKNOWN",
        )

        a = score_candidate(
            self.profile,
            eligible,
        )
        b = score_candidate(
            self.profile,
            unknown,
        )

        self.assertFalse(b.hard_reject)
        self.assertGreater(a.score, b.score)
        self.assertIn(
            "APPLICANT_FEASIBILITY_UNKNOWN",
            b.reason_codes,
        )

    def test_ranking_is_repeatable_and_nonmutating(self):
        candidates = [
            candidate("b"),
            candidate("a"),
        ]

        before_profile = copy.deepcopy(self.profile)
        before_candidates = tuple(candidates)

        first = rank_candidates(
            self.profile,
            candidates,
        )
        second = rank_candidates(
            self.profile,
            candidates,
        )

        self.assertEqual(first, second)
        self.assertEqual(self.profile, before_profile)
        self.assertEqual(tuple(candidates), before_candidates)


class OpportunitySynthesisTests(unittest.TestCase):

    def observation(self, **changes):
        values = {
            "observation_id": "obs-1",
            "observed_condition": (
                "A new machine-readable capability exists."
            ),
            "economic_mechanism": (
                "A buyer pays per successful automated unit."
            ),
            "value_source": "Existing buyer budget",
            "why_ai_changes_feasibility": (
                "AI reduces execution labor enough to test the mechanism."
            ),
            "assumptions": (
                "Demand remains available",
            ),
            "cheap_test": (
                "Run one bounded non-financial feasibility test."
            ),
            "evidence_required": (
                "Primary-source mechanism evidence",
                "Independent test result",
            ),
            "source_ids": (
                "source-observation-1",
            ),
            "mechanism_hint": "machine_api",
        }
        values.update(changes)
        return SynthesisObservation(**values)

    def test_valid_observation_becomes_synthesized_candidate(self):
        obs = self.observation()

        result = build_synthesized_candidate(
            obs,
            candidate_id="synth-001",
            title="Machine-readable opportunity hypothesis",
        )

        self.assertEqual(
            result.origin,
            CandidateOrigin.SYNTHESIZED,
        )
        self.assertEqual(
            result.value_source,
            "Existing buyer budget",
        )
        self.assertEqual(
            result.source_ids,
            ("source-observation-1",),
        )

        self.assertIsNone(result.ai_executability)
        self.assertIsNone(result.estimated_upside)
        self.assertIsNone(result.time_to_evidence_days)

    def test_synthesis_refuses_unsupported_brainstorming(self):
        bad = [
            {"value_source": ""},
            {"cheap_test": ""},
            {"source_ids": ()},
            {"evidence_required": ()},
            {"observed_condition": ""},
            {"why_ai_changes_feasibility": ""},
        ]

        for changes in bad:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    self.observation(**changes)


class StaticBoundaryTests(unittest.TestCase):

    def test_v3_foundation_has_no_network_cloud_or_process_imports(self):
        files = [
            "user_profile.py",
            "opportunity_candidate.py",
            "personalized_ranking.py",
            "opportunity_synthesis.py",
        ]

        forbidden_roots = {
            "requests",
            "httpx",
            "urllib",
            "socket",
            "subprocess",
            "google",
            "vertexai",
        }

        for name in files:
            path = (
                ROOT
                / "src"
                / "opportunity_operator"
                / name
            )

            self.assertTrue(
                path.is_file(),
                f"{name} missing",
            )

            tree = ast.parse(
                path.read_text(encoding="utf-8")
            )

            imported = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported.add(
                            alias.name.split(".")[0]
                        )

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported.add(
                            node.module.split(".")[0]
                        )

            self.assertFalse(
                imported & forbidden_roots,
                f"{name} imports forbidden runtime dependency: "
                f"{sorted(imported & forbidden_roots)}",
            )


if __name__ == "__main__":
    unittest.main()
