# Cost Guardrails

Wave 0 has a hard zero-cloud-spend boundary: no API enablement, resource creation, deployment, or paid model calls.

For a later cloud smoke test:

- Require an explicit operator-approved project ID and billing context.
- Default to local emulators and synthetic fixtures.
- Use request, token, concurrency, retry, and wall-clock caps per workflow.
- Apply deterministic gates and failure-memory matching before any model call.
- Permit only allow-listed model names, regions, and services.
- Disable automatic retries for non-idempotent or cost-bearing actions; bound all other retries.
- Attach correlation IDs and cost-attribution labels to every cloud operation.
- Enforce daily and per-opportunity budgets in application logic; configure Cloud Billing budgets as alerts, not as a sole hard-stop mechanism.
- Stop work when telemetry is missing, estimates exceed limits, or adjudication abstains.
- Keep Pub/Sub out of the initial deployment unless measured load or reliability needs justify it.

No agent may increase a budget, enable billing, or create a billable resource. Those are human approval actions.

