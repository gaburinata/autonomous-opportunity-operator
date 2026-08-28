from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from .economics import adjudicate_economics
from .failure_memory import DeterministicJaccardMatcher, FailureMatcher
from .gates import hard_gate
from .models import EconomicEvidenceDecision, EvidenceEvent, FailureMatch, FailureMemory, Opportunity, State
from .state_machine import transition


@dataclass(frozen=True)
class PipelineResult:
    opportunity: Opportunity
    final_state: State
    events: tuple[EvidenceEvent, ...]
    failure_matches: tuple[FailureMatch, ...]
    economic_decision: EconomicEvidenceDecision | None
    expensive_investigation_started: bool


class OpportunityPipeline:
    def __init__(self, memories: Sequence[FailureMemory] = (), matcher: FailureMatcher | None = None) -> None:
        self._memories = tuple(memories)
        self._matcher = matcher or DeterministicJaccardMatcher()

    def run(self, opportunity: Opportunity, now: datetime | None = None) -> PipelineResult:
        events: list[EvidenceEvent] = [EvidenceEvent.create(
            opportunity.opportunity_id, "DISCOVERED", "discoverer", opportunity.source_ids[0],
            {"title": opportunity.title, "all_source_ids": list(opportunity.source_ids)})]
        state = State.DISCOVERED
        state = transition(state, State.VERIFIED)
        events.append(EvidenceEvent.create(opportunity.opportunity_id, "PRIMARY_SOURCE_VERIFIED", "verifier",
                                           opportunity.source_ids[0], {"state": state.value}))

        gate = hard_gate(opportunity, now)
        events.append(EvidenceEvent.create(opportunity.opportunity_id, "HARD_GATE", "gatekeeper",
                                           "deterministic:hard_gate", {"passed": gate.passed,
                                           "reasons": list(gate.reason_codes)}))
        if gate.terminal_state is not None:
            state = transition(state, gate.terminal_state)
            events.append(EvidenceEvent.create(opportunity.opportunity_id, "TERMINAL_DECISION", "controller",
                                               "deterministic:hard_gate", {"state": state.value}))
            return PipelineResult(opportunity, state, tuple(events), (), None, False)

        matches = self._matcher.match(opportunity, self._memories)
        warnings = [m for m in matches if m.warning]
        events.append(EvidenceEvent.create(opportunity.opportunity_id, "FAILURE_MEMORY_MATCH", "failure_matcher",
                                           "failure-memory:v0", {"warning_memory_ids": [m.memory_id for m in warnings],
                                           "scores": {m.memory_id: str(m.score) for m in matches}}))
        state = transition(state, State.INVESTIGATING)
        events.append(EvidenceEvent.create(opportunity.opportunity_id, "INVESTIGATION_STARTED", "investigator",
                                           "synthetic:offline", {"state": state.value}))
        state = transition(state, State.TESTED)
        test_event = EvidenceEvent.create(opportunity.opportunity_id, "SYNTHETIC_TEST", "test_runner",
                                          "synthetic:offline", {"unit_economics_present": opportunity.unit_economics is not None})
        events.append(test_event)
        decision = adjudicate_economics(opportunity, (test_event.event_id,), bool(warnings))
        events.append(EvidenceEvent.create(opportunity.opportunity_id, "ECONOMIC_ADJUDICATION", "evidence_adjudicator",
                                           test_event.event_id, {"disposition": decision.disposition.value,
                                           "reasons": list(decision.reason_codes), "abstained": decision.abstained}))
        state = transition(state, decision.disposition)
        events.append(EvidenceEvent.create(opportunity.opportunity_id, "TERMINAL_DECISION", "controller",
                                           "economic-adjudication:v0", {"state": state.value}))
        return PipelineResult(opportunity, state, tuple(events), matches, decision, True)

