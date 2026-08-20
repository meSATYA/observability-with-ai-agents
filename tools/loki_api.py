import os, time, requests
def query(q):
    try:
        r=requests.get(os.environ["LOKI_URL"]+"/loki/api/v1/query_range",params={"query":q,"start":int((time.time()-300)*1e9),"end":int(time.time()*1e9),"limit":50},timeout=3)
        r.raise_for_status(); return r.json()["data"]["result"]
    except requests.RequestException as exc:
        return {"error": f"Loki query unavailable: {exc}"}
