import os, requests
def query(q):
    try:
        r=requests.get(os.environ["PROMETHEUS_URL"]+"/api/v1/query",params={"query":q},timeout=3)
        r.raise_for_status(); return r.json()["data"]["result"]
    except requests.RequestException as exc:
        return {"error": f"Prometheus query unavailable: {exc}"}
