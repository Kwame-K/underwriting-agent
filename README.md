# Underwriting Agent

[![Continuous Integration](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

An explainable cyber-insurance underwriting workflow for Canadian small and medium-sized enterprises. It applies deterministic eligibility and appetite rules, calculates a cyber-risk score and a synthetic pricing indication, recommends conditions, and can attach documentary evidence and portfolio context. Persisted decisions support an audit trail and human review.

This repository is Project 4 in the Insurance Agentic Platform. It integrates with the Submission Extractor, Insurance Knowledge Agent, and Data Analyst Agent through HTTP. Those services supply inputs or context; they do not override underwriting rules.

> This is a portfolio and learning project. Rules, risk scores, pricing factors, and decisions are demonstrative. Do not use this service to bind coverage, quote commercial premiums, or make real underwriting decisions.

## Highlights

- FastAPI for structured submissions, extraction-to-underwriting, decision retrieval, review, and audit history.
- Pydantic validation and critical-field completeness checks.
- Versioned YAML policy, deterministic rules, explainable scoring, and synthetic pricing.
- Documentary citations and assistive provincial portfolio context.
- SQLAlchemy persistence with SQLite by default and PostgreSQL through Alembic.
- MCP stdio tools for extraction, evaluation, submission, and read-only decision queries.

## System Design

```text
Structured JSON ─────────────────────────────────┐
                                                  ↓
Raw submission text → Submission Extractor → map + apply overrides
                                                  ↓
Validation and completeness
    ↓
Eligibility, appetite, decline, and referral rules
    ↓
Risk scoring, pricing indication, and conditions when applicable
    ↓
Documentary evidence and assistive portfolio context
    ↓
UnderwritingDecision
    ↓
Persistence and audit trail when the entry point saves the decision
    ↓
Human review for persisted decisions that require it
```

## Decision Hierarchy

Validation and completeness checks come first. Decline and referral rules are evaluated before a result can be treated as eligible for automated acceptance. Evidence and portfolio context cannot bypass a rule or alter the risk score or price.

| Decision | Meaning |
|---|---|
| `NEED_MORE_INFORMATION` | Critical submission data is missing |
| `DECLINE` | The submission is outside the documented appetite |
| `REFER` | An underwriter must review the submission |
| `ACCEPT` | The submission satisfies the deterministic rules without recommended conditions |
| `ACCEPT_WITH_CONDITIONS` | The submission satisfies the rules with recommended conditions |
| `PENDING_UNDERWRITING` | Legacy value, not produced by the current workflow |

These are decision values, not review statuses or extraction workflow statuses. For example, `PENDING_REVIEW` is a review status used when listing stored decisions.

## Repository Structure

```text
underwriting-agent/
├── configs/
│   └── underwriting_policy.yaml
├── data/
├── docs/
│   ├── policy-reconciliation.md
│   └── system-architecture.md
├── src/underwriting_agent/
│   ├── api/
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   ├── integrations/
│   ├── mcp_server/
│   ├── rules/
│   ├── scoring/
│   └── settings.py
├── tests/
│   ├── e2e/
│   ├── integration/
│   └── unit/
├── .env.example
├── compose.yaml
├── Dockerfile
└── pyproject.toml
```

## Installation

Python 3.11+ and [uv](https://docs.astral.sh/uv/) are required.

```bash
git clone [https://github.com/Kwame-K/underwriting-agent.git](https://github.com/Kwame-K/underwriting-agent.git)
cd underwriting-agent
uv sync
cp .env.example .env
```

Example local configuration:

```dotenv
DATABASE_URL=sqlite:///data/underwriting_agent.db

SUBMISSION_EXTRACTOR_BASE_URL=http://127.0.0.1:8000
SUBMISSION_EXTRACTOR_TIMEOUT_SECONDS=30

KNOWLEDGE_AGENT_BASE_URL=http://127.0.0.1:8001
KNOWLEDGE_AGENT_TIMEOUT_SECONDS=20

PORTFOLIO_ANALYST_BASE_URL=http://127.0.0.1:8003
PORTFOLIO_ANALYST_TIMEOUT_SECONDS=30
```

The Extractor is needed for raw-text extraction. The Knowledge Agent and Analyst provide live evidence and portfolio context respectively. The central platform sets Compose service names rather than loopback addresses for service-to-service calls. Do not commit `.env`.

## Underwriting Policy

[`configs/underwriting_policy.yaml`](configs/underwriting_policy.yaml) defines supported countries, excluded industries, authority limits, MFA requirements, scoring and pricing factors, condition templates, and the policy version.

An exact match against an excluded industry triggers decline under `UW-CYB-002`. A free-text match against an excluded-industry alias triggers referral rather than automatic decline. See [Policy Reconciliation](docs/policy-reconciliation.md) for how executable rules are aligned with documentary evidence.

## Run the API

```bash
uv run uvicorn underwriting_agent.api.app:app --reload --port 8002
curl http://127.0.0.1:8002/health
```

OpenAPI is available at `http://127.0.0.1:8002/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service liveness |
| POST | `/underwrite` | Evaluate a structured submission and persist the resulting decision |
| GET | `/decisions?status=PENDING_REVIEW` | List stored decisions for a required review `status` |
| GET | `/decisions/{decision_id}` | Retrieve a stored decision |
| POST | `/decisions/{decision_id}/review` | Record a reviewer command |
| GET | `/decisions/{decision_id}/audit-trail` | Retrieve the audit events for a stored decision |
| POST | `/extract-and-underwrite` | Extract, map, and evaluate submission text; persist only when requested and evaluation completes |

## Submit an Underwriting Request

### Structured Cyber SME Submission

```bash
curl -X POST http://127.0.0.1:8002/underwrite \
  -H 'Content-Type: application/json' \
  -d '{
    "submission_id":"SUB-HIGH-RISK-RAG-001",
    "product_line":"CYBER_SME",
    "applicant_name":"Retail Services Inc.",
    "country":"Canada",
    "province":"Quebec",
    "industry":"Retail",
    "annual_revenue_cad":8000000,
    "employee_count":45,
    "handles_personal_data":true,
    "handles_payment_card_data":true,
    "mfa_enabled":false,
    "endpoint_detection_response":false,
    "offline_backups":false,
    "prior_cyber_claims":0,
    "requested_limit_cad":1000000,
    "requested_retention_cad":25000
  }'
```

The documented example for policy `0.6.0` returns `REFER`, a risk score of 99 (`SEVERE`), and a synthetic indicated premium of CAD 40,800. Retrieved evidence depends on the indexed corpus; portfolio context depends on the Analyst API and seeded data. Use the returned `decision_id`, not `submission_id`, to retrieve the stored decision.

### List and Review Stored Decisions

```bash
curl 'http://127.0.0.1:8002/decisions?status=PENDING_REVIEW'
```

Replace `DECISION_ID` with a returned decision identifier:

```bash
curl -X POST http://127.0.0.1:8002/decisions/DECISION_ID/review \
  -H 'Content-Type: application/json' \
  -d '{
    "reviewer_id":"UW-001",
    "action":"APPROVE",
    "notes":"Referral cleared after confirming MFA remediation timeline."
  }'

curl http://127.0.0.1:8002/decisions/DECISION_ID/audit-trail
```

### Extract and Underwrite from Raw Text

```bash
curl -X POST http://127.0.0.1:8002/extract-and-underwrite \
  -H 'Content-Type: application/json' \
  -H 'X-Correlation-ID: corr-0001' \
  -d '{
    "source_id":"EMAIL-001",
    "source_type":"EMAIL",
    "document_name":"broker-submission.eml",
    "content":"Applicant: Retail Services Inc. ...",
    "language":"en",
    "overrides":{
      "mfa_enabled":true,
      "requested_limit_cad":1000000,
      "requested_retention_cad":25000
    },
    "persist":false
  }'
```

This example demonstrates the request contract, not a guaranteed completed evaluation. The text is intentionally abbreviated. `overrides` supplies underwriting fields missing from the extraction. The API propagates the supplied `X-Correlation-ID` or generates one if omitted. `persist` defaults to `false`; with `true`, only a completed evaluation is saved.

| `workflow_status` | Meaning |
|---|---|
| `EVALUATED` | Extraction was mapped and evaluated; a decision is returned |
| `PENDING_INFORMATION` | Extraction requires review, mapping failed, or critical fields are missing; no decision is persisted |
| `UNSUPPORTED_SUBMISSION` | The submission does not request supported cyber coverage |
| `EXTRACTION_UNAVAILABLE` | The Extractor was unreachable or returned an invalid response |

## Pricing Indication

```text
base_exposure_premium = max(minimum_premium, annual_revenue × base_rate)

indicated_premium = max(
    minimum_premium,
    base_exposure_premium × limit_factor × risk_band_multiplier × retention_factor
)
```

For the documented structured example, CAD 8,000,000 × 0.003 gives a CAD 24,000 base exposure premium. Applying a 1.7 `SEVERE` multiplier and factors of 1.0 for the limit and retention gives CAD 40,800. This is not a commercial quote.

## Risk Scoring

The score uses revenue, employee count, personal- and payment-card-data exposure, MFA, endpoint detection and response, offline or immutable backups, prior cyber claims, and requested coverage limit. Returned `risk_factors` explain individual contributions.

| Score | Band |
|---:|---|
| 0–29 | `LOW` |
| 30–49 | `MEDIUM` |
| 50–69 | `HIGH` |
| 70–100 | `SEVERE` |

## Persistence and Audit Trail

`POST /underwrite` saves the submission and decision. `POST /extract-and-underwrite` saves only a completed evaluation when `persist=true`. MCP separates non-persisting evaluation tools from `submit_underwriting`, which writes.

SQLite defaults to `data/underwriting_agent.db`. A PostgreSQL `DATABASE_URL` selects PostgreSQL with Alembic migrations. Persisted decisions requiring human review can be listed with `status=PENDING_REVIEW`. The `DECISION_CREATED` audit event records evidence retrieval status and portfolio context.

## Insurance Knowledge Agent Integration (Project 3)

The service calls [`insurance-rag-assistant`](https://github.com/Kwame-K/insurance-rag-assistant) at `POST /v1/retrieve-evidence`. It does not access the corpus or vector store directly. Citations are attached as documentary evidence; unavailable or insufficient evidence is surfaced through `evidence_retrieval_status` and does not override the deterministic decision.

## Data Analyst Agent Integration (Project 2)

The service calls [`insurance-data-analyst-agent`](https://github.com/Kwame-K/insurance-data-analyst-agent) at `POST /v1/portfolio-quality-metrics`. The platform configures `PORTFOLIO_ANALYST_BASE_URL=http://data-analyst-agent:8003`.

The returned context is provincial, covers all lines of business, and is labelled synthetic. If the Analyst is unreachable, times out, or has no row for the province, `portfolio_context.status` is `UNAVAILABLE`. The underwriting decision, risk score, and pricing remain unchanged. The Analyst dataset must be initialized separately in the platform.

## MCP Server

```bash
uv run underwriting-mcp
```

The server runs over stdio and does not listen on an HTTP port. It uses the same settings and application services as the REST API.

| Tool | Purpose | Persists |
|---|---|---|
| `extract_submission` | Extract candidate data through the Submission Extractor | No |
| `extract_and_evaluate` | Extract, map, and evaluate with optional overrides | No |
| `check_completeness` | Report missing critical and optional fields | No |
| `evaluate_underwriting` | Evaluate a structured submission | No |
| `submit_underwriting` | Evaluate and save the decision | Yes |
| `get_decision` | Read a persisted decision | No |
| `get_audit_trail` | Read audit events | No |
| `list_pending_reviews` | List decisions awaiting review | No |

```bash
npx @modelcontextprotocol/inspector uv run underwriting-mcp
```

## Submission Extractor Integration (Project 1)

`POST /extract-and-underwrite` delegates to `ExtractAndEvaluateService`, which calls [`insurance-submission-extractor`](https://github.com/Kwame-K/insurance-submission-extractor), maps the candidate extraction, and applies explicit overrides. The same workflow is used by MCP `extract_and_evaluate`. Missing underwriting values are supplied explicitly or reported as missing, not invented.

## Project Boundaries

| Service | Owns |
|---|---|
| Submission Extractor | Candidate fields, extraction evidence, and extraction review flags |
| Data Analyst Agent | Deterministic portfolio metrics and provincial aggregations |
| Insurance Knowledge Agent | Retrieval, documentary citations, and evidence sufficiency |
| Underwriting Agent | Eligibility, rules, scoring, pricing, persistence, and decision review |
| Email Intake and Underwriting UI | Broker-email intake and the Streamlit operator interface; they do not own underwriting rules |

## Quality Checks

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
```

Run end-to-end tests against a running platform:

```bash
uv run pytest -m e2e -rs -v
```

`E2E_API_URL` defaults to `http://127.0.0.1:8002`. The tests cover validation, completeness, policy loading, rule priority, scoring, pricing, persistence, review, downstream integrations, migrations, and API and MCP contracts.

## Docker

```bash
docker compose up --build
```

The local Compose file publishes port `8002`. For the integrated demonstration, use the [Insurance Agentic Platform](https://github.com/Kwame-K/insurance-agentic-platform) and follow its PostgreSQL and Analyst initialization steps. The platform also runs [Email Intake](https://github.com/Kwame-K/insurance-email-intake) and the [Underwriting UI](https://github.com/Kwame-K/insurance-underwriting-ui).

## Design Principles

- Deterministic rules control material underwriting outcomes.
- Documentary evidence and portfolio metrics are assistive, not decision-makers.
- Persisted decisions retain policy, scoring, and pricing versions and can be audited.
- Services exchange data through HTTP contracts rather than accessing each other's internal stores.
- Missing inputs and unavailable integrations should surface as explicit statuses.

## Roadmap

- [x] Structured underwriting with deterministic eligibility, referral, scoring, and pricing.
- [x] Persistence, decision review, and audit trail.
- [x] Submission extraction, evidence retrieval, and portfolio context through HTTP.
- [ ] Generate underwriter summaries from verified facts and citations only.
- [ ] Explore LangGraph orchestration with conditional routing and human-review interruption.
- [ ] Improve cross-service tracing and platform deployment hardening.


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
| Observability | No tracing | Langfuse or OpenTelemetry spanning `/underwrite`, `/extract-and-underwrite`, and downstream HTTP calls | End-to-end latency and failure visibility across Projects 1, 2, 3, and 4 |
| Persistence | SQLite by default; Alembic + PostgreSQL when `DATABASE_URL` is Postgres | PostgreSQL as the shared platform store, SQLAlchemy 2.0 async | Concurrent access and cross-project decision analytics |
| Resilience | Synchronous HTTP calls with timeouts | Circuit breaker and retry policy (e.g. `tenacity`) around the knowledge-agent, extractor, and portfolio clients | Reduces cascading failures when Project 1, 2, or 3 is degraded |
| Summary generation | No LLM narrative | LLM-generated underwriter summary strictly from verified facts and citations (already on roadmap) | Faster underwriter review without weakening the deterministic core |
| Deployment | Local `uvicorn` + per-repo `compose.yaml` and CI | Centralized `insurance-agentic-platform` Compose stack (already in progress) | Single command to run Projects 1, 2, 3, and 4 together |

## Improvements and Next Steps

1. Close the remaining `docs/policy-reconciliation.md` "Pending alignment" items (for example `UW-CYB-001`, `UW-CYB-002`, `UW-CYB-004`) by adding documentary evidence to Project 3 or explicitly reclassifying the rules as internal authority controls.
2. Implement the LangGraph orchestration already on the roadmap to make the referral pause and multi-service retry logic explicit and inspectable.
3. Add a circuit breaker and retry policy around the Project 1, Project 2, and Project 3 HTTP clients to harden the resilience principle already documented.
4. Add an LLM-generated underwriter summary strictly from verified facts and citations.
5. Default the platform stack to PostgreSQL so concurrent underwriters share analytics with Project 2 (Alembic migrations already exist).

## Agentic AI Best Practices Applied Here

- **Strict decision hierarchy**: input validation, completeness, decline, referral, scoring, and pricing are evaluated in a fixed deterministic order that no retrieval or generative component can bypass.
- **RAG as evidence, not authority**: Project 3 citations explain a decision but cannot change it, directly mirroring current guidance that retrieval-augmented components should support, not replace, deterministic business logic.
- **Explicit failure degradation across service boundaries**: unavailable knowledge-agent, extractor, or portfolio-analyst services produce explicit statuses (empty evidence, `EXTRACTION_UNAVAILABLE`, `portfolio_context.status=UNAVAILABLE`) instead of silently failing open or closed.
- **Full audit trail and human-in-the-loop**: every decision, and every reviewer action on it, is persisted and retrievable, which is essential for a regulated, high-impact domain like underwriting.
- **Governed rule provenance**: `docs/policy-reconciliation.md` formally classifies every executable rule against documentary sources, making rule authority auditable rather than implicit.
- **Next practice to adopt**: wrap the multi-service workflow (extraction → underwriting → evidence retrieval → review) in an explicit orchestration graph (LangGraph) so pause points, retries, and human-review interrupts are first-class, versioned parts of the workflow rather than implicit control flow in `underwriting_service.py`.
