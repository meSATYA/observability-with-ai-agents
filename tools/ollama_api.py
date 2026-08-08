import os
def summarize(evidence):
    if os.getenv("ENABLE_LLM_SUMMARY", "false").lower() != "true": return None
    if not os.getenv("OLLAMA_MODEL"): return None
    try:
        from openai import OpenAI
        c=OpenAI(base_url=os.environ["OLLAMA_BASE_URL"],api_key="local", timeout=12.0, max_retries=0)
        return c.chat.completions.create(model=os.environ["OLLAMA_MODEL"],messages=[{"role":"system","content":"Act as a cautious SRE. Use only supplied evidence; do not recommend unapproved changes."},{"role":"user","content":str(evidence)}]).choices[0].message.content
    except Exception:
        # LLM narration is optional. Never allow an infrastructure/model error to
        # become an incident finding or to overwrite evidence-based root cause.
        return None
