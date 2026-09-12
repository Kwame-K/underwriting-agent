# Policy Reconciliation

## Purpose

This document reconciles the executable underwriting policy in Project 4 with the documentary evidence retrieved by Project 3.

The objective is to ensure that every material underwriting rule is classified as one of the following:

- **Documented rule:** directly supported by an active insurance document.
- **Internal authority rule:** an operating or delegation threshold that may be more restrictive than the underwriting guide.
- **Synthetic portfolio rule:** a demonstrative rule used for the portfolio project and not presented as an insurer rule.
- **Pending alignment:** a rule whose logic, threshold, data requirements, or source must be reconciled before it can be represented as documentary policy.

> **Scope note:** this is a portfolio project. The policy YAML, score, pricing indication, and insurance documentation are synthetic or demonstrative. This document demonstrates governance and traceability; it does not represent an insurer's binding underwriting authority.

## Source documents

| Source ID | Document | Version | Relevant sections | Status |
|---|---|---|---|---|
| `cyber_underwriting_guide_v1` | Cyber Insurance Underwriting Guide | v1 | 3. Minimum Security Controls; 4. Referral Criteria; 6. Cyber Coverage Reminder | Active portfolio document |
| `underwriting_policy.yaml` | Cyber SME Underwriting Policy | 0.4.0 | Territory, exclusions, authority, security controls, pricing, conditions | Active executable policy |

## Governance principles

1. **Deterministic rules take precedence.** Project 4 evaluates completeness, decline, referral, scoring, and pricing using Python services and versioned YAML configuration.
2. **RAG provides evidence, not authority.** Project 3 retrieves documentary passages but cannot change an underwriting decision.
3. **Documentary evidence must be traceable.** A retrieved citation must include its document ID, title, section, excerpt, retrieval score, and supported finding ID.
4. **Conflicts must be visible.** A mismatch between executable policy and retrieved documentation must never be silently treated as alignment.
5. **Coverage and underwriting are distinct.** Underwriting criteria, referral criteria, and security controls do not independently determine policy coverage, exclusions, or claim outcomes.
6. **Internal authority can be stricter.** An automated underwriting limit may be lower than the referral threshold in an underwriting guide, provided it is explicitly classified as an internal authority rule.

## Rule reconciliation matrix

| Finding ID | Executable Project 4 rule | Current Project 3 documentary evidence | Classification | Status | Required action |
|---|---|---|---|---|---|
| `UW-CYB-001` | Decline when the applicant country is not Canada | No citation yet mapped to the supported Canadian territory rule | Pending alignment | Source required | Add a territory/appetite passage to the knowledge base or classify the rule as a synthetic territorial appetite rule |
| `UW-CYB-002` | Decline for adult entertainment, cryptocurrency exchange, cryptocurrency mining, gambling, and weapons manufacturing | The Cyber Underwriting Guide referral criteria mention cryptocurrency exchange, online gambling, and critical infrastructure | Partial alignment | Reconcile | Align terminology, decide whether items are decline or referral, and add documentary support for adult entertainment, cryptocurrency mining, and weapons manufacturing if retained |
| `UW-CYB-003` | Refer when MFA is not enabled | Guide section 3 requires MFA for organizations above CAD 5 million; section 4 requires senior referral when MFA is absent for remote access | Documented for revenue above CAD 5 million | Partial alignment | Add a revenue threshold to the executable MFA rule, or label the rule as a stricter internal automated-underwriting control for smaller risks |
| `UW-CYB-004` | Refer when requested limit exceeds CAD 2 million | Guide section 4 requires senior referral when aggregate limit exceeds CAD 5 million | Internal authority rule | Source required | Keep CAD 2 million only as `max_automated_limit_cad`; add a separate documented referral threshold of CAD 5 million if that guide rule should be executed |
| `UW-CYB-005` | Refer when the applicant has more than one prior cyber claim | Guide section 4 refers applicants with a ransomware incident during the prior 36 months | Pending alignment | Data and logic gap | Extend the submission model with `prior_ransomware_incident`, `prior_ransomware_incident_date`, and possibly claim-level details; do not present claim-count logic as direct guide evidence |
| `UW-CYB-006` | Refer when annual revenue exceeds CAD 50 million | Guide section 4 requires senior referral when annual revenue exceeds CAD 50 million | Documented | Aligned | Preserve threshold and add a deterministic test linked to the documentary rule |
| `COND-001` | Require MFA for remote and privileged access | Guide section 3 requires MFA for remote access, email accounts, and privileged administrator accounts above CAD 5 million | Documented for revenue above CAD 5 million | Partial alignment | Add the revenue threshold and update wording to include email accounts where appropriate |
| `COND-002` | Require evidence that EDR is deployed and monitored | Guide section 3 requires EDR or equivalent endpoint protection above CAD 10 million | Documented for revenue above CAD 10 million | Misaligned | Trigger a mandatory EDR condition only above CAD 10 million; below the threshold, treat EDR as a risk factor or optional information request |
| `COND-003` | Require evidence of tested offline or immutable backups | Guide section 3 requires critical-system and data backups, tested at least annually, above CAD 5 million | Documented for revenue above CAD 5 million | Partial alignment | Add the revenue threshold; retain stronger immutable-backup wording only if documented elsewhere or explicitly label it as an internal control standard |
| `COND-004` | Request payment-card data processing, storage, encryption, and access-control details | No citation mapped yet | Pending alignment | Source required | Add a PCI/data-security guide or classify as a synthetic information-request template |
| `COND-005` | Request details of prior cyber incidents and remediation | The guide supports a narrower ransomware-within-36-months referral condition | Partial alignment | Reconcile | Link the condition to claim details; add date and ransomware fields to the submission model before asserting direct guide support |
| `COND-006` | Require an enhanced cybersecurity controls review for HIGH or SEVERE risk bands | No direct source; risk bands are generated by the Project 4 synthetic scoring model | Synthetic portfolio rule | Approved as synthetic | Document as an internal portfolio-control step, not a rule extracted from an underwriting guide |
| `COND-007` | Request added exposure and controls documentation above CAD 1 million limit | Guide documents referral above CAD 5 million, not this information-request threshold | Internal authority rule | Source required | Keep as an internal information-request practice or add a supporting capacity/authority source |
| `RSK-001` to `RSK-010` | Deterministic points-based cyber score | No direct documentary source required; score is a synthetic technical model | Synthetic portfolio model | Approved as synthetic | Maintain a model card and avoid presenting factor weights as insurer pricing or underwriting standards |
| Pricing indication | Base-rate and factor-based synthetic premium indication | No pricing guide citation mapped yet | Synthetic portfolio model | Approved as synthetic | Maintain explicit non-commercial disclaimer and version the pricing model independently |

## Confirmed documentary evidence

### MFA requirement and referral

**Finding:** `UW-CYB-003`

**Document:** Cyber Insurance Underwriting Guide

**Relevant evidence:**

> For organizations with annual revenue above CAD 5 million, multi-factor authentication must be enabled for remote access, email accounts, and privileged administrator accounts.

> The submission must be referred to a senior underwriter if the applicant does not use multi-factor authentication for remote access.

**Executable interpretation:**

```text
If annual_revenue_cad > 5,000,000
and mfa_enabled is False
then REFER
and recommend the MFA underwriting condition.
```

### EDR requirement

**Finding:** `COND-002`

**Document:** Cyber Insurance Underwriting Guide

**Relevant evidence:**

> Endpoint detection and response or equivalent endpoint protection is required for organizations with annual revenue above CAD 10 million.

**Executable interpretation:**

```text
If annual_revenue_cad > 10,000,000
and endpoint_detection_response is not True
then add a required EDR control condition.

If annual_revenue_cad <= 10,000,000
and endpoint_detection_response is not True
then retain a scoring penalty or request confirmation,
but do not represent EDR as a documented mandatory condition.
```

### Backup requirement

**Finding:** `COND-003`

**Document:** Cyber Insurance Underwriting Guide

**Relevant evidence:**

> The applicant must maintain backups of critical systems and data. Backups must be tested at least annually.

**Executable interpretation:**

```text
If annual_revenue_cad > 5,000,000
and offline_backups is not True
then request evidence of backups and annual testing.
```

The phrase "offline or immutable backups" is a stronger condition than the current retrieved excerpt. It must be supported by a separate source or labeled as an internal portfolio-control standard.

### Revenue referral threshold

**Finding:** `UW-CYB-006`

**Document:** Cyber Insurance Underwriting Guide

**Relevant evidence:**

> The submission must be referred to a senior underwriter if annual revenue exceeds CAD 50 million.

**Executable interpretation:**

```text
If annual_revenue_cad > 50,000,000
then REFER.
```

## Required data-model enhancements

The current `InsuranceSubmission` model is sufficient for the initial portfolio demonstration, but the following fields are needed to align more closely with the documented referral criteria:

| New field | Type | Reason |
|---|---|---|
| `prior_ransomware_incident` | `bool | None` | Distinguish ransomware from other cyber claims |
| `prior_ransomware_incident_date` | `date | None` | Evaluate the 36-month referral window |
| `mfa_remote_access_enabled` | `bool | None` | Match the guide's remote-access requirement precisely |
| `mfa_email_enabled` | `bool | None` | Match the guide's email-account requirement precisely |
| `mfa_privileged_access_enabled` | `bool | None` | Match the guide's privileged-account requirement precisely |
| `backup_testing_frequency_months` | `int | None` | Verify annual backup testing |
| `endpoint_protection_type` | `str | None` | Allow EDR or equivalent endpoint protection |
| `requested_aggregate_limit_cad` | `float | None` | Distinguish aggregate limit from another limit field if required by the source document |

## Planned policy changes

### Phase 1 — Immediate alignment

- Add explicit revenue thresholds for documented MFA, backup, and EDR requirements.
- Reclassify the CAD 2 million threshold as an internal automated-authority threshold.
- Preserve the CAD 50 million revenue referral rule as a documented rule.
- Update condition wording so it does not claim documentary support beyond the available source excerpt.
- Add unit tests for boundary values at CAD 5 million, CAD 10 million, and CAD 50 million.

### Phase 2 — Data-model alignment

- Add structured ransomware and incident-date fields.
- Split the single MFA field into remote, email, and privileged-access controls if the product requires exact source alignment.
- Add backup-test frequency and endpoint-protection details.
- Update completeness requirements based on the refined fields.

### Phase 3 — Evidence governance

- Attach `source_document_id`, `section_reference`, and `citation_id` to rule metadata or policy-reconciliation records.
- Add `evidence_retrieval_status` to `UnderwritingDecision`.
- Record `SUCCESS`, `PARTIAL`, `INSUFFICIENT_CONTEXT`, and `UNAVAILABLE` states in the audit trail.
- Add tests ensuring that missing or unavailable RAG evidence never changes deterministic decision outcomes.

## Evidence-status policy

| Status | Meaning | Impact on underwriting decision |
|---|---|---|
| `SUCCESS` | Relevant evidence retrieved for all requested findings | Attach citations to the decision |
| `PARTIAL` | Some requested findings have evidence; others do not | Preserve decision; display unresolved findings |
| `INSUFFICIENT_CONTEXT` | No finding has a source above the retrieval threshold | Preserve decision; do not claim documentary support |
| `UNAVAILABLE` | Knowledge Agent is unavailable, times out, or returns an invalid response | Preserve decision; log failure and flag the decision for evidence follow-up if appropriate |

## Approval and change record

| Date | Policy version | Change | Status |
|---|---|---|---|
| 2026-09-10 | 0.4.0 | Initial reconciliation created after live RAG retrieval for MFA referral evidence | Open: alignment changes pending |

## Next implementation step

Implement the Phase 1 threshold alignment in Project 4, then add decision-level evidence-retrieval status and resilience tests before introducing Groq-based underwriter summaries or LangGraph orchestration.
