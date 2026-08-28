# Autonomous Opportunity Operator — Architecture

## System objective

AOO converts the open-ended question:

> What can AI realistically build, operate, execute, exploit, pursue or prepare for this person?

into a bounded, evidence-backed decision workflow.

The architecture separates three kinds of authority:

1. Probabilistic intelligence — Gemini agents discover, verify and investigate.
2. Deterministic authority — explicit tools enforce eligibility, economics, failure memory and final safety.
3. Human authority — credentials, capital, identity, legal acceptance, deployment and consequential external action.

## End-to-end architecture

~~mermaid
flowchart LR
    subgraph UX["Product layer"]
        U["User profile"]
        HOME["Opportunity Inbox"]
        JC["Technical proof / judge console"]
        U --> HOME
    end

    subgraph ORCH["Google ADK orchestration"]
        A1["Discovery Agent"]
        A2["Primary Source Verification Agent"]
        A3["Deterministic Hard Gate Agent"]
        A4["Investigation Agent"]
        A5["Failure Memory Agent"]
        A6["Economic Evidence Agent"]
        A7["Final Adjudication Agent"]

        A1 --> A2 --> A3 --> A4 --> A5 --> A6 --> A7
    end

    subgraph AUTH["Deterministic authority"]
        G1["Eligibility / capital / deadline gate"]
        G2["Failure-memory similarity"]
        G3["Unit economics"]
        G4["Final evidence + safety adjudication"]
    end

    subgraph STATE["Authoritative state"]
        FS[("Cloud Firestore")]
        RP["Idempotent replay"]
        FS --> RP
    end

    HOME --> A1

    G1 --> A3
    G2 --> A5
    G3 --> A6
    G4 --> A7

    A7 --> FS

    RP --> HOME
    FS --> JC

    CR["Google Cloud Run"] --- HOME
    ADK["Google ADK"] --- ORCH
    GEM["Gemini 3.5 Flash"] --- ORCH
~~

## Decision flow

~~text
candidate
  |
  v
primary-source verification
  |
  v
deterministic feasibility gate
  |
  +---- fail ----------------------> KILL / WATCH
  |
  v
deeper investigation
  |
  v
failure-memory comparison
  |
  v
unit economics
  |
  v
final evidence + safety adjudication
  |
  v
PROMOTE / WATCH / KILL
  |
  v
Firestore persistence
  |
  v
authoritative replay
~~

## Why this is not a chatbot

AOO maintains an explicit workflow with:

- agent specialization
- primary-source verification
- typed state
- deterministic decision gates
- evidence provenance
- persistent authoritative outcomes
- replay semantics
- permission boundaries

The final outcome is not accepted merely because an LLM says it is correct.

## Public judge deployment

The public hackathon service exposes:

- homepage
- opportunity snapshot
- deterministic personalization
- health
- provenance
- judge console

It blocks anonymous POST requests to model-bearing and cost-bearing workflow routes.

The protected proof runtime retains the genuine Google ADK + Gemini + Firestore workflow used in the live proof-of-action demonstration.

## Failure philosophy

When evidence is malformed, authority is ambiguous, provenance is absent, or a dependency fails, AOO defaults to abstention or fail-closed behavior instead of manufacturing certainty.
