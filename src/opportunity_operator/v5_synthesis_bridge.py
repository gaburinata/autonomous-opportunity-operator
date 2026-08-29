"""V5 person-profile bridge to the existing evidence-backed synthesis runtime.

This module does not call a model itself.

It:
1. validates/canonicalizes the V5 economic profile,
2. adapts it to the frozen V3 synthesis profile contract,
3. adds V5-specific latent-opportunity search policy,
4. reuses the existing synthesis prompt, schema, validation and
   OpportunityCandidate construction.

No economic fact is invented here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .public_v5_operator import (
    canonicalize_v5_profile,
)
from .synthesis_runtime import (
    build_synthesis_prompt,
    execute_evidence_backed_synthesis,
)


_LATENT_BASE_FAMILIES = (
    "niche SaaS or subscription software",
    "standalone app or focused software tool",
    "API or machine-to-machine service",
    "automation system or automation-led business",
    "data product, dataset, monitoring product or intelligence service",
    "licensable software, workflow or digital asset",
)


_EXCLUSION_LABELS = {
    "competitions":
        "posted competitions and hackathons",

    "grants":
        "grants and funding calls",

    "financial_trading":
        "investment, trading and financial mechanisms",

    "customer_work":
        "customer-facing or client-service work",

    "selling_content":
        "sales-dependent or content-dependent work",
}


def to_v3_synthesis_profile(
    profile: object,
) -> dict[str, object]:
    """Adapt V5 profile to the frozen synthesis profile without losing context."""

    canonical = canonicalize_v5_profile(
        profile
    )

    exclusions = set(
        canonical["exclusions"]
    )

    residence = str(
        canonical[
            "residence_country"
        ]
    )

    citizenships = [
        str(value)
        for value in canonical[
            "citizenships"
        ]
    ]

    currency = str(
        canonical["currency"]
    )

    constraints = [
        (
            "Residence jurisdiction: "
            + residence
            + ". Eligibility must be checked against residence, "
              "not merely used as a search keyword."
        ),
        (
            "Citizenship(s): "
            + ", ".join(citizenships)
            + ". Citizenship restrictions are separate from residence."
        ),
        (
            "All profile monetary amounts are denominated in "
            + currency
            + ". Never silently reinterpret them as USD, EUR, or "
              "another currency."
        ),
        (
            "Traditional employment where the human remains the "
            "primary worker is outside the target opportunity scope."
        ),
        (
            "Prefer opportunities where AI can perform most or all "
            "research, construction, testing, preparation, operation "
            "or repeated delivery."
        ),
    ]

    for exclusion in sorted(
        exclusions
    ):
        label = _EXCLUSION_LABELS[
            exclusion
        ]

        constraints.append(
            "User exclusion: do not pursue "
            + label
            + "."
        )

    skills_assets = [
        str(value)
        for value in canonical[
            "skills_assets"
        ]
    ]

    willing_customer = (
        "customer_work"
        not in exclusions
    )

    willing_selling = (
        "selling_content"
        not in exclusions
    )

    willing_finance = (
        "financial_trading"
        not in exclusions
    )

    willing_contests = (
        "competitions"
        not in exclusions
    )

    return {
        "goal":
            canonical["goal"],

        "country":
            residence,

        "available_capital":
            canonical[
                "available_money"
            ],

        "max_cash_spend":
            canonical[
                "max_cash_spend_or_risk"
            ],

        "human_hours_per_week":
            canonical[
                "human_hours_per_week"
            ],

        # V5's product thesis is maximum useful AI autonomy,
        # subject to deterministic/human consequential-action gates.
        "ai_autonomy":
            "maximum",

        "willingness": {
            "build_business":
                True,

            "work_with_customers":
                willing_customer,

            "sell":
                willing_selling,

            "publish_content":
                willing_selling,

            "invest_capital":
                willing_finance,

            "contests_juries":
                willing_contests,

            "financial_protocols":
                willing_finance,
        },

        "skills_assets":
            skills_assets,

        "constraints":
            constraints,
    }


def permitted_latent_families(
    profile: object,
) -> tuple[str, ...]:
    """Return machine-heavy mechanism families permitted by V5 exclusions."""

    canonical = canonicalize_v5_profile(
        profile
    )

    exclusions = set(
        canonical["exclusions"]
    )

    families = list(
        _LATENT_BASE_FAMILIES
    )

    if (
        "financial_trading"
        not in exclusions
    ):
        families.extend(
            (
                "systematic trading or market-neutral trading mechanism",
                "arbitrage, market-structure or pricing-dislocation system",
                "other bounded financial mechanism where AI materially changes feasibility",
            )
        )

    if (
        "customer_work"
        not in exclusions
    ):
        families.append(
            "AI-operated service business with bounded human involvement"
        )

    if (
        "selling_content"
        not in exclusions
    ):
        families.extend(
            (
                "AI-operated distribution or sales mechanism",
                "AI-produced monetizable information/content asset",
            )
        )

    return tuple(families)


def build_v5_synthesis_policy(
    profile: object,
) -> str:
    """Create deterministic V5 latent-opportunity policy for model prompting."""

    canonical = canonicalize_v5_profile(
        profile
    )

    families = permitted_latent_families(
        canonical
    )

    exclusions = set(
        canonical["exclusions"]
    )

    lines = [
        "V5 LATENT OPPORTUNITY POLICY",
        "",
        "MISSION:",
        (
            "Find specific economic opportunities this person's AI system "
            "could BUILD, OPERATE, TEST, PREPARE, OR PURSUE with AI doing "
            "most or all of the repeatable work."
        ),
        "",
        "THIS IS NOT A GENERIC IDEA-BRAINSTORMING TASK.",
        (
            "Every proposed opportunity must be grounded in the supplied "
            "evidence and must identify an economic mechanism, value source, "
            "why AI changes feasibility, a cheap falsifiable test, and what "
            "evidence remains required."
        ),
        "",
        "DO NOT DEFAULT TO 'BUILD AN APP'.",
        (
            "Compare materially different economic mechanisms. A SaaS, "
            "automation, API, data product, trading system, service mechanism "
            "or other machine-heavy opportunity may win. No category has a "
            "preferred status."
        ),
        "",
        "PERMITTED LATENT MECHANISM FAMILIES:",
    ]

    for family in families:
        lines.append(
            "- " + family
        )

    lines.extend(
        (
            "",
            "EXTERNAL VS LATENT:",
            (
                "Posted grants, competitions and bounties are primarily "
                "handled by external discovery. Latent synthesis should add "
                "opportunities that can be CREATED or OPERATED, not merely "
                "repeat the external feed."
            ),
            "",
            "PERSON-SPECIFIC CONSTRAINTS:",
            (
                "Residence: "
                + str(
                    canonical[
                        "residence_country"
                    ]
                )
            ),
            (
                "Citizenship(s): "
                + ", ".join(
                    str(value)
                    for value in canonical[
                        "citizenships"
                    ]
                )
            ),
            (
                "Capital currency: "
                + str(
                    canonical[
                        "currency"
                    ]
                )
            ),
            (
                "Available money: "
                + str(
                    canonical[
                        "available_money"
                    ]
                )
                + " "
                + str(
                    canonical[
                        "currency"
                    ]
                )
            ),
            (
                "Maximum spend/risk: "
                + str(
                    canonical[
                        "max_cash_spend_or_risk"
                    ]
                )
                + " "
                + str(
                    canonical[
                        "currency"
                    ]
                )
            ),
            (
                "Human hours/week: "
                + str(
                    canonical[
                        "human_hours_per_week"
                    ]
                )
            ),
        )
    )

    if exclusions:
        lines.append(
            "Explicit exclusions:"
        )

        for exclusion in sorted(
            exclusions
        ):
            lines.append(
                "- "
                + _EXCLUSION_LABELS[
                    exclusion
                ]
            )
    else:
        lines.append(
            "Explicit exclusions: none beyond legality, safety and evidence gates."
        )

    lines.extend(
        (
            "",
            "QUALITY BAR:",
            (
                "Prefer a small number of testable, economically distinct "
                "opportunities over many cosmetic variants of one idea."
            ),
            (
                "Do not claim revenue, eligibility, capital requirement, "
                "AI executability, human workload, loss, demand or upside "
                "unless supported by evidence. Unknown must remain unknown."
            ),
            (
                "Traditional jobs where the person remains the primary "
                "worker are outside this synthesis scope."
            ),
        )
    )

    return "\n".join(lines)


def build_v5_synthesis_prompt(
    profile: object,
    evidence_items: object,
) -> str:
    """Build the existing synthesis prompt plus the V5 economic scope."""

    legacy = to_v3_synthesis_profile(
        profile
    )

    base = build_synthesis_prompt(
        legacy,
        evidence_items,
    )

    policy = build_v5_synthesis_policy(
        profile
    )

    return (
        base
        + "\n\n"
        + policy
    )


def execute_v5_evidence_backed_synthesis(
    profile: object,
    evidence_items: object,
    executor: Callable[
        [str, dict[str, Any]],
        object,
    ],
) -> dict[str, object]:
    """Run V5 through the existing synthesis validator/candidate builder.

    The wrapper injects only V5 search policy. The original synthesis
    runtime remains authoritative for schema validation, provenance,
    candidate construction and fail-closed behavior.
    """

    legacy = to_v3_synthesis_profile(
        profile
    )

    policy = build_v5_synthesis_policy(
        profile
    )

    def scoped_executor(
        prompt: str,
        schema: dict[str, Any],
    ) -> object:

        return executor(
            prompt
            + "\n\n"
            + policy,
            schema,
        )

    return execute_evidence_backed_synthesis(
        legacy,
        evidence_items,
        scoped_executor,
    )


__all__ = [
    "build_v5_synthesis_policy",
    "build_v5_synthesis_prompt",
    "execute_v5_evidence_backed_synthesis",
    "permitted_latent_families",
    "to_v3_synthesis_profile",
]
