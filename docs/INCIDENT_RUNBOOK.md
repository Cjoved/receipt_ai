# Incident Runbook (AI Ops)

Operational response runbook for high-impact AI incidents in `receipt_ai`.

## 1) Scope

Use this runbook for incidents impacting:
- RAG answer quality/grounding/citations
- extraction and indexing integrity
- retrieval availability (Qdrant or JSON fallback)
- sensitive data safety in prompts/outputs/logs

## 2) Incident Taxonomy

- **Hallucination spike**: answers unsupported by retrieved context.
- **Citation mismatch/fabrication**: source metadata missing/incorrect for claimed facts.
- **Prompt injection-like behavior**: model follows malicious instructions from retrieved text.
- **Data leakage risk**: sensitive content appears in output/logs.
- **Provider outage/rate limiting**: model API errors, high latency, timeouts.
- **Indexing/retrieval outage**: newly indexed docs not retrievable or zero-hit spikes.

## 3) Severity and Ownership

### Severity Levels
- **SEV-1 Critical**
  - active leakage risk, broad wrong answers, auth/access boundary risk.
  - target: immediate containment.
- **SEV-2 High**
  - major degradation for core AI flows without confirmed leakage.
  - target: same-day containment + recovery.
- **SEV-3 Medium**
  - partial degradation or non-critical feature instability.
  - target: scheduled fix with monitoring.

### Ownership
- **Incident Lead**: primary owner coordinating containment/recovery.
- **AI Engineer**: prompt/retrieval/indexing diagnosis and remediation.
- **App/Platform Engineer**: deployment/config/runtime mitigation.
- **Security Owner** (if needed): leakage and key rotation response.

## 4) Immediate Response Flow

1. **Declare**
   - classify SEV level and assign incident lead.
2. **Contain**
   - disable risky prompt/path if required,
   - force safe fallback mode where possible,
   - restrict impacted endpoints/features temporarily if needed.
3. **Protect**
   - rotate credentials immediately if exposure is suspected.
4. **Diagnose**
   - isolate root stage: extraction, indexing, retrieval, prompt, provider.
5. **Recover**
   - deploy minimal safe fix first, then full corrective patch.
6. **Validate**
   - rerun checks from `docs/EVALUATION.md` and `docs/RELEASE_CHECKLIST.md`.
7. **Document**
   - publish incident summary and prevention actions.

## 5) Containment Actions by Incident Type

### A) Hallucination / Citation Incident
- tighten or revert recent prompt changes,
- reduce unsafe behavior surface (more conservative answer policy),
- verify retrieval quality and citation attachment.

### B) Injection-like Behavior
- harden instruction hierarchy and sanitization behavior,
- reject unsafe instruction patterns from context,
- review exposure scope and user impact.

### C) Leakage Risk
- stop affected flow if needed,
- rotate keys/tokens,
- remove/redact leaked logs/output artifacts.

### D) Provider Outage/Rate Limit
- activate fallback provider/model strategy if available,
- reduce request concurrency / retry safely,
- degrade gracefully with explicit user-safe errors.

### E) Index/Retrieval Outage
- validate indexing pipeline completion,
- validate backend mode parity (Qdrant vs JSON fallback),
- reindex affected dataset when required.

## 6) Recovery Validation Checklist

- [ ] Root cause identified and mapped to pipeline stage.
- [ ] Immediate risk is contained.
- [ ] Baseline evaluation rerun (`docs/EVALUATION.md`).
- [ ] Release checklist AI gates rerun (`docs/RELEASE_CHECKLIST.md`).
- [ ] No new security issues introduced (`docs/SECURITY_AI.md`).

## 7) Post-Incident Template

```md
Incident ID:
Date/Time:
Severity:
Incident Lead:

Summary:
Impacted surface:
- <chat | extraction | retrieval | indexing | auth boundary>

User impact:
Blast radius:
Detection signal:

Root cause:
Contributing factors:

Containment actions:
Recovery actions:
Validation evidence:

Preventive actions:
Owner(s):
Target completion date:
```

## 8) Related Docs

- `docs/OBSERVABILITY.md`
- `docs/EVALUATION.md`
- `docs/SECURITY_AI.md`
- `docs/RELEASE_CHECKLIST.md`
- `AGENT.md`
