import json
import logging
import os

import requests

from tools.skill_context import load_context

logger = logging.getLogger(__name__)


def _compact_evidence(evidence, limit=6000):
    """Keep the synthesis prompt bounded; raw logs and traces can be enormous."""
    compact = {}
    for key, value in evidence.items():
        serialized = json.dumps(value, default=str)
        compact[key] = serialized[-1200:] if len(serialized) > 1200 else value
    return json.dumps(compact, default=str)[:limit]


def summarize(evidence, question=""):
    if os.getenv("ENABLE_LLM_SUMMARY", "false").lower() != "true":
        logger.info("llama.cpp summary disabled by ENABLE_LLM_SUMMARY")
        return None
    if not os.getenv("LLAMA_MODEL"):
        logger.warning("llama.cpp summary skipped: LLAMA_MODEL is not configured")
        return None
    # Factual metric/log/trace questions are answered directly from evidence.
    q = question.lower()
    synthesis_terms = ("why", "explain", "summarize", "root cause", "mitigation", "recommend", "assess")
    if not any(term in q for term in synthesis_terms):
        logger.info("llama.cpp summary skipped for factual question: %s", question)
        return None
    try:
        timeout = float(os.getenv("LLAMA_TIMEOUT_SECONDS", "300"))
        response = requests.post(
            os.getenv("LLAMA_BASE_URL", "http://llama-cpp:8080/v1").rstrip("/") + "/chat/completions",
            json={
                "model": os.environ["LLAMA_MODEL"],
                "messages": [
                    {"role": "system", "content": load_context(question)},
                    {"role": "user", "content": _compact_evidence(evidence)},
                ],
                "temperature": 0.1,
                "max_tokens": int(os.getenv("LLAMA_NUM_PREDICT", "120")),
                "stream": False,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json().get("choices", [{}])[0].get("message", {}).get("content")
    except Exception:
        # Narration is optional. Never let model/server errors overwrite evidence.
        logger.exception("llama.cpp summary request failed")
        return None
