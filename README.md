# AI Observability Lab — entirely local

This is a production-debugging simulation, not an autonomous remediator. A user clicks **Inject Failure**, generates checkout requests, and asks **“Why is checkout failing?”**. The agent API runs a LangGraph workflow with a Supervisor, Metrics, Traces, Logs, Correlation, Knowledge, Root Cause, and Remediation stages. The remediation stage only recommends human-approved actions.

## Architecture

`Frontend → Gateway → Checkout → Inventory → Payment`

Every service exports OpenTelemetry traces, metrics, and logs to the local Collector. The Collector sends them to Tempo, Prometheus, and Loki. Prometheus remote-writes a copy to VictoriaMetrics. Grafana has all sources provisioned. The five-agent evidence fan-in is then passed to an optional local Ollama model; Qdrant is available for local runbook memory.

## Start

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Open these local-only endpoints:

- UI: http://localhost:5173
- Grafana: http://localhost:3000 (`admin` / `admin`)
- Agent API: http://localhost:8081/docs

Pull a local model once (optional, enables natural-language root-cause synthesis):

```powershell
docker compose exec ollama ollama pull llama3.2:3b
```

Ollama is optional. If the model has not been pulled or is unavailable, the
evidence-based root-cause report still runs; only the optional
`local_llm_summary` field is omitted.

The report is evidence-first and completes without waiting for an LLM. To opt
into a bounded (12-second) local LLM summary, add `ENABLE_LLM_SUMMARY=true` to
`.env` and recreate `agent-api`.

## Exercise the workflow

1. In the UI, select any combination of failure simulations. One failure mode is
   allowed per service: frontend overload, gateway rate limit, checkout Redis
   timeout, inventory database outage, and three Payment modes (database-pool
   exhaustion, provider timeout, or card decline).
2. Generate traffic (repeat `/checkout` requests from http://localhost:8080/checkout, or run `make demo`).
3. Click **Why is checkout failing?**.
4. Review the report and Grafana correlations. Clear the failure when finished.

Wait 10 seconds after injecting the failure: traces and logs are batched, and the
lab exports metrics every 5 seconds. In Grafana Explore, use `checkout_stage_total`
in VictoriaMetrics, `{service_name="payment"}` in Loki, and search Tempo for the
`payment` service.

For pipeline diagnostics, the Collector health endpoint is `http://localhost:13133`.
Its logs show `debug` exporter batch counts for each received signal.

Each simulated Payment fault propagates upstream and produces matching error logs,
error spans, and latency/error metrics. The root-cause and remediation stages
select their evidence-backed findings and local runbook accordingly.

## Project map

- `apps/`: five independently named, OpenTelemetry-instrumented services.
- `otel/`: Collector fan-out configuration.
- `grafana/`, `victoriametrics/`, `tempo/`, `loki/`, `prometheus/`: local observability components.
- `agents/` and `langgraph/`: specialist responsibilities and graph source. `workflow/` hosts the executable wrapper, avoiding a Python import-name collision with LangGraph itself.
- `tools/`: narrow query clients; agent code has no write access to observability backends.
- `faults/`, `runbooks/`, `vectorstore/`, `ui/`, `tests/`, `docs/`: exercise, knowledge, presentation, and verification surfaces.

## Safety boundaries

The current system is deliberately **read-only** after failure injection. Any future remediation tool should be a separate, allowlisted capability that requires explicit human approval. Also apply time windows, result limits, query budgets, and evidence citations before using the design against real systems.

Grafana’s [Tempo local quickstart](https://grafana.com/docs/tempo/latest/docker-example/) and [Loki native OpenTelemetry ingestion guide](https://grafana.com/docs/loki/latest/send-data/otel/) informed the local telemetry topology.
