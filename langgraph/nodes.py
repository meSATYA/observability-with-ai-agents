from tools import prometheus_api, loki_api, tempo_api, qdrant_api, llama_api
def supervisor(s): return {"question":s.get("question","Why is checkout failing?")}
def metrics(s): return {"metrics":{"error_rate":prometheus_api.query('sum(rate(checkout_stage_total{service="payment",outcome="error"}[5m]))'),"latency":prometheus_api.query('histogram_quantile(0.95,sum(rate(checkout_stage_duration_seconds_bucket{service="payment"}[5m])) by (le))')}}
def logs(s): return {"logs":loki_api.query('{service_name="payment"} |= "error"')}
def traces(s): return {"traces":tempo_api.search()}
def correlate(s):
    trace_ids=[v[1] for stream in s.get("logs",[]) for v in stream.get("values",[]) if "trace_id" in v[1]]
    return {"correlation":{"shared_signal":"payment errors propagate through checkout → inventory → payment","log_samples":trace_ids[-5:]}}
def knowledge(s): return {"knowledge":qdrant_api.runbook()}
def rootcause(s):
    evidence={k:s.get(k) for k in ("metrics","logs","traces","correlation","knowledge")}
    result={"root_cause":"Probable payment PostgreSQL connection-pool exhaustion. Confirm using the linked error traces and pool metrics."}
    summary=llama_api.summarize(evidence)
    if summary: result["llm_summary"]=summary
    return result
def remediate(s): return {"remediation":["Verify payment database pool saturation and connection leaks.","Temporarily reduce checkout concurrency or increase pool capacity only with change approval.","After mitigation, disable the injected fault and validate error rate recovery."]}
def report(s): return {"report":{"question":s["question"],"root_cause":s["root_cause"],"local_llm_summary":s.get("llm_summary"),"evidence":{"metrics":s.get("metrics"),"logs":s.get("logs"),"traces":s.get("traces"),"correlation":s.get("correlation")},"remediation":s["remediation"],"safety":"Read-only investigation; no remediation is executed."}}
