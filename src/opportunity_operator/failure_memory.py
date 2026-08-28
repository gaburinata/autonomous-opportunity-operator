from __future__ import annotations

from decimal import Decimal
from typing import Protocol, Sequence

from .models import FailureMatch, FailureMemory, Opportunity


class FailureMatcher(Protocol):
    def match(self, opportunity: Opportunity, memories: Sequence[FailureMemory]) -> tuple[FailureMatch, ...]: ...


class DeterministicJaccardMatcher:
    def __init__(self, warning_threshold: Decimal = Decimal("0.50")) -> None:
        self.warning_threshold = warning_threshold

    def match(self, opportunity: Opportunity, memories: Sequence[FailureMemory]) -> tuple[FailureMatch, ...]:
        candidate = {term.strip().lower() for term in opportunity.similarity_signature if term.strip()}
        matches: list[FailureMatch] = []
        for memory in memories:
            prior = {term.strip().lower() for term in memory.similarity_signature if term.strip()}
            union = candidate | prior
            score = Decimal(len(candidate & prior)) / Decimal(len(union)) if union else Decimal("0")
            matches.append(FailureMatch(memory.memory_id, score, tuple(sorted(candidate & prior)),
                                        score >= self.warning_threshold))
        return tuple(sorted(matches, key=lambda item: (-item.score, item.memory_id)))

