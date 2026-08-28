# Authoritative State Design V1

## Trust boundary

Google ADK injects `ToolContext` into native tool calls. ADK omits that
parameter from the LLM-visible function declaration. The operator uses its
invocation-scoped `temp:` state for authoritative deterministic results:

| State key | Sole writer |
|---|---|
| `temp:aoo_gate_result` | `eligibility_capital_deadline_gate` |
| `temp:aoo_economics_result` | `calculate_unit_economics` |
| `temp:aoo_failure_result` | `failure_memory_similarity_check` |

Each writer stores the same dictionary object it returns, including all early
error and fail-closed paths. No LLM-produced summary is authoritative.

`final_evidence_safety_adjudication` has only provenance/event inputs in its
LLM-visible schema. It receives injected `ToolContext`, loads all three state
values, and validates their required shape, disposition domain, and reason-code
list before adjudicating.

## Fail-closed rules

A missing state value produces `KILL` with its specific
`MISSING_AUTHORITATIVE_*_RESULT` reason. A present but malformed value produces
`KILL` with `INVALID_AUTHORITATIVE_STATE`. Missing facts are never inferred.

For valid state, precedence is fixed:

1. gate `KILL` or `DECISION_REQUIRED`;
2. economics `KILL`;
3. known-failure warning as `WATCH`;
4. economics `WATCH`;
5. economics `PROMOTE`.

The selected authoritative reason codes are copied unchanged into the final
event and covered by its stable digest.

## Economic parsing

Revenue and variable cost are parsed and checked for finiteness before
confidence. Their margin is computed next. A non-positive margin always yields
`KILL / NON_POSITIVE_UNIT_MARGIN`, even when confidence is a qualitative label.
Confidence is parsed only for positive-margin promotion. Missing, non-finite,
or malformed positive-margin confidence yields
`WATCH / MALFORMED_OR_MISSING_CONFIDENCE`. Decimal outputs remain JSON strings.

## Test boundary

Direct tests use a lightweight context with `state` and `function_call_id`.
They also build the real ADK `FunctionTool` declaration to prove injected
context and intermediate result dictionaries are absent from the model schema.
Topology/import tests instantiate the genuine seven-agent ADK graph while
patching the model method to ensure zero live calls.
