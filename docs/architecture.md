# Architecture and agent workflow

The UI can activate one failure mode per service and multiple services at once.
The Agent API clears unselected modes, activates selected modes, and generates
traffic both through the normal request chain and directly to selected services.
This produces evidence even when an upstream failure prevents normal propagation.

```mermaid
flowchart TB
    U["User"] --> UI["Local UI :5173"]
    UI --> FS["Multi-select fault simulation"]
    FS --> API["Agent API :8081"]
    API --> CTRL["Activate selected service modes\nand generate concurrent traffic"]

    CTRL --> FE["Frontend\noverload"]
    FE --> GW["Gateway\nrate limit"]
    GW --> CO["Checkout\nRedis timeout"]
    CO --> IN["Inventory\ndatabase outage"]
    IN --> PA["Payment\nDB pool / provider timeout / card decline"]
    PA --> DB[("PostgreSQL")]
    CO --> R[("Redis")]

    FE & GW & CO & IN & PA --> OTEL["OpenTelemetry Collector\nOTLP HTTP/gRPC ingress"]
    OTEL --> TR["Tempo\ntraces"]
    OTEL --> LO["Loki\nlogs"]
    OTEL --> PR["Prometheus\nmetrics"]
    PR --> VM["VictoriaMetrics\nremote-write store"]
    TR & LO & PR & VM --> GF["Grafana\nExplore + dashboard"]

    UI --> Q["Question preset"]
    Q --> SUP["Supervisor"]
    SUP --> MA["Metrics query\nPrometheus"]
    SUP --> LA["Logs query\nLoki"]
    SUP --> TA["Traces query\nTempo"]
    MA & LA & TA --> CA["Correlation"]
    CA --> KA["Knowledge\nlocal Markdown runbook\n(Qdrant extension point)"]
    CA & KA --> RCA["Evidence-based root cause"]
    RCA --> RA["Safety-gated remediation advice"]
    RA --> REP["Human-readable report"]
    OL["Ollama (optional)\nsummary only"] --> RCA
```

## Execution boundaries

- Each query client has a three-second timeout and returns partial evidence on
  backend errors.
- Root-cause detection uses known fault signatures in current logs; it does not
  depend on Ollama.
- Ollama, when enabled, is capped at 12 seconds and contributes only the
  `local_llm_summary` report field.
- No remediation is executed by the agent.
