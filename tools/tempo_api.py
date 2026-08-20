import os

import requests


def traces_for_ids(trace_ids, limit=20):
    """Fetch only the traces observed in the current Loki result set.

    Tempo search is intentionally broad and can return unrelated recent traces.
    Looking up the IDs directly keeps the report's trace evidence tied to the
    current incident window and makes missing exports explicit.
    """
    unique_ids = list(dict.fromkeys(str(trace_id).lower() for trace_id in trace_ids if trace_id))[:limit]
    found, missing, errors = [], [], []
    for trace_id in unique_ids:
        try:
            response = requests.get(
                f"{os.environ['TEMPO_URL']}/api/traces/{trace_id}", timeout=3
            )
            if response.ok:
                found.append({"traceID": trace_id, "data": response.json()})
            elif response.status_code == 404:
                missing.append(trace_id)
            else:
                errors.append({"traceID": trace_id, "status": response.status_code})
        except requests.RequestException as exc:
            errors.append({"traceID": trace_id, "error": str(exc)})
    return {"traces": found, "missing_trace_ids": missing, "errors": errors}


def search(traceql='{ status = error }', trace_ids=None):
    if trace_ids:
        return traces_for_ids(trace_ids)
    try:
        r = requests.get(
            os.environ["TEMPO_URL"] + "/api/search",
            params={"q": traceql, "limit": 20},
            timeout=3,
        )
        return r.json() if r.ok else {"error": r.text}
    except requests.RequestException as exc:
        return {"error": f"Tempo query unavailable: {exc}"}
