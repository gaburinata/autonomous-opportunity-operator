# ADK Tool Contracts V1

- `eligibility_capital_deadline_gate`: JSON scalars in; `passed`, `disposition`, and stable reason codes out. Malformed gate input fails closed.
- `calculate_unit_economics`: decimal strings and evidence IDs in; exact decimal strings, disposition, and reason codes out. Margin at or below zero is `KILL`.
- `failure_memory_similarity_check`: candidate signature and external records in; validated Jaccard matches plus explicit rejected-record entries out. Evidence requires source identity and digest.
- `final_evidence_safety_adjudication`: prior deterministic results and provenance in; one disposition, reason codes, sequence, source, evidence IDs, and stable SHA-256 digest out.

Precedence is hard-gate `KILL`/`DECISION_REQUIRED`, economic `KILL`, failure warning
`WATCH`, then the evidence disposition. Tools are pure, offline, JSON-compatible, and have
no authority to execute external actions.
