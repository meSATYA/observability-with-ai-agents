# Agent workflow

Supervisor → {Metrics, Traces, Logs} → Correlation → Knowledge → Root Cause → Remediation → Report.

The initial executable graph sequences the specialist calls so its evidence is deterministic. The next engineering step is to fan out Metrics/Traces/Logs concurrently, retain their individual timestamps, and add a human-approval edge before any action tool.

## End-to-end project flow

```mermaid
flowchart TB
    U["User: Inject Failure / Why is checkout failing?"] --> UI["Local UI :5173"]
    UI --> API["Agent API :8081"]
    API --> F["Inject payment fault + generate checkout traffic"]

    F --> FE["Frontend"]
    FE --> GW["Gateway"]
    GW --> CO["Checkout"]
    CO --> IN["Inventory"]
    IN --> PA["Payment"]
    PA --> DB[("PostgreSQL")]
    CO --> R[("Redis")]

    FE & GW & CO & IN & PA --> OTEL["OpenTelemetry Collector"]
    OTEL --> TR["Tempo<br/>traces"]
    OTEL --> LO["Loki<br/>logs"]
    OTEL --> PR["Prometheus<br/>metrics"]
    PR --> VM["VictoriaMetrics<br/>longer-term metrics"]
    TR & LO & PR & VM --> GF["Grafana<br/>Explore + dashboard"]

    API --> SUP["Supervisor Agent"]
    SUP --> MA["Metrics Agent"]
    SUP --> TA["Trace Agent"]
    SUP --> LA["Logs Agent"]
    MA & TA & LA --> CA["Correlation Agent"]
    CA --> KA["Knowledge Agent"]
    KA --> Q[("Qdrant + local runbooks")]
    CA --> RCA["Root Cause Agent"]
    KA --> RCA
    RCA --> RA["Remediation Agent"]
    RA --> REP["Human-readable report"]
    OL["Ollama (optional local LLM)"] --> RCA
```
