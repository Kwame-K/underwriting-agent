# Underwriting Agent

An explainable cyber-insurance underwriting workflow for Canadian small and medium-sized enterprises. The service validates a submission, checks underwriting appetite, calculates a deterministic cyber-risk score, produces a synthetic pricing indication, recommends underwriting conditions, retrieves documentary evidence from the Insurance Knowledge Agent, and persists every decision with a full audit trail and human-review workflow.

This repository is **Project 4** in a five-project insurance agentic AI portfolio. It combines deterministic underwriting controls with two external services (a submission extractor and a RAG knowledge agent) while keeping material underwriting decisions auditable and under explicit rule control.

> **Scope note:** this is a portfolio and learning project. All underwriting rules, risk scores, pricing factors, documents, decisions, and examples are synthetic or demonstrative. The system must not be used to bind coverage, set a commercial premium, or make real underwriting decisions.

## Highlights

- FastAPI endpoints: `POST /underwrite`, `GET /decisions`, `GET /decisions/{id}`, `POST /decisions/{id}/review`, `GET /decisions/{id}/audit-trail`, `POST /extract-and-underwrite`.
- Pydantic validation for structured cyber SME submissions.
- Critical-field completeness checks before risk evaluation.
- Deterministic eligibility, appetite, referral, and decline rules.
- Versioned underwriting policy stored in YAML (`configs/underwriting_policy.yaml`).
- Explainable rule-based cyber-risk score from 0 to 100.
- Risk bands: `LOW`, `MEDIUM`, `HIGH`, and `SEVERE`.
- Synthetic pricing indication using revenue, limit, retention, and risk band.
- Structured underwriting conditions and information requests.
- Human-review workflow with persisted decisions and reviewer commands.
- SQLAlchemy persistence (SQLite by default) for submissions, decisions, reviews, and audit events.
- HTTP integration with Project 3 (Insurance Knowledge Agent / RAG service) for documentary evidence.
- HTTP integration with Project 1 (Submission Extractor) through `POST /extract-and-underwrite`.
- Graceful fallback when the knowledge service or extractor is unavailable.
- Documented policy-reconciliation process aligning executable rules with documentary evidence.
- `uv`, Git, Ruff, mypy, pytest, and GitHub Actions-ready project structure.

## System Design

```text
Raw submission text (Project 1) or structured JSON
        |
        v
InsuranceSubmission validation
        |
        v
CompletenessChecker
  |-- Critical data missing --> NEED_MORE_INFORMATION
  '-- Complete submission
        |
        v
UnderwritingRulesEngine
  |-- Outside appetite --> DECLINE
  |-- Referral trigger --> REFER
  '-- Eligible submission
        |
        v
CyberRiskScoringService
        |
        v
CyberPricingIndicationService
        |
        v
UnderwritingConditionsRecommender
        |
        v
HTTPInsuranceKnowledgeAgent --> Project 3 (Qdrant + semantic retrieval + citations)
        |
        v
UnderwritingDecision
        |
        v
UnderwritingDecisionRepository (SQLAlchemy persistence + audit trail)
        |
        v
Human review (when human_review_required = true)
```

## Decision Hierarchy

The project follows a strict hierarchy. A generative model or retrieval component cannot override deterministic underwriting rules.

```text
1. Input validation
2. Completeness validation
3. Decline rules
4. Referral rules
5. Risk scoring
6. Pricing indication
7. Conditions recommendation
8. Documentary evidence retrieval
9. Persistence and audit trail
10. Human underwriting review when required
```

| Decision | Meaning |
|---|---|
| `NEED_MORE_INFORMATION` | Critical submission data is missing; no risk decision can proceed |
| `DECLINE` | The submission is outside the documented underwriting appetite |
| `REFER` | The submission requires review by an authorized underwriter |
| `PENDING_UNDERWRITING` | The submission meets current deterministic rules; later workflow stages may continue |
| `ACCEPT_WITH_CONDITIONS` | Reserved for a later workflow stage with explicit approval authority |
| `ACCEPT` | Reserved for a later workflow stage with explicit approval authority |

## Repository Structure

```text
underwriting-agent/
├── configs/
│   └── underwriting_policy.yaml          # Versioned synthetic business policy
├── data/
│   ├── synthetic/
│   ├── evaluation/
│   └── underwriting_agent.db             # Local SQLite database
├── docs/
│   └── policy-reconciliation.md          # Reconciles YAML rules with Project 3 documentary evidence
├── src/underwriting_agent/
│   ├── api/
│   │   ├── app.py                        # FastAPI application and routes
│   │   ├── dependencies.py
│   │   └── extraction_models.py          # Extract-and-underwrite request/response contracts
│   ├── application/
│   │   ├── completeness_service.py
│   │   ├── conditions_service.py
│   │   └── underwriting_service.py
│   ├── domain/
│   │   ├── audit.py                      # AuditEvent, AuditEventType
│   │   ├── completeness.py
│   │   ├── condition.py
│   │   ├── decision.py
│   │   ├── enums.py
│   │   ├── evidence.py
│   │   ├── policy.py
│   │   ├── pricing.py
│   │   ├── review.py                     # DecisionReview, ReviewDecisionCommand
│   │   ├── risk_score.py
│   │   ├── rules.py
│   │   └── submission.py
│   ├── infrastructure/
│   │   ├── persistence/
│   │   │   ├── database.py               # SQLAlchemy engine and session factory
│   │   │   └── models.py                 # ORM records for submissions, decisions, reviews, audit events
│   │   └── repositories/
│   │       └── decision_repository.py    # UnderwritingDecisionRepository
│   ├── integrations/
│   │   ├── knowledge_agent/
│   │   │   ├── http_client.py            # Calls Project 3
│   │   │   ├── no_op_client.py
│   │   │   └── port.py
│   │   └── submission_extractor/
│   │       ├── http_client.py            # Calls Project 1
│   │       ├── models.py
│   │       └── port.py
│   ├── rules/
│   │   ├── engine.py
│   │   └── policy_loader.py
│   ├── scoring/
│   │   ├── pricing.py
│   │   └── risk_score.py
│   └── settings.py
├── tests/
│   ├── integration/
│   │   ├── test_extract_and_underwrite_api.py
│   │   └── test_health_api.py
│   └── unit/
│       ├── test_completeness_service.py
│       ├── test_conditions_service.py
│       ├── test_decision_repository.py
│       ├── test_policy_loader.py
│       ├── test_pricing_service.py
│       ├── test_review.py
│       ├── test_risk_scoring_service.py
│       ├── test_rules_engine.py
│       ├── test_submission.py
│       └── test_submission_extractor_http_client.py
├── .env.example
├── compose.yaml
├── pyproject.toml
└── README.md
```

## Installation

### Prerequisites

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/)
- Git
- Project 3 running locally only when testing real RAG evidence retrieval
- Project 1 running locally only when testing `POST /extract-and-underwrite`

### Setup

```bash
git clone https://github.com/Kwame-K/underwriting-agent.git
cd underwriting-agent
uv sync
```

Create the local environment file:

```bash
cp .env.example .env
```

Expected local development configuration:

```dotenv
KNOWLEDGE_AGENT_BASE_URL=http://127.0.0.1:8001
KNOWLEDGE_AGENT_TIMEOUT_SECONDS=10

SUBMISSION_EXTRACTOR_BASE_URL=http://127.0.0.1:8000
SUBMISSION_EXTRACTOR_TIMEOUT_SECONDS=30

DATABASE_URL=sqlite:///data/underwriting_agent.db
```

Do not commit `.env`. Commit `.env.example` only.

## Underwriting Policy

The synthetic policy is located at `configs/underwriting_policy.yaml` and contains supported countries, excluded industries, automated underwriting authority thresholds, MFA requirements, scoring and pricing factors, condition templates, and a policy version.

Example:

```yaml
policy_name: Cyber SME Underwriting Policy
policy_version: 0.4.0
product_line: CYBER_SME

supported_countries:
  - Canada

authority:
  max_automated_limit_cad: 2000000
  max_automated_revenue_cad: 50000000
  max_automated_prior_claims: 1
```

Every material change to a rule, threshold, factor, condition, or exclusion should increment `policy_version`. See [Policy Reconciliation](docs/policy-reconciliation.md) for how each executable rule is classified against documentary evidence from Project 3.

## Run the API

Start the Underwriting Agent on port `8000`:

```bash
uv run uvicorn underwriting_agent.api.app:app --reload --port 8000
```

Open the interactive OpenAPI interface at `http://127.0.0.1:8000/docs`.

Available endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service liveness check |
| POST | `/underwrite` | Evaluate a structured submission and persist the decision |
| GET | `/decisions` | List persisted decisions filtered by review status |
| GET | `/decisions/{decision_id}` | Retrieve a persisted decision |
| POST | `/decisions/{decision_id}/review` | Record an underwriter's review command |
| GET | `/decisions/{decision_id}/audit-trail` | Retrieve the full audit trail for a decision |
| POST | `/extract-and-underwrite` | Extract a raw submission via Project 1, then underwrite it |

### Health Check

```bash
curl "http://127.0.0.1:8000/health"
```

```json
{
  "status": "ok"
}
```

## Submit an Underwriting Request

### High-risk cyber SME example

```bash
curl -X POST "http://127.0.0.1:8000/underwrite" \
  -H "Content-Type: application/json" \
  -d '{
    "submission_id": "SUB-HIGH-RISK-RAG-001",
    "product_line": "CYBER_SME",
    "applicant_name": "Retail Services Inc.",
    "country": "Canada",
    "province": "Quebec",
    "industry": "Retail",
    "annual_revenue_cad": 8000000,
    "employee_count": 45,
    "handles_personal_data": true,
    "handles_payment_card_data": true,
    "mfa_enabled": false,
    "endpoint_detection_response": false,
    "offline_backups": false,
    "prior_cyber_claims": 0,
    "requested_limit_cad": 1000000,
    "requested_retention_cad": 25000
  }'
```

Expected underwriting outcome:

```json
{
  "decision": "REFER",
  "human_review_required": true,
  "risk_score": 99,
  "risk_band": "SEVERE",
  "base_exposure_premium_cad": 24000.0,
  "indicated_premium_cad": 40800.0,
  "policy_version": "0.4.0",
  "scoring_model_version": "0.1.0",
  "pricing_model_version": "0.1.0",
  "evidence": [
    {
      "source_document_title": "Cyber Insurance Underwriting Guide",
      "section_reference": "3. Minimum Security Controls",
      "supported_finding_id": "UW-CYB-003"
    }
  ]
}
```

The exact citations depend on the documents indexed by Project 3. This request is automatically persisted, so the decision becomes retrievable through `GET /decisions/{decision_id}`.

### List and review referred decisions

```bash
curl "http://127.0.0.1:8000/decisions?status=PENDING_REVIEW"
```

```bash
curl -X POST "http://127.0.0.1:8000/decisions/SUB-HIGH-RISK-RAG-001/review" \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_id": "UW-001",
    "action": "APPROVE",
    "notes": "Referral cleared after confirming MFA remediation timeline."
  }'
```

### Inspect the audit trail

```bash
curl "http://127.0.0.1:8000/decisions/SUB-HIGH-RISK-RAG-001/audit-trail"
```

### Extract and underwrite from raw text (Project 1 integration)

```bash
curl -X POST "http://127.0.0.1:8000/extract-and-underwrite" \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: corr-0001" \
  -d '{
    "source_id": "EMAIL-001",
    "source_type": "EMAIL",
    "document_name": "broker-submission.eml",
    "content": "Applicant: Retail Services Inc. ... ",
    "language": "en"
  }'
```

If Project 1 extraction is incomplete or flagged for review, the workflow returns `PENDING_INFORMATION` with missing fields instead of proceeding to underwriting. If Project 1 is unreachable, it returns `EXTRACTION_UNAVAILABLE` rather than failing silently.

## Pricing Indication

The pricing service uses a synthetic, deterministic formula:

\[
\text{Indicated Premium} = \max\left(\text{Minimum Premium}, \text{Base Exposure Premium} \times \text{Limit Factor} \times \text{Risk Band Multiplier} \times \text{Retention Factor}\right)
\]

Where:

\[
\text{Base Exposure Premium} = \max\left(\text{Minimum Premium}, \text{Annual Revenue} \times \text{Base Rate}\right)
\]

For the example above:

```text
Revenue: 8,000,000 CAD
Base rate: 0.003
Base exposure premium: 24,000 CAD
Requested limit factor: 1.0
SEVERE risk band multiplier: 1.7
Reference retention factor: 1.0

Indicated premium: 24,000 x 1.0 x 1.7 x 1.0 = 40,800 CAD
```

This calculation is not a commercial premium quote. It is a transparent demonstration of how exposure, coverage limit, deductible, and risk characteristics can affect a technical indication.

## Risk Scoring

The scoring model is deterministic and interpretable. It calculates a score from 0 to 100 using annual revenue, employee count, personal-data exposure, payment-card-data exposure, MFA status, EDR deployment status, offline/immutable backup status, prior cyber claims, and requested coverage limit.

| Score range | Risk band |
|---:|---|
| 0–29 | `LOW` |
| 30–49 | `MEDIUM` |
| 50–69 | `HIGH` |
| 70–100 | `SEVERE` |

The API returns the individual `risk_factors` that contributed to the result, making the calculation inspectable and testable.

## Persistence and Audit Trail

Every `POST /underwrite` call persists the submission, the decision, and an audit event through `UnderwritingDecisionRepository`, backed by SQLAlchemy (SQLite by default at `data/underwriting_agent.db`). Decisions requiring human review are stored with `PENDING_REVIEW` status until an underwriter records a review command via `POST /decisions/{decision_id}/review`. The full audit trail (submission, decision, review actions) is retrievable at any time through `GET /decisions/{decision_id}/audit-trail`.

## Insurance Knowledge Agent Integration (Project 3)

Project 4 does not access Qdrant or insurance documents directly. Instead, it calls Project 3 through a versioned HTTP boundary.

```text
Project 4 Underwriting Agent, http://127.0.0.1:8000
        |
        v
HTTPInsuranceKnowledgeAgent
        |
        v
Project 3 Insurance Knowledge Agent, http://127.0.0.1:8001/v1/retrieve-evidence
        |
        v
Qdrant + multilingual E5 retrieval
        |
        v
Documentary citations
        |
        v
UnderwritingDecision.evidence
```

### Start both services

First terminal, Project 3:

```bash
cd /path/to/insurance-rag-assistant
uv run uvicorn insurance_rag_assistant.api.app:app --reload --port 8001
```

Second terminal, Project 4:

```bash
cd /path/to/underwriting-agent
uv run uvicorn underwriting_agent.api.app:app --reload --port 8000
```

### Resilience principle

If the knowledge service is unavailable, times out, or returns no relevant citation, the underwriting decision remains deterministic, the risk score and pricing indication remain available, and documentary evidence can be empty. A RAG failure must never silently turn a decline into an acceptance, or bypass a referral rule.

## Submission Extractor Integration (Project 1)

`POST /extract-and-underwrite` calls Project 1 through `SubmissionExtractorPort` (`http_client.py`) to convert raw broker text into a structured submission before underwriting proceeds. A correlation ID (`X-Correlation-ID` header) is generated or propagated end to end, and extraction failures degrade to an explicit `EXTRACTION_UNAVAILABLE` or `PENDING_INFORMATION` workflow status rather than a silent failure.

## Project Boundaries

| Project 4 owns | Project 3 owns | Project 1 owns |
|---|---|---|
| Submission validation | Insurance documents | Broker document parsing |
| Completeness checks | Chunking and metadata | Field extraction |
| Appetite and eligibility rules | E5 embeddings | Extraction review routing |
| Referral and decline logic | Qdrant collection | Extraction confidence |
| Risk scoring | Semantic retrieval | |
| Pricing indication | Citation retrieval | |
| Conditions recommendation | Grounded answer generation | |
| Human-review routing and persistence | Document-level evidence | |

## Quality Checks

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest
```

The test suite includes unit and integration coverage for Pydantic submission validation, critical-field completeness checks, underwriting policy loading, deterministic rules and priority handling, cyber risk scoring and score caps, pricing calculations and minimum premium, condition recommendations, decision persistence and review workflow, submission-extractor HTTP client behavior, and FastAPI health, underwriting, and extraction endpoints.

## Docker

```bash
docker compose up --build
```

This service can also be orchestrated centrally by the `insurance-agentic-platform` Docker Compose project alongside Project 1 and Project 3.

## Design Principles

- **Deterministic decisions first:** critical underwriting outcomes remain Python/YAML rules.
- **LLM and RAG are assistive:** evidence explains or supports a decision; it does not override it.
- **Human-in-the-loop:** sensitive, high-risk, or out-of-authority risks are referred and persisted for review.
- **Versioned policy:** decisions preserve `policy_version`, scoring version, and pricing version.
- **Traceability:** outputs include rule results, factors, conditions, documentary evidence, and a full audit trail.
- **Service isolation:** Projects 1 and 3 are accessed by HTTP rather than shared direct access to their internal data stores.
- **Failure-safe behavior:** unavailable RAG evidence or extraction must not stop deterministic controls; they degrade to explicit statuses.
- **Portfolio realism:** all data and business logic are explicitly synthetic.

## Roadmap

- [x] Structured cyber SME submission model
- [x] Completeness checking
- [x] YAML-configured appetite and eligibility rules
- [x] Referral and decline routing
- [x] Deterministic cyber risk scoring
- [x] Synthetic pricing indication
- [x] Underwriting condition recommender
- [x] Insurance Knowledge Agent integration through HTTP (Project 3)
- [x] Retrieval evidence included in the underwriting response
- [x] Persistence of submissions, decisions, and audit events (SQLAlchemy)
- [x] Human-review workflow (`/decisions`, `/decisions/{id}/review`)
- [x] Policy reconciliation between YAML rules and documentary sources (`docs/policy-reconciliation.md`)
- [x] Raw document integration through Project 1 Submission Extractor (`/extract-and-underwrite`)
- [ ] Retrieval status and failure metadata surfaced directly in the audit trail
- [ ] Portfolio and claims analysis through Project 2 Data Analyst Agent
- [ ] LLM-generated underwriter summary using verified facts and citations only
- [ ] LangGraph orchestration with conditional routing and human-review interruption
- [ ] Full Docker Compose, observability, CI/CD, and deployment hardening at the platform level

## Position in the Insurance Agentic Platform

| Project | Repository | Role |
|---|---|---|
| 1 | insurance-submission-extractor | Structured submission intake and validation |
| 2 | insurance-data-analyst-agent | Controlled portfolio analytics (loss ratio, deterministic SQL) |
| 3 | insurance-rag-assistant | Insurance Knowledge Agent with grounded, cited retrieval |
| 4 | underwriting-agent (this repo) | Deterministic underwriting rules, risk scoring, pricing, and evidence retrieval |
| — | insurance-agentic-platform | Docker Compose orchestration layer for the running services |

## Recommended Technology Upgrades

| Area | Current | Recommended (2026) | Benefit |
|---|---|---|---|
| Orchestration | Sequential Python service calls | LangGraph with conditional routing and human-review interruption (already on roadmap) | Explicit graph-based control over referral pauses and multi-service retries |
| Observability | No tracing | Langfuse or OpenTelemetry spanning `/underwrite`, `/extract-and-underwrite`, and downstream HTTP calls | End-to-end latency and failure visibility across Projects 1, 3, and 4 |
| Persistence | SQLite via SQLAlchemy | PostgreSQL with SQLAlchemy 2.0 async, shared with Project 2's audit store | Concurrent access and cross-project decision analytics |
| Resilience | Synchronous HTTP calls with timeouts | Circuit breaker and retry policy (e.g. `tenacity`) around the knowledge-agent and extractor clients | Reduces cascading failures when Project 1 or 3 is degraded |
| Summary generation | No LLM narrative | LLM-generated underwriter summary strictly from verified facts and citations (already on roadmap) | Faster underwriter review without weakening the deterministic core |
| Deployment | Local `uvicorn` + `compose.yaml` per repo | Centralized `insurance-agentic-platform` Compose stack (already in progress) | Single command to run Projects 1, 3, and 4 together |

## Improvements and Next Steps

1. Close the remaining `docs/policy-reconciliation.md` "Pending alignment" items (for example `UW-CYB-001`, `UW-CYB-002`, `UW-CYB-004`) by adding documentary evidence to Project 3 or explicitly reclassifying the rules as internal authority controls.
2. Surface Project 3 retrieval status (`SUCCESS`/`PARTIAL`/`INSUFFICIENT_CONTEXT`) directly in the persisted audit trail so reviewers can see when a decision relied on incomplete evidence.
3. Implement the LangGraph orchestration already on the roadmap to make the referral pause and multi-service retry logic explicit and inspectable.
4. Add a circuit breaker and retry policy around the Project 1 and Project 3 HTTP clients to harden the resilience principle already documented.
5. Integrate Project 2 (Data Analyst Agent) so portfolio-level loss-ratio context can inform referral review, without changing the deterministic decision hierarchy.
6. Migrate persistence from SQLite to PostgreSQL to support concurrent underwriters and shared analytics with Project 2.

## Agentic AI Best Practices Applied Here

- **Strict decision hierarchy**: input validation, completeness, decline, referral, scoring, and pricing are evaluated in a fixed deterministic order that no retrieval or generative component can bypass.
- **RAG as evidence, not authority**: Project 3 citations explain a decision but cannot change it, directly mirroring current guidance that retrieval-augmented components should support, not replace, deterministic business logic.
- **Explicit failure degradation across service boundaries**: unavailable knowledge-agent or extractor services produce explicit statuses (empty evidence, `EXTRACTION_UNAVAILABLE`) instead of silently failing open or closed.
- **Full audit trail and human-in-the-loop**: every decision, and every reviewer action on it, is persisted and retrievable, which is essential for a regulated, high-impact domain like underwriting.
- **Governed rule provenance**: `docs/policy-reconciliation.md` formally classifies every executable rule against documentary sources, making rule authority auditable rather than implicit.
- **Next practice to adopt**: wrap the multi-service workflow (extraction → underwriting → evidence retrieval → review) in an explicit orchestration graph (LangGraph) so pause points, retries, and human-review interrupts are first-class, versioned parts of the workflow rather than implicit control flow in `underwriting_service.py`.
