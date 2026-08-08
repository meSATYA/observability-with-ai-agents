---
name: incident-investigation
description: Compact evidence-first guidance for local SRE incident synthesis. Use when the agent summarizes metrics, logs, traces, runbooks, or approved incident memory.
---

# Incident investigation skill

Use only the evidence supplied in the request. Keep the application failure separate from infrastructure or LLM availability failures.

## Always

- Prefer observed metric, log, and trace values over guesses.
- State the affected service, failure signature, and confidence.
- Treat runbooks and approved incident memory as supporting context, not proof.
- Never invent telemetry, citations, or remediation results.
- Recommend reversible, approved actions only; do not execute changes.

## Signal selection

- Metrics: error rate, latency, saturation, and service labels.
- Logs: exact failure signatures and timestamps.
- Traces: request path, downstream span, and trace correlation.
- Memory: use only explicitly approved similar incidents.

## Output

Return a short root-cause explanation followed by evidence and safe next steps. If evidence conflicts or is missing, say so. A missing/slow local model is not an application root cause.
