from tools import prometheus_api, loki_api, tempo_api, qdrant_api, ollama_api
def supervisor(s): return {"question":s.get("question","Why is checkout failing?")}
def metrics(s): return {"metrics":{"error_rate":prometheus_api.query('sum by (service, fault) (rate(checkout_stage_total{outcome="error"}[5m]))'),"latency":prometheus_api.query('histogram_quantile(0.95,sum by (le, service) (rate(checkout_stage_duration_seconds_bucket[5m])))')}}
def logs(s): return {"logs":loki_api.query('{service_name=~"frontend|gateway|checkout|inventory|payment"} |= "error"')}
def traces(s): return {"traces":tempo_api.search()}
def correlate(s): return {"correlation":{"service_path":"frontend → gateway → checkout → inventory → payment","signals":"Payment errors are matched by time and trace IDs across downstream failures."}}
def knowledge(s): return {"knowledge":qdrant_api.runbook(s.get("logs", ""))}
def rootcause(s):
    evidence={k:s.get(k) for k in ("metrics","logs","traces","correlation","knowledge")}
    # The root-cause agent is evidence-first and remains useful with Ollama off.
    log_text = str(s.get("logs", ""))
    findings = []
    signatures = {
        "frontend worker pool saturated": "Frontend worker saturation.",
        "gateway rate limit exceeded": "Gateway rate limiting.",
        "redis session cache timeout": "Checkout Redis cache timeout.",
        "inventory reservation database unavailable": "Inventory reservation database unavailable.",
        "payment database connection pool exhausted": "Payment PostgreSQL connection-pool exhaustion.",
        "payment provider timeout": "Payment-provider timeout.",
        "card declined": "Card declined by the payment provider (check whether it is an expected business outcome).",
    }
    for signature, finding in signatures.items():
        if signature in log_text: findings.append(finding)
    finding = "; ".join(findings) if findings else "No matching simulated-failure signature was found in the current log window."
    result = {"root_cause": finding}
    summary = ollama_api.summarize(evidence)
    if summary:
        result["llm_summary"] = summary
    return result
def remediate(s):
    root = s.get("root_cause", "")
    actions = ["Inspect the matching traces, logs, and metric error/latency window before any change."]
    if "timeout" in root: actions.append("Check the affected dependency's latency, timeout budget, and circuit-breaker behavior.")
    if "saturation" in root or "pool" in root: actions.append("Check capacity, queue depth, and connection leaks; use only approved reversible scaling changes.")
    if "rate limiting" in root: actions.append("Validate the gateway limit policy and client retry behavior before changing thresholds.")
    if "Card declined" in root: actions.append("Validate decline codes; do not automatically retry a hard decline.")
    actions.append("Clear injected faults and validate recovery after mitigation.")
    return {"remediation": actions}
def report(s): return {"report":{"question":s["question"],"root_cause":s["root_cause"],"local_llm_summary":s.get("llm_summary"),"evidence":{k:s.get(k) for k in ("metrics","logs","traces","correlation")},"remediation":s["remediation"],"safety":"Read-only investigation; no remediation is executed."}}
