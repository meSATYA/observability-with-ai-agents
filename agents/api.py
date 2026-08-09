import os, requests, uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field
from tools import qdrant_api
from workflow.graph import build_graph
app=FastAPI(title="Local SRE multi-agent API"); graph=build_graph()
app.mount("/metrics", make_asgi_app())
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
class Investigation(BaseModel): question:str="Why is checkout failing?"
class FailureSimulation(BaseModel): faults:list[str] = Field(default_factory=list)
SERVICE_URLS = {
    "frontend": os.environ["FRONTEND_URL"],
    "gateway": "http://gateway:8000",
    "checkout": "http://checkout:8000",
    "inventory": "http://inventory:8000",
    "payment": os.environ["PAYMENT_CONTROL_URL"],
}

def generate_traffic(services=()):
    targets = [os.environ["FRONTEND_URL"]]
    targets.extend(SERVICE_URLS[service] for service in services if service != "frontend")
    def create_request(target):
        try: requests.get(target + "/checkout", timeout=5)
        except requests.RequestException: pass
    with ThreadPoolExecutor(max_workers=10) as pool: list(pool.map(create_request, targets * 8))

@app.post("/api/failures")
def inject_failures(simulation: FailureSimulation):
    selected = set(simulation.faults)
    unknown = [item for item in selected if ":" not in item or item.split(":", 1)[0] not in SERVICE_URLS]
    if unknown: return {"error": "Unknown fault selections", "unknown": unknown}
    results = {}
    for service, base_url in SERVICE_URLS.items():
        matching = [item.split(":", 1)[1] for item in selected if item.startswith(service + ":")]
        if len(matching) > 1: return {"error": f"Only one fault mode may be active per {service}"}
        mode = matching[0] if matching else "off"
        response = requests.post(f"{base_url}/control/failure/{mode}", timeout=5)
        results[service] = response.json()
    if selected: generate_traffic(item.split(":", 1)[0] for item in selected)
    return {"faults": results}
@app.post("/api/failures/payment/{state}")
def inject_failure(state:str):
    result = requests.post(f'{os.environ["PAYMENT_CONTROL_URL"]}/control/failure/{state}',timeout=5).json()
    # Generate the incident window concurrently so slow simulated dependencies do
    # not make the UI wait for 25 serial requests.
    if state != "off": generate_traffic(("payment",))
    return result
@app.post("/api/investigations")
def investigate(req:Investigation):
    return graph.invoke({"incident_id": str(uuid.uuid4()), "question": req.question})["report"]

class MemoryApproval(BaseModel):
    report: dict
    approved: bool = False

@app.post("/api/memory/incidents")
def save_incident_memory(request: MemoryApproval):
    if not request.approved:
        return {"saved": False, "error": "Explicit approval is required to write incident memory."}
    try:
        incident_id = qdrant_api.save_incident(request.report)
        return {"saved": True, "incident_id": incident_id}
    except Exception as exc:
        return {"saved": False, "error": f"Incident memory unavailable: {exc}"}
