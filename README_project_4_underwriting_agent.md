# Underwriting Agent

An explainable cyber-insurance underwriting workflow for Canadian small and medium-sized enterprises. The service validates a submission, checks underwriting appetite, calculates a deterministic cyber-risk score, produces a synthetic pricing indication, recommends underwriting conditions, and retrieves documentary evidence from the Insurance Knowledge Agent.

This repository is **Project 4** in an insurance AI portfolio. It combines deterministic underwriting controls with an external RAG service while keeping material underwriting decisions auditable and under explicit rule control.

> **Scope note:** this is a portfolio and learning project. All underwriting rules, risk scores, pricing factors, documents, decisions, and examples are synthetic or demonstrative. The system must not be used to bind coverage, set a commercial premium, or make real underwriting decisions.

## Highlights

- FastAPI underwriting endpoint: `POST /underwrite`.
- Pydantic validation for structured cyber SME submissions.
- Critical-field completeness checks before risk evaluation.
- Deterministic eligibility, appetite, referral, and decline rules.
- Versioned underwriting policy stored in YAML.
- Explainable rule-based cyber-risk score from 0 to 100.
- Risk bands: `LOW`, `MEDIUM`, `HIGH`, and `SEVERE`.
- Synthetic pricing indication using revenue, limit, retention, and risk band.
- Structured underwriting conditions and information requests.
- Human-review routing for referred risks.
- HTTP integration with Project 3, the Insurance Knowledge Agent / RAG service.
- Documentary evidence attached to underwriting decisions.
- Graceful fallback when the knowledge service is unavailable.
- `uv`, Git, Ruff, mypy, pytest, and GitHub Actions-ready project structure.

## System design

```text
Raw submission or structured JSON
        ↓
InsuranceSubmission validation
        ↓
CompletenessChecker
        ├── Critical data missing → NEED_MORE_INFORMATION
        └── Complete submission
                    ↓
        UnderwritingRulesEngine
        ├── Outside appetite → DECLINE
        ├── Referral trigger → REFER
        └── Eligible submission
                    ↓
        CyberRiskScoringService
                    ↓
        CyberPricingIndicationService
                    ↓
        UnderwritingConditionsRecommender
                    ↓
        HTTPInsuranceKnowledgeAgent
                    ↓
        Project 3 Insurance Knowledge Agent
        Qdrant + semantic retrieval + citations
                    ↓
        UnderwritingDecision
```

## Decision hierarchy

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
9. Human underwriting review when required
```

| Decision | Meaning |
|---|---|
| `NEED_MORE_INFORMATION` | Critical submission data is missing; no risk decision can proceed |
| `DECLINE` | The submission is outside the documented underwriting appetite |
| `REFER` | The submission requires review by an authorized underwriter |
| `PENDING_UNDERWRITING` | The submission meets current deterministic rules; later workflow stages may continue |
| `ACCEPT_WITH_CONDITIONS` | Reserved for a later workflow stage with explicit approval authority |
| `ACCEPT` | Reserved for a later workflow stage with explicit approval authority |

## Repository structure

```text
underwriting-agent/
├── configs/
│   └── underwriting_policy.yaml       # Versioned synthetic business policy
├── data/
│   ├── synthetic/
│   └── evaluation/
├── docs/
│   ├── architecture.md
│   ├── decision-policy.md
│   ├── evaluation-framework.md
│   ├── model-card.md
│   ├── policy-reconciliation.md       # To be completed
│   └── risk-register.md
├── src/underwriting_agent/
│   ├── api/
│   │   ├── app.py
│   │   └── dependencies.py
│   ├── application/
│   │   ├── completeness_service.py
│   │   ├── conditions_service.py
│   │   └── underwriting_service.py
│   ├── domain/
│   │   ├── completeness.py
│   │   ├── condition.py
│   │   ├── decision.py
│   │   ├── enums.py
│   │   ├── evidence.py
│   │   ├── policy.py
│   │   ├── pricing.py
│   │   ├── risk_score.py
│   │   ├── rules.py
│   │   └── submission.py
│   ├── integrations/
│   │   └── knowledge_agent/
│   │       ├── http_client.py
│   │       ├── no_op_client.py
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
│   └── unit/
├── .env.example
├── pyproject.toml
└── README.md
```

## Installation

### Prerequisites

- Python 3.11 or later.
- [uv](https://docs.astral.sh/uv/).
- Git.
- Project 3 running locally only when testing real RAG evidence retrieval.

### Setup

```bash
git clone <your-repository-url>
cd underwriting-agent
uv sync
```

Create the local environment file:

```bash
cp .env.example .env
```

Expected local development configuration:

```bash
KNOWLEDGE_AGENT_BASE_URL=http://127.0.0.1:8001
KNOWLEDGE_AGENT_TIMEOUT_SECONDS=5
```

Do not commit `.env`. Commit `.env.example` only.

## Underwriting policy

The synthetic policy is located at:

```text
configs/underwriting_policy.yaml
```

It contains:

- Supported countries.
- Excluded industries.
- Automated underwriting authority thresholds.
- MFA requirements.
- Scoring and pricing factors.
- Condition templates.
- Policy version.

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

Every material change to a rule, threshold, factor, condition, or exclusion should increment `policy_version`.

## Run the API

Start the Underwriting Agent on port `8000`:

```bash
uv run uvicorn underwriting_agent.api.app:app --reload --port 8000
```

Open the interactive OpenAPI interface:

```text
http://127.0.0.1:8000/docs
```

Available endpoints:

```text
GET  /health
POST /underwrite
```

### Health check

```bash
curl "http://127.0.0.1:8000/health"
```

Expected response:

```json
{
  "status": "ok"
}
```

## Submit an underwriting request

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

The exact citations depend on the documents indexed by Project 3.

## Pricing indication

The pricing service uses a synthetic, deterministic formula:

\[
\text{Indicated Premium}
=
\max\left(
\text{Minimum Premium},
\text{Base Exposure Premium}
\times
\text{Limit Factor}
\times
\text{Risk Band Multiplier}
\times
\text{Retention Factor}
\right)
\]

Where:

\[
\text{Base Exposure Premium}
=
\max\left(
\text{Minimum Premium},
\text{Annual Revenue} \times \text{Base Rate}
\right)
\]

For the example above:

```text
Revenue: 8,000,000 CAD
Base rate: 0.003
Base exposure premium: 24,000 CAD
Requested limit factor: 1.0
SEVERE risk band multiplier: 1.7
Reference retention factor: 1.0

Indicated premium: 24,000 × 1.0 × 1.7 × 1.0 = 40,800 CAD
```

This calculation is not a commercial premium quote. It is a transparent demonstration of how exposure, coverage limit, deductible, and risk characteristics can affect a technical indication.

## Risk scoring

The first scoring model is deterministic and interpretable. It calculates a score from 0 to 100 using factors such as:

- Annual revenue.
- Number of employees.
- Personal-data exposure.
- Payment-card-data exposure.
- MFA status.
- EDR deployment status.
- Offline or immutable backup status.
- Prior cyber claims.
- Requested coverage limit.

| Score range | Risk band |
|---:|---|
| 0–29 | `LOW` |
| 30–49 | `MEDIUM` |
| 50–69 | `HIGH` |
| 70–100 | `SEVERE` |

The API returns the individual `risk_factors` that contributed to the result. This makes the calculation inspectable and suitable for testing.

## Insurance Knowledge Agent integration

Project 4 does not access Qdrant or insurance documents directly. Instead, it calls Project 3 through a versioned HTTP boundary.

```text
Project 4 Underwriting Agent
http://127.0.0.1:8000
        ↓
HTTPInsuranceKnowledgeAgent
        ↓
Project 3 Insurance Knowledge Agent
http://127.0.0.1:8001/v1/retrieve-evidence
        ↓
Qdrant + multilingual E5 retrieval
        ↓
Documentary citations
        ↓
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

Then call `POST /underwrite` on port `8000`.

### Resilience principle

If the knowledge service is unavailable, times out, or returns no relevant citation:

```text
Underwriting decision remains deterministic.
Risk score and pricing indication remain available.
Documentary evidence can be empty.
The incident should be logged and surfaced through future audit metadata.
```

A RAG failure must never silently turn a decline into an acceptance, or bypass a referral rule.

## Project boundaries

| Project 4 owns | Project 3 owns |
|---|---|
| Submission validation | Insurance documents |
| Completeness checks | Chunking and metadata |
| Appetite and eligibility rules | E5 embeddings |
| Referral and decline logic | Qdrant collection |
| Risk scoring | Semantic retrieval |
| Pricing indication | Citation retrieval |
| Conditions recommendation | Grounded answer generation |
| Human-review routing | Document-level evidence |

## Quality checks

Run the complete local quality suite:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest
```

The test suite includes unit and integration coverage for:

- Pydantic submission validation.
- Critical-field completeness checks.
- Underwriting policy loading.
- Deterministic rules and priority handling.
- Cyber risk scoring and score caps.
- Pricing calculations and minimum premium.
- Condition recommendations.
- Knowledge-agent contract injection.
- FastAPI health and underwriting endpoints.

## Design principles

- **Deterministic decisions first:** critical underwriting outcomes remain Python/YAML rules.
- **LLM and RAG are assistive:** evidence explains or supports a decision; it does not override it.
- **Human-in-the-loop:** sensitive, high-risk, or out-of-authority risks are referred.
- **Versioned policy:** decisions preserve `policy_version`, scoring version, and pricing version.
- **Traceability:** outputs include rule results, factors, conditions, and documentary evidence.
- **Service isolation:** Project 3 is accessed by HTTP rather than shared direct access to Qdrant.
- **Failure-safe behavior:** unavailable RAG evidence must not stop deterministic controls.
- **Portfolio realism:** all data and business logic are explicitly synthetic.

## Roadmap

- [x] Structured cyber SME submission model.
- [x] Completeness checking.
- [x] YAML-configured appetite and eligibility rules.
- [x] Referral and decline routing.
- [x] Deterministic cyber risk scoring.
- [x] Synthetic pricing indication.
- [x] Underwriting condition recommender.
- [x] Insurance Knowledge Agent integration through HTTP.
- [x] Retrieval evidence included in the underwriting response.
- [ ] Policy reconciliation between YAML rules and documentary sources.
- [ ] Retrieval status and failure metadata in the audit trail.
- [ ] Persistence of submissions, decisions, and audit events.
- [ ] Raw document integration through Project 1 Submission Extractor.
- [ ] Portfolio and claims analysis through Project 2 Data Analyst Agent.
- [ ] LLM-generated underwriter summary using verified facts and citations only.
- [ ] LangGraph orchestration with conditional routing and human-review interruption.
- [ ] Docker Compose, observability, CI/CD, and deployment hardening.

## License

This repository is intended for educational and portfolio use. Add a license appropriate to your chosen distribution model before publishing or reusing it externally.
