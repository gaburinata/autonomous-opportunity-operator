# Security Boundary

## Trust zones

1. Untrusted discovery inputs: opportunity descriptions, web content, files, and model output.
2. Validated domain data: normalized typed records that passed structural checks.
3. Evidence store: append-only provenance and adjudication records.
4. Execution adapters: narrowly scoped tools for tests or later external calls.
5. Human authority: accounts, capital, legal acceptance, identity, credentials, and deployment.

Untrusted text is data, never executable instruction. It cannot expand permissions or select credentials.

## Permission rules

- Offline core code has no network adapter and no credential dependency.
- Tools are deny-by-default and allow-listed by operation, target, and budget.
- Discovery/investigation agents cannot adjudicate their own economic evidence.
- Model output cannot bypass deterministic eligibility, capital, deadline, or cost gates.
- Secrets must come from a managed secret facility in later cloud work; never from logs, fixtures, prompts, or repository files.
- Capital movement, account creation/login, terms acceptance, legal representations, and production deployment require explicit human approval.
- Evidence events retain source identifiers and hashes; sensitive source payloads should remain outside general logs.
- On malformed evidence, ambiguous authority, missing provenance, or unavailable dependencies, the system abstains safely.

## Wave 0 boundary

Only local synthetic data and standard-library execution are allowed. There are no network calls, model calls, cloud mutations, account actions, or real-money actions.

