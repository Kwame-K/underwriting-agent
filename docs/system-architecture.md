# System Architecture — Underwriting Agent

## Purpose

The Underwriting Agent is Project 4 of the insurance agent portfolio. It is the controlled decision-support layer: it evaluates a normalized submission against deterministic underwriting policy, risk signals, and retrieved insurance knowledge. It produces a recommendation for an authorized human underwriter.

## System context

```text
                         +--------------------------------+
                         | Project 1                       |
                         | Submission Extractor            |
                         +---------------+----------------+
                                         |
                             normalized submission
                                         v
+----------------------+    +------------------------------+    +----------------------+
| Project 2            |--->| Project 4: Underwriting Agent|<---| Project 3            |
| Data Analyst Agent   |    |                              |    | Insurance RAG        |
| risk/data signals    |    | rules + scoring + decision   |    | cited knowledge      |
+----------------------+    +---------------+--------------+    +----------------------+
                                            |
                              recommendation + audit record
                                            v
                              +----------------------------+
                              | Human Underwriter           |
                              | approve / amend / decline   |
                              +----------------------------+
```

The future `insurance-multi-agent-system` repository can orchestrate these calls. This repository remains independently deployable and owns underwriting decision logic.

## Component model

```text
API / CLI
  |
  v
Application workflow
  |---- Submission validator
  |---- Eligibility and referral rules
  |---- Risk scoring service
  |---- RAG integration client (Project 3)
  |---- Decision policy and explanation builder
  |---- Human review router
  |---- Audit-event publisher
  v
Infrastructure adapters
  |---- Configuration
  |---- Persistence / JSON audit store
  |---- HTTP clients
  |---- Observability
```

### Domain layer

The domain layer contains business concepts and must not depend on HTTP frameworks, LLM providers, or database implementations. Typical entities include `Submission`, `RiskSignal`, `KnowledgeEvidence`, `UnderwritingRecommendation`, `ReviewRequest`, and `AuditEvent`.

### Application layer

The application layer owns the use case `assess_submission`. It coordinates validation, policy rules, scoring, knowledge retrieval, decision formation, escalation, and audit persistence. It does not contain transport-specific logic.

### Rules and scoring

Rules are explicit and deterministic: eligibility checks, mandatory fields, appetite boundaries, decline criteria, and referral triggers. Scoring is an input to the decision policy, not a substitute for policy. Every rule and score must be included in the decision explanation with a version identifier.

### Integration layer

The integration layer isolates external services. The Project 3 client belongs here. This prevents a direct source-code dependency between the RAG system and the underwriting service.

## Project 3 RAG contract

### Request

The Underwriting Agent sends a versioned request only after it has a validated context.

```json
{
  "contract_version": "1.0",
  "correlation_id": "uuid",
  "query": "What are the referral criteria for this commercial property risk?",
  "context": {
    "product": "commercial_property",
    "jurisdiction": "QC",
    "coverage": "property",
    "risk_facts": {"occupancy": "...", "construction": "..."}
  },
  "top_k": 5
}
```

### Response

Project 3 returns evidence, not a binding underwriting decision.

```json
{
  "contract_version": "1.0",
  "correlation_id": "uuid",
  "evidence": [
    {
      "document_id": "guideline-123",
      "text": "Relevant approved underwriting guidance...",
      "source": "Commercial Property Underwriting Guide",
      "section": "Referral criteria",
      "retrieval_score": 0.91
    }
  ],
  "retrieval_confidence": 0.88,
  "warnings": []
}
```

The exact endpoint, authentication mechanism, and persistence technology remain implementation choices. The semantic contract and correlation ID are mandatory.

## Decision policy

The decision policy produces one of four controlled outcomes:

| Outcome | Meaning | Human action |
|---|---|---|
| `accept` | Rules pass and available evidence supports the appetite. | Human approval may still be required by operating policy. |
| `refer` | More information, expert judgment, or an authority review is required. | Underwriter reviews and decides. |
| `decline` | A deterministic decline rule applies or required information cannot be obtained. | Underwriter confirms where policy requires. |
| `review_required` | Technical, evidence, or confidence failure prevents a safe recommendation. | Human review is mandatory. |

Generative language may summarize a decision but must not override deterministic rules, decision thresholds, or mandatory escalation.

## Sequence: knowledge-supported assessment

```text
Caller -> API: assess submission
API -> Application: validated request
Application -> Rules: evaluate eligibility
Application -> Scoring: calculate risk signals
Application -> RAG Client: retrieve guideline evidence
RAG Client -> Project 3: versioned knowledge query
Project 3 --> RAG Client: evidence + confidence + sources
Application -> Decision Policy: rules + score + evidence
Decision Policy --> Application: recommendation + rationale
Application -> Audit Store: persist full decision trace
Application --> API: response or review request
API --> Caller: controlled outcome
```

## Failure and escalation policy

| Failure condition | Safe behavior |
|---|---|
| Mandatory submission field missing | Return `refer` or `review_required`; never infer a material fact. |
| A hard decline rule applies | Produce `decline` with the rule identifier and rationale. |
| Project 3 is unavailable | Continue only if deterministic policy permits; otherwise require review. Record the outage. |
| Retrieval confidence is below threshold | Do not present evidence as authoritative; require review or ask for more information. |
| Evidence conflicts with a deterministic rule | Deterministic rule prevails; log the conflict and refer when necessary. |
| Risk score or model input is unavailable | Do not fabricate a score; route according to fallback policy. |

## Auditability requirements

Each assessment must carry a `correlation_id` and record:

- Submission and input-schema versions
- Rule identifiers, outcomes, and rule-set version
- Score values, feature/data provenance, and scoring-model version
- Project 3 request and response identifiers
- Evidence source, document section, retrieval score, and confidence
- Decision outcome, explanation, confidence, and escalation reason
- Human-review action, actor identifier where permitted, timestamp, and amendment reason

Audit records must distinguish facts supplied by the submission, deterministic rule results, analytical signals, retrieved knowledge, and generated narrative.

## Security and data handling

- Keep API keys and service credentials in environment-managed secrets.
- Do not place customer documents, personally identifiable information, or underwriting data in repositories, logs, or test fixtures.
- Use synthetic or de-identified fixtures for automated tests.
- Restrict Project 3 queries to the minimum necessary underwriting context.
- Apply authorization and retention controls before connecting production data sources.

## Implementation roadmap

1. Define Pydantic request/response models for the RAG contract.
2. Implement a timeout-bounded Project 3 client and a mock adapter for tests.
3. Persist a structured decision/audit record for every assessment.
4. Add contract tests for successful, low-confidence, empty-evidence, and unavailable-RAG responses.
5. Run one synthetic end-to-end scenario through submission validation, RAG retrieval, decision, and human review.
