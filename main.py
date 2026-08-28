"""Private FastAPI proof surface for the Google-native vertical slice."""

import hashlib
import os
from collections.abc import Mapping
from decimal import Decimal

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, StrictStr, field_validator

from opportunity_operator.cloud_vertical_slice import CloudAdkExecutor
from opportunity_operator.firestore_workflow_store import FirestoreWorkflowStore
from opportunity_operator.workflow_coordinator import coordinate_opportunity_event
from opportunity_operator.primary_source_intake import build_discovered_event, ingest_primary_source
from opportunity_operator.real_source_decision import execute_primary_source_decision
from opportunity_operator.judge_console import render_judge_console
from opportunity_operator.opportunity_feed import load_opportunity_feed
from opportunity_operator.opportunity_candidate import CandidateOrigin, OpportunityCandidate
from opportunity_operator.discovery import run_live_discovery
from opportunity_operator.product_home import render_product_home
from opportunity_operator.product_integration import build_product_view
from opportunity_operator.synthesis_runtime import (
    canonicalize_evidence_items, execute_evidence_backed_synthesis,
)
from opportunity_operator.user_profile import canonicalize_user_profile


class ProofRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    wave_id: StrictStr

    @field_validator("wave_id")
    @classmethod
    def valid_wave_id(cls, value):
        import re
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9_-]{0,62}[A-Za-z0-9])?", value, re.ASCII):
            raise ValueError("invalid wave_id")
        return value


class PrimarySourceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_url: StrictStr
    opportunity_id: StrictStr

    @field_validator("source_url", "opportunity_id")
    @classmethod
    def non_empty(cls, value):
        if not value:
            raise ValueError("must not be empty")
        return value


class DecisionProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operator_jurisdiction: StrictStr
    available_capital: StrictStr
    max_cash_spend: StrictStr
    max_human_hours: StrictStr
    objective: StrictStr


class PrimarySourceDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_url: StrictStr
    opportunity_id: StrictStr
    decision_profile: DecisionProfileRequest


def _event(wave_id, human=False):
    digest = hashlib.sha256(wave_id.encode("ascii")).hexdigest()
    event = {
        "event_id": "proof-event-" + digest,
        "event_type": "opportunity.discovered",
        "opportunity_id": "proof-opportunity-" + digest,
        "payload": {"wave_id": wave_id, "revenue": "0.01", "variable_cost": "0.20"},
    }
    if human:
        event["action_class"] = "EXTERNAL_SUBMISSION"
    return event


def create_app(*, store_factory=None, executor_factory=None, environ=None,
               primary_source_ingestor=None, synthesis_executor_factory=None):
    env = os.environ if environ is None else environ
    database = env.get("AOO_FIRESTORE_DATABASE", "(default)")
    collection = env.get("AOO_FIRESTORE_COLLECTION", "aoo_workflows")
    if store_factory is None:
        store_factory = lambda: FirestoreWorkflowStore(collection=collection, database=database)
    if executor_factory is None:
        executor_factory = CloudAdkExecutor
    if primary_source_ingestor is None:
        primary_source_ingestor = ingest_primary_source
    service = FastAPI()

    @service.get("/", response_class=HTMLResponse)
    def product_home():
        return HTMLResponse(
            content=render_product_home(
                load_opportunity_feed()
            )
        )

    @service.get("/judge-console", response_class=HTMLResponse)
    async def judge_console():
        return HTMLResponse(
            render_judge_console()
        )

    @service.post("/discover/refresh")
    def discover_refresh(payload: dict):
        search_terms = str(
            payload.get(
                "search_terms",
                "",
            )
        )

        try:
            return run_live_discovery(
                search_terms
            )

        except ValueError as exc:
            return {
                "status": "INVALID",
                "reason_codes": [
                    "INVALID_SEARCH_TERMS"
                ],
                "detail": type(exc).__name__,
                "shortlist_count": 0,
                "items": [],
            }

    @service.get("/opportunities")
    def opportunities():
        return load_opportunity_feed()

    @service.post("/opportunities/personalized")
    async def personalized_opportunities(payload: dict):
        try:
            return build_product_view(payload, load_opportunity_feed())
        except (TypeError, ValueError, ArithmeticError):
            return {
                "status": "INVALID",
                "reason_codes": ["INVALID_USER_PROFILE"],
            }

    @service.post("/opportunities/synthesize")
    async def synthesize_opportunities(payload: dict):
        try:
            if not isinstance(payload, Mapping) or set(payload) != {"profile", "evidence_items"}:
                raise ValueError("invalid synthesis request")
            canonicalize_user_profile(payload["profile"])
            canonicalize_evidence_items(payload["evidence_items"])
        except (TypeError, ValueError, KeyError, ArithmeticError):
            return {"status": "INVALID", "reason_codes": ["INVALID_SYNTHESIS_REQUEST"],
                    "candidates": [], "evidence_source_ids": []}
        if synthesis_executor_factory is None:
            return {"status": "DECISION_REQUIRED",
                    "reason_codes": ["SYNTHESIS_EXECUTOR_NOT_CONFIGURED"],
                    "candidates": [], "evidence_source_ids": []}
        try:
            executor = synthesis_executor_factory()
        except Exception:
            return {"status": "FAIL_CLOSED", "reason_codes": ["SYNTHESIS_EXECUTOR_FAILED"],
                    "candidates": [], "evidence_source_ids": []}
        synthesis = execute_evidence_backed_synthesis(
            payload["profile"], payload["evidence_items"], executor
        )
        if synthesis["status"] != "PASS":
            return synthesis
        trusted_candidates = [
            OpportunityCandidate(
                **{
                    **candidate,
                    "origin": CandidateOrigin(candidate["origin"]),
                    "source_ids": tuple(candidate["source_ids"]),
                    **{
                        name: (Decimal(candidate[name]) if candidate[name] is not None else None)
                        for name in (
                            "capital_required", "estimated_human_hours",
                            "estimated_upside", "max_loss",
                        )
                    },
                }
            )
            for candidate in synthesis["candidates"]
        ]
        product_view = build_product_view(
            payload["profile"], {"items": []}, trusted_candidates
        )
        return {**synthesis, "product_view": product_view}

    @service.get("/health")
    async def health():
        return {"status": "ok", "proof_mode": True}

    @service.get("/provenance")
    async def provenance():
        return {"source_sha256": env.get("AOO_SOURCE_SHA256"), "model_id": env.get("AOO_MODEL_ID"), "revision": env.get("K_REVISION"), "firestore_database": database, "firestore_collection": collection}

    def run(request, scenario, human=False):
        executor = executor_factory()
        outcome = coordinate_opportunity_event(_event(request.wave_id, human), store_factory(), executor)
        return {"scenario": scenario, "outcome": outcome, "runtime_evidence": executor.runtime_evidence()}

    @service.post("/proof/discovered")
    async def discovered(request: ProofRequest):
        return run(request, "discovered")

    @service.post("/proof/human-gate")
    async def human_gate(request: ProofRequest):
        return run(request, "human-gate", True)

    @service.post("/intake/primary-source")
    async def primary_source(request: PrimarySourceRequest):
        try:
            document = primary_source_ingestor(request.source_url)
        except Exception:
            document = {"status": "FAIL_CLOSED", "reason_codes": ["SOURCE_FETCH_FAILED"]}
        if not isinstance(document, Mapping) or document.get("status") != "PASS":
            return {
                "scenario": "primary-source-intake",
                "status": "FAIL_CLOSED",
                "reason_codes": (document.get("reason_codes", ["SOURCE_FETCH_FAILED"])
                                 if isinstance(document, Mapping) else ["SOURCE_FETCH_FAILED"]),
            }
        try:
            event = build_discovered_event(document, request.opportunity_id)
        except (TypeError, ValueError, KeyError):
            return {"scenario": "primary-source-intake", "status": "FAIL_CLOSED", "reason_codes": ["INVALID_INTAKE_DOCUMENT"]}
        payload = event["payload"]
        return {
            "scenario": "primary-source-intake", "status": "PASS",
            "reason_codes": document["reason_codes"], "event_id": event["event_id"],
            "opportunity_id": event["opportunity_id"], "source_url": payload["source_url"],
            "final_url": payload["final_url"], "content_type": payload["content_type"],
            "byte_length": payload["byte_length"], "source_sha256": payload["source_sha256"],
            "text_length": payload["text_length"], "text_sha256": payload["text_sha256"],
        }

    @service.post("/decision/primary-source")
    async def primary_source_decision(request: PrimarySourceDecisionRequest):
        return execute_primary_source_decision(
            request.source_url,
            request.opportunity_id,
            request.decision_profile.model_dump(),
            store_factory=store_factory,
            executor_factory=executor_factory,
            ingestor=primary_source_ingestor,
        )

    return service


app = create_app()
