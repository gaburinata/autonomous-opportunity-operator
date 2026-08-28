# Google ADK Architecture V1

`opportunity_operator.agent` exports a genuine Google ADK `SequentialAgent` named `root_agent`.
Its seven model-bearing `LlmAgent` stages are discovery, primary-source verification,
deterministic hard gate, investigation, failure memory, economic evidence, and final
adjudication. Every model is configured as `gemini-3.5-flash`; configuration and import do
not make a model call.

The deterministic boundary lives in `adk_tools.py`. Native Python callables are registered
as ADK function tools. Gate and final-adjudication outputs are authoritative: ineligibility,
expired deadlines, prohibited/safety conditions, non-positive margins, and guarded actions
cannot be promoted by narrative reasoning. The Wave-0 `OpportunityPipeline` remains the
offline executable reference path.

No execution agent exists. Spending, registration, declarations, wallet activity, trading,
cloud creation, and submission require `DECISION_REQUIRED`.
