import json, os, requests
from tools.skill_context import load_context

def _compact_evidence(evidence, limit=6000):
    """Keep the summary prompt bounded; raw logs/traces can be enormous."""
    compact = {}
    for key, value in evidence.items():
        serialized = json.dumps(value, default=str)
        compact[key] = serialized[-1200:] if len(serialized) > 1200 else value
    return json.dumps(compact, default=str)[:limit]

def summarize(evidence, question=""):
    if os.getenv("ENABLE_LLM_SUMMARY", "false").lower() != "true": return None
    if not os.getenv("OLLAMA_MODEL"): return None
    # Factual metric/log/trace questions are answered directly from evidence;
    # do not spend a minute invoking a local model for a simple lookup.
    q = question.lower()
    synthesis_terms = ("why", "explain", "summarize", "root cause", "mitigation", "recommend", "assess")
    if not any(term in q for term in synthesis_terms): return None
    try:
        timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300"))
        context_size = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
        prediction_limit = int(os.getenv("OLLAMA_NUM_PREDICT", "120"))
        base_url = os.environ["OLLAMA_BASE_URL"].removesuffix("/v1")
        response = requests.post(base_url + "/api/chat", json={
            "model": os.environ["OLLAMA_MODEL"],
            "messages": [
                {"role": "system", "content": load_context(question)},
                {"role": "user", "content": _compact_evidence(evidence)},
            ],
            "stream": False,
            "keep_alive": "5m",
            "options": {"num_ctx": context_size, "num_predict": prediction_limit},
        }, timeout=timeout)
        response.raise_for_status()
        return response.json().get("message", {}).get("content")
    except Exception:
        # LLM narration is optional. Never allow an infrastructure/model error to
        # become an incident finding or to overwrite evidence-based root cause.
        return None
