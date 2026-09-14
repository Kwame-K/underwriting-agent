# Underwriting Agent

A decision-support service for commercial insurance underwriting. It converts a validated submission, deterministic rules, risk scores, and cited underwriting knowledge into an explainable recommendation: **accept**, **refer**, or **decline**.

> The agent supports underwriters; it does not make an autonomous binding decision. Escalation and human approval remain mandatory where configured.

## Role in the agentic portfolio

This is **Project 4** and the decision authority of the insurance agent portfolio. It consumes structured information from upstream agents and produces a traceable underwriting recommendation.

| Upstream capability | Project | Relationship to this agent |
|---|---|---|
| Submission extraction | [Project 1 — insurance-submission-extractor](https://github.com/Kwame-K/insurance-submission-extractor) | Provides normalized application data and extraction-quality signals. |
| Data analysis | [Project 2 — insurance-data-analyst-agent](https://github.com/Kwame-K/insurance-data-analyst-agent) | Can provide analytical context and portfolio/risk signals. |
| Insurance knowledge retrieval | [Project 3 — insurance-rag-assistant](https://github.com/Kwame-K/insurance-rag-assistant) | Provides cited policy, appetite, and guideline evidence. |
| Multi-agent orchestration | [insurance-multi-agent-system](https://github.com/Kwame-K/insurance-multi-agent-system) | Coordinates the end-to-end workflow and audit context. |

## Decision flow

```text
Validated submission
       + risk signals
       + RAG evidence from Project 3
                |
                v
       Eligibility rules -> Risk scoring -> Decision policy
                |                 |                |
                +-----------------+----------------+
                                  v
                 Recommendation + rationale + confidence
                                  |
                    accept / refer / decline / review
                                  |
                           Human underwriter
```

## Core responsibilities

- Validate the completeness and consistency of an underwriting submission.
- Apply deterministic eligibility, referral, and decline rules.
- Combine permitted risk scores and analytical signals.
- Request insurance-guideline evidence from Project 3 when knowledge is required.
- Generate an explainable recommendation with evidence, rule outcomes, and assumptions separated.
- Escalate incomplete, conflicting, low-confidence, or policy-sensitive cases to human review.
- Persist auditable decision records.

## Architecture

The service follows layered boundaries:

```text
src/underwriting_agent/
  api/             # HTTP boundary and request/response validation
  application/     # Use cases and decision workflow
  domain/          # Business entities, decision states, invariants
  rules/           # Deterministic underwriting rules
  scoring/         # Risk score calculation and interpretation
  integrations/    # External clients, including the Project 3 RAG adapter
  infrastructure/  # Persistence, audit logs, configuration adapters
```

See [System architecture](docs/system-architecture.md) for component boundaries, data contracts, RAG integration, failure modes, and audit requirements.

## Project 3 integration

Project 3 is treated as an **external knowledge service**, not as a Python package imported into this repository. The intended integration is a versioned HTTP contract:

1. This agent sends a contextualized query: product, jurisdiction, coverage, risk facts, and question.
2. Project 3 retrieves relevant approved knowledge-base passages.
3. Project 3 returns evidence text, source metadata, retrieval confidence, and a request/correlation ID.
4. This agent records the evidence and uses it as decision support.
5. If evidence is unavailable, weak, or contradictory, the case is referred rather than automatically accepted or declined.

This approach keeps deployments independent and preserves clear ownership of the knowledge base.

## Current status

| Capability | Status |
|---|---|
| Domain, application, rules, scoring, API, and integration package boundaries | Present in the repository |
| Human review workflow | Implemented and validated as a standalone project capability |
| Project 3 RAG integration | Architecture and contract defined; runtime adapter implementation pending |
| End-to-end multi-agent orchestration | Owned by the integration repository; pending |

## Engineering standards

- Python 3.12 and `uv`
- Domain-driven, testable boundaries
- Deterministic rules before generative reasoning
- Explicit Pydantic contracts at API and integration boundaries
- Structured audit events with correlation IDs
- Synthetic or de-identified data only in development
- No credentials or client data committed to Git

## Next implementation increment

Implement `integrations/rag_client.py` and its contract tests against a mocked Project 3 response. The first accepted scenario should demonstrate a complete recommendation with: validated inputs, rule outcomes, risk score, cited evidence, confidence, and a human-review decision.
