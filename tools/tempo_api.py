import os, requests
def search(traceql='{ status = error }'):
    try:
        r=requests.get(os.environ["TEMPO_URL"]+"/api/search",params={"q":traceql,"limit":20},timeout=3)
        return r.json() if r.ok else {"error":r.text}
    except requests.RequestException as exc:
        return {"error": f"Tempo query unavailable: {exc}"}
