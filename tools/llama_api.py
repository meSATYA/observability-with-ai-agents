import json
import logging
import os
import time

import requests
from prometheus_client import Counter, Histogram

from tools.skill_context import load_context

logger = logging.getLogger(__name__)

LLAMA_REQUESTS = Counter(
    "agent_llama_requests_total",
    "llama.cpp summary requests by outcome",
    ["status"],
)
LLAMA_REQUEST_LATENCY = Histogram(
    "agent_llama_request_duration_seconds",
    "llama.cpp summary request latency",
    ["status"],
)
LLAMA_PROMPT_TOKENS = Counter(
    "agent_llama_prompt_tokens_total",
    "Prompt tokens reported by llama.cpp",
)
LLAMA_COMPLETION_TOKENS = Counter(
    "agent_llama_completion_tokens_total",
    "Completion tokens reported by llama.cpp",
)


def _finish(status, started, payload=None):
    LLAMA_REQUESTS.labels(status=status).inc()
    LLAMA_REQUEST_LATENCY.labels(status=status).observe(time.perf_counter() - started)
    if payload:
        usage = payload.get("usage", {})
        LLAMA_PROMPT_TOKENS.inc(float(usage.get("prompt_tokens", 0)))
        LLAMA_COMPLETION_TOKENS.inc(float(usage.get("completion_tokens", 0)))


def _compact_evidence(evidence, limit=6000):
    """Keep the synthesis prompt bounded; raw logs and traces can be enormous."""
    compact = {}
    for key, value in evidence.items():
        serialized = json.dumps(value, default=str)
        # Keep the beginning for structured findings and the end for recent logs.
        compact[key] = (serialized[:900] + " … " + serialized[-900:]) if len(serialized) > 1800 else value
    return json.dumps(compact, default=str)[:limit]


def summarize_result(evidence, question="", root_cause=""):
    started = time.perf_counter()
    if os.getenv("ENABLE_LLM_SUMMARY", "false").lower() != "true":
        logger.info("llama.cpp summary disabled by ENABLE_LLM_SUMMARY")
        _finish("disabled", started)
        return {"summary": None, "status": "disabled"}
    if not os.getenv("LLAMA_MODEL"):
        logger.warning("llama.cpp summary skipped: LLAMA_MODEL is not configured")
        _finish("not_configured", started)
        return {"summary": None, "status": "not_configured"}
    # Factual metric/log/trace questions are answered directly from evidence.
    q = question.lower()
    synthesis_terms = ("why", "explain", "summarize", "root cause", "mitigation", "recommend", "assess")
    if not any(term in q for term in synthesis_terms):
        logger.info("llama.cpp summary skipped for factual question: %s", question)
        _finish("factual_query", started)
        return {"summary": None, "status": "factual_query"}
    try:
        timeout = float(os.getenv("LLAMA_TIMEOUT_SECONDS", "300"))
        system_prompt = load_context(question) + (
            " You are a constrained incident explainer. The deterministic root-cause finding "
            "and observed signatures below are authoritative. Explain those exact findings; "
            "do not replace them with a new primary cause inferred from service topology. "
            "Clearly separate primary failures from downstream impact."
        )
        user_prompt = (
            f"QUESTION:\n{question}\n\n"
            f"DETERMINISTIC ROOT CAUSE (AUTHORITATIVE):\n{root_cause or 'Not available'}\n\n"
            f"EVIDENCE:\n{_compact_evidence(evidence)}\n\n"
            "Write a concise explanation with: (1) each observed failure signature, "
            "(2) the likely mechanism for that signature, (3) downstream effects, "
            "and (4) one verification step per signature. Do not claim evidence that is absent."
        )
        response = requests.post(
            os.getenv("LLAMA_BASE_URL", "http://llama-cpp:8080/v1").rstrip("/") + "/chat/completions",
            json={
                "model": os.environ["LLAMA_MODEL"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "max_tokens": int(os.getenv("LLAMA_NUM_PREDICT", "120")),
                "stream": False,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        summary = payload.get("choices", [{}])[0].get("message", {}).get("content")
        status = "completed" if summary else "empty_response"
        _finish(status, started, payload)
        return {"summary": summary, "status": status}
    except Exception as exc:
        # Narration is optional. Never let model/server errors overwrite evidence.
        logger.exception("llama.cpp summary request failed")
        _finish("error", started)
        return {"summary": None, "status": "error", "error": str(exc)[:300]}


def summarize(evidence, question="", root_cause=""):
    """Backward-compatible summary-only helper for legacy graph code."""
    return summarize_result(evidence, question, root_cause).get("summary")
