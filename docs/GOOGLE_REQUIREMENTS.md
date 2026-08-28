# Google and Contest Requirements

Contest facts were checked against the official Devpost overview, rules, and FAQ. Submission-facing requirements were rechecked during finalization on 2026-08-28.

## Supported facts

- Contest period: 2026-08-03 through 2026-08-31.
- Submission deadline: 2026-08-31 at 5:00 PM Pacific Time.
- Solo entries are permitted.
- Projects must be newly created during the submission period.
- Standard libraries, frameworks, starter templates, and AI coding assistants may be used; other incorporated pre-existing work must be disclosed.
- The project must use Gemini 3.5 or newer through the Gemini API or Vertex AI. The build page specifically frames Gemini 3.5 Flash as the target.
- The project must use at least one Google agent framework: Google ADK, GenAI SDK, Antigravity SDK, or GenKit.
- The project must use at least one Google Cloud infrastructure service.
- Proof of deployment on Google Cloud is required, though continuous hosting is not.
- Taskmaster is the current architectural track choice, subject to later review.

## Wave 0 status

Wave 0 is deliberately offline. It uses no Gemini model, Google agent framework, or Google Cloud service and creates no deployment proof. Therefore it is a fresh implementation foundation, **not a contest-compliant submission yet**.

## Intended later mapping (not yet implemented)

| Requirement | Intended implementation | Current status |
|---|---|---|
| Gemini 3.5+ | Gemini 3.5 Flash through Vertex AI | Not implemented |
| Agent framework | Google ADK orchestration | Not installed or implemented |
| Cloud infrastructure | Cloud Run service plus Firestore persistence | Not provisioned or deployed |
| Deployment proof | Timestamped Cloud Run revision evidence | Not available |
| Disclosure | `PREEXISTING_ASSET_DISCLOSURE.md` | Implemented for Wave 0 |

Requirements must be re-verified against the official contest pages before submission.

