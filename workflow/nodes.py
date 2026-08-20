import json
import re

from tools import llama_api, loki_api, prometheus_api, qdrant_api, tempo_api


FAILURE_SIGNATURES = {
    "frontend_overloaded": {
        "patterns": ("frontend worker pool saturated", "frontend worker saturation"),
        "finding": "Frontend worker saturation.",
    },
    "gateway_rate_limited": {
        "patterns": ("gateway rate limit exceeded", "gateway rate limiting"),
        "finding": "Gateway rate limiting.",
    },
    "redis_timeout": {
        "patterns": ("redis session cache timeout", "checkout redis cache timeout", "redis cache timeout"),
        "finding": "Checkout Redis cache timeout.",
    },
    "inventory_unavailable": {
        "patterns": ("inventory reservation database unavailable", "inventory unavailable"),
        "finding": "Inventory reservation database unavailable.",
    },
    "payment_db_pool": {
        "patterns": (
            "payment database connection pool exhausted",
            "payment postgresql connection-pool exhaustion",
            "payment db pool",
        ),
        "finding": "Payment PostgreSQL connection-pool exhaustion.",
    },
    "gateway_timeout": {
        "patterns": ("payment provider timeout", "payment-provider timeout", "provider timeout"),
        "finding": "Payment-provider timeout.",
    },
    "card_declined": {
        "patterns": ("card declined", "card payment declined"),
        "finding": "Card declined by the payment provider (check whether it is an expected business outcome).",
    },
}
TRACE_ID_PATTERN = re.compile(r'"trace_id"\s*:\s*"([0-9a-f]{32})"', re.IGNORECASE)


def _failure_classes(text):
    lowered = str(text).lower()
    return {
        key
        for key, signature in FAILURE_SIGNATURES.items()
        if any(pattern in lowered for pattern in signature["patterns"])
    }


def _trace_ids_from_logs(logs):
    """Extract IDs from the current Loki response only."""
    ids = []
    for stream in logs if isinstance(logs, list) else []:
        metadata = stream.get("stream", {}) if isinstance(stream, dict) else {}
        candidate = metadata.get("trace_id") if isinstance(metadata, dict) else None
        if candidate:
            ids.append(str(candidate).lower())
        for value in stream.get("values", []) if isinstance(stream, dict) else []:
            line = value[1] if isinstance(value, (list, tuple)) and len(value) > 1 else ""
            if isinstance(line, dict):
                candidate = line.get("trace_id")
                if candidate:
                    ids.append(str(candidate).lower())
            else:
                match = TRACE_ID_PATTERN.search(str(line))
                if match:
                    ids.append(match.group(1).lower())
    return list(dict.fromkeys(ids))


def _trace_ids_from_tempo(traces):
    """Extract IDs from the current Tempo lookup/search response only."""
    items = traces.get("traces", []) if isinstance(traces, dict) else []
    ids = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        candidate = item.get("traceID") or item.get("trace_id")
        if candidate:
            ids.append(str(candidate).lower())
    return list(dict.fromkeys(ids))


def _similar_incident_ids(candidates, current_classes):
    """Return IDs only, and only for the same active failure class."""
    if not current_classes:
        return []
    ids = []
    for candidate in candidates if isinstance(candidates, list) else []:
        if not isinstance(candidate, dict):
            continue
        candidate_text = f"{candidate.get('question', '')} {candidate.get('root_cause', '')}"
        if current_classes.intersection(_failure_classes(candidate_text)):
            incident_id = candidate.get("incident_id")
            if incident_id and incident_id not in ids:
                ids.append(incident_id)
    return ids


def supervisor(s): return {"question": s.get("question", "Why is checkout failing?")}
def metrics(s): return {"metrics": {"error_rate": prometheus_api.query('sum by (service, fault) (rate(checkout_stage_total{outcome="error"}[5m]))'), "latency": prometheus_api.query('histogram_quantile(0.95,sum by (le, service) (rate(checkout_stage_duration_seconds_bucket[5m])))')}}
def logs(s): return {"logs": loki_api.query('{service_name=~"frontend|gateway|checkout|inventory|payment"} |= "error"')}
def traces(s): return {"traces": tempo_api.search(trace_ids=_trace_ids_from_logs(s.get("logs", [])))}


def correlate(s):
    log_ids = _trace_ids_from_logs(s.get("logs", []))
    tempo_ids = _trace_ids_from_tempo(s.get("traces", {}))
    tempo_id_set = set(tempo_ids)
    matched = [trace_id for trace_id in log_ids if trace_id in tempo_id_set]
    return {"correlation": {
        "scope": "current_investigation",
        "service_path": "frontend → gateway → checkout → inventory → payment",
        "current_log_trace_ids": log_ids,
        "current_tempo_trace_ids": tempo_ids,
        "matched_trace_ids": matched,
        "log_only_trace_ids": [trace_id for trace_id in log_ids if trace_id not in tempo_id_set],
        "signals": "Correlated from the current Loki and Tempo responses; historical incidents are excluded.",
    }}


def knowledge(s):
    context = f"{s.get('question', '')} {s.get('logs', '')} {s.get('correlation', '')}"
    candidates = qdrant_api.search_similar(context)
    current_classes = _failure_classes(s.get("logs", ""))
    return {
        "knowledge": qdrant_api.runbook(s.get("logs", "")),
        "similar_incidents": _similar_incident_ids(candidates, current_classes),
    }


def rootcause(s):
    evidence = {k: s.get(k) for k in ("metrics", "logs", "traces", "correlation", "knowledge", "similar_incidents")}
    # The root-cause agent is evidence-first and remains useful with local LLM narration off.
    findings = [signature["finding"] for key, signature in FAILURE_SIGNATURES.items() if key in _failure_classes(s.get("logs", ""))]
    finding = "; ".join(findings) if findings else "No matching simulated-failure signature was found in the current log window."
    evidence["observed_signatures"] = findings
    result = {"root_cause": finding}
    llm = llama_api.summarize_result(evidence, s.get("question", ""), finding)
    result["llm_status"] = llm["status"]
    if llm.get("error"):
        result["llm_error"] = llm["error"]
    if llm.get("summary"):
        result["llm_summary"] = llm["summary"]
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
def report(s): return {"report":{"incident_id":s.get("incident_id"),"question":s["question"],"root_cause":s["root_cause"],"local_llm_summary":s.get("llm_summary"),"local_llm_status":s.get("llm_status","unknown"),"local_llm_error":s.get("llm_error"),"similar_incidents":s.get("similar_incidents",[]),"evidence":{k:s.get(k) for k in ("metrics","logs","traces","correlation")},"remediation":s["remediation"],"safety":"Read-only investigation; memory writes require explicit approval; no remediation is executed."}}
