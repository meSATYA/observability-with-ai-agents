import json, os

def _compact_evidence(evidence, limit=12000):
    """Keep the summary prompt bounded; raw logs/traces can be enormous."""
    compact = {}
    for key, value in evidence.items():
        serialized = json.dumps(value, default=str)
        compact[key] = serialized[-2500:] if len(serialized) > 2500 else value
    return json.dumps(compact, default=str)[:limit]

def summarize(evidence):
    if os.getenv("ENABLE_LLM_SUMMARY", "false").lower() != "true": return None
    if not os.getenv("OLLAMA_MODEL"): return None
    try:
        from openai import OpenAI
        timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))
        c=OpenAI(base_url=os.environ["OLLAMA_BASE_URL"],api_key="local", timeout=timeout, max_retries=0)
        return c.chat.completions.create(model=os.environ["OLLAMA_MODEL"],messages=[{"role":"system","content":"Act as a cautious SRE. Use only supplied evidence; do not recommend unapproved changes."},{"role":"user","content":_compact_evidence(evidence)}], max_tokens=400).choices[0].message.content
    except Exception:
        # LLM narration is optional. Never allow an infrastructure/model error to
        # become an incident finding or to overwrite evidence-based root cause.
        return None
