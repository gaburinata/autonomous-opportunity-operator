"""Bounded Google ADK executor for the proof workflow."""

from collections.abc import Mapping
import asyncio
from concurrent.futures import ThreadPoolExecutor
import copy
import inspect
import json

from .agent import root_agent


_AGENTS = (
    "discovery_agent", "primary_source_verification_agent",
    "deterministic_hard_gate_agent", "investigation_agent",
    "failure_memory_agent", "economic_evidence_agent",
    "final_adjudication_agent",
)
_TOOLS = (
    "eligibility_capital_deadline_gate", "failure_memory_similarity_check",
    "calculate_unit_economics", "final_evidence_safety_adjudication",
)
_TERMINAL = {"PROMOTE", "WATCH", "KILL", "DECISION_REQUIRED"}


def _collect(value):
    if not inspect.isawaitable(value) and not hasattr(value, "__aiter__"):
        return list(value)

    async def collect_async(source):
        if inspect.isawaitable(source):
            source = await source
        if hasattr(source, "__aiter__"):
            return [item async for item in source]
        return list(source)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(collect_async(value))
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, collect_async(value)).result()


class CloudAdkExecutor:
    def __init__(self, *, workflow=None):
        self._workflow = workflow
        self._loaded = False
        self._stream = []
        self._runs = 0
        self._agents_seen = []
        self._tools_called = []
        self._workflow_error_phase = None
        self._workflow_error_type = None
        self._raw_stream_items_seen = 0

    def _production_workflow(self, event):
        from google.adk.runners import InMemoryRunner

        runner = InMemoryRunner(agent=root_agent, app_name="aoo-proof")

        async def run():
            payload = event.get("payload")
            if not isinstance(payload, Mapping):
                payload = {}

            profile = payload.get("decision_profile")
            if not isinstance(profile, Mapping):
                profile = {}

            source_text = payload.get("source_text")
            if not isinstance(source_text, str) or not source_text:
                source_text = json.dumps(
                    payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    default=str,
                )

            decision_profile_json = json.dumps(
                dict(profile),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )

            initial_state = {
                "source_text": source_text,
                "decision_profile_json": decision_profile_json,
                "source_url": str(payload.get("source_url") or ""),
                "final_url": str(payload.get("final_url") or ""),
                "source_sha256": str(payload.get("source_sha256") or ""),
                "text_sha256": str(payload.get("text_sha256") or ""),
                "text_length": str(payload.get("text_length") or ""),
                "opportunity_id": str(event.get("opportunity_id") or ""),
                "decision_event_id": str(event.get("event_id") or ""),
            }

            session = await runner.session_service.create_session(
                app_name="aoo-proof",
                user_id="proof",
                session_id=event["event_id"],
                state=initial_state,
            )

            from google.genai import types

            message = types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=(
                            "Execute the AOO decision workflow using "
                            "authoritative session state. "
                            f"event_id={event['event_id']} "
                            f"opportunity_id={event['opportunity_id']}"
                        )
                    )
                ],
            )
            return [item async for item in runner.run_async(
                user_id="proof", session_id=session.id, new_message=message
            )]
        return run()

    def _normalize(self, item):
        if isinstance(item, Mapping):
            return copy.deepcopy(dict(item))
        result = {"author": getattr(item, "author", "")}
        content = getattr(item, "content", None)
        for part in getattr(content, "parts", ()) or ():
            text = getattr(part, "text", None)
            call = getattr(part, "function_call", None)
            response = getattr(part, "function_response", None)
            if isinstance(text, str) and text:
                result["text"] = result.get("text", "") + text
            if call is not None:
                result["tool_call"] = {"name": call.name, "arguments": dict(call.args or {})}
            if response is not None:
                result["tool_result"] = {"name": response.name, "result": copy.deepcopy(response.response)}
        return result

    def _load(self, event):
        if self._loaded:
            return
        self._loaded = True
        self._runs = 1
        try:
            source = self._workflow(copy.deepcopy(dict(event))) if self._workflow else self._production_workflow(copy.deepcopy(dict(event)))
            raw_items = _collect(source)
            self._raw_stream_items_seen = len(raw_items)
        except Exception as exc:
            self._workflow_error_phase = "WORKFLOW"
            self._workflow_error_type = type(exc).__name__
            self._stream = []
        else:
            try:
                self._stream = [
                    self._normalize(item)
                    for item in raw_items
                ]
            except Exception as exc:
                self._workflow_error_phase = "NORMALIZATION"
                self._workflow_error_type = type(exc).__name__
                self._stream = []
        for item in self._stream:
            author = item.get("author")
            if (author in _AGENTS and isinstance(item.get("text"), str)
                    and item["text"] and author not in self._agents_seen):
                self._agents_seen.append(author)
            call = item.get("tool_call")
            if (isinstance(call, Mapping) and call.get("name") in _TOOLS
                    and isinstance(call.get("arguments"), Mapping)
                    and call["name"] not in self._tools_called):
                self._tools_called.append(call["name"])

    def execute(self, stage, event, prior_results):
        del prior_results
        self._load(event)
        if stage != "FINAL_ADJUDICATION":
            observed_tool_result = any(
                isinstance(item.get("tool_result"), Mapping)
                and item["tool_result"].get("name") in _TOOLS
                and "result" in item["tool_result"]
                for item in self._stream
            )
            if not (self._agents_seen or self._tools_called or observed_tool_result):
                return {
                    "status": "TERMINAL",
                    "disposition": "KILL",
                    "reason_codes": ["MISSING_ADK_WORKFLOW_EVIDENCE"],
                }
            return {"status": "CONTINUE", "reason_codes": ["ADK_EVIDENCE_OBSERVED"]}
        finals = []
        for item in self._stream:
            result = item.get("tool_result")
            if isinstance(result, Mapping) and result.get("name") == "final_evidence_safety_adjudication":
                finals.append(result.get("result"))
        if len(finals) == 1 and isinstance(finals[0], Mapping):
            disposition = finals[0].get("disposition")
            reasons = finals[0].get("reason_codes")
            if disposition in _TERMINAL and isinstance(reasons, list) and reasons and all(isinstance(x, str) and x for x in reasons):
                return {"status": "TERMINAL", "disposition": disposition, "reason_codes": copy.deepcopy(reasons)}
        return {"status": "TERMINAL", "disposition": "KILL", "reason_codes": ["INVALID_AUTHORITATIVE_FINAL_EVIDENCE"]}

    def runtime_evidence(self):
        observed_tool_result = any(
            isinstance(item.get("tool_result"), Mapping)
            and item["tool_result"].get("name") in _TOOLS
            and "result" in item["tool_result"]
            for item in self._stream
        )

        if self._workflow_error_phase == "WORKFLOW":
            workflow_state = "WORKFLOW_EXCEPTION"
        elif self._workflow_error_phase == "NORMALIZATION":
            workflow_state = "NORMALIZATION_EXCEPTION"
        elif self._raw_stream_items_seen == 0:
            workflow_state = "EMPTY_STREAM"
        elif (
            self._agents_seen
            or self._tools_called
            or observed_tool_result
        ):
            workflow_state = "EVIDENCE_OBSERVED"
        else:
            workflow_state = "UNRECOGNIZED_STREAM"

        return copy.deepcopy({
            "adk_workflow_runs": self._runs,
            "agents_seen": self._agents_seen,
            "tools_called": self._tools_called,
            "workflow_state": workflow_state,
            "workflow_error_phase": self._workflow_error_phase,
            "workflow_error_type": self._workflow_error_type,
            "raw_stream_items_seen": self._raw_stream_items_seen,
            "normalized_stream_items_seen": len(self._stream),
        })
