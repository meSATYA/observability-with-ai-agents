"""Local runbooks plus approval-gated incident memory in Qdrant."""
import os, uuid
from pathlib import Path
from .embeddings import DIMENSION, embed

COLLECTION = "incident_memory"

def _client():
    from qdrant_client import QdrantClient
    return QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"), timeout=3)

def _ensure_collection(client):
    from qdrant_client.models import Distance, VectorParams
    if not client.collection_exists(COLLECTION):
        client.create_collection(COLLECTION, vectors_config=VectorParams(size=DIMENSION, distance=Distance.COSINE))

def runbook(context=""):
    context = str(context)
    if "payment provider timeout" in context:
        path = "runbooks/payment-provider-timeout.md"
    elif "card declined" in context:
        path = "runbooks/payment-card-declined.md"
    else:
        path = "runbooks/payment-db-pool.md"
    return Path(path).read_text()

def search_similar(context, limit=3):
    try:
        client = _client(); _ensure_collection(client)
        hits = client.query_points(collection_name=COLLECTION, query=embed(context), limit=limit).points
        return [hit.payload for hit in hits if hit.payload]
    except Exception:
        return []

def save_incident(report):
    """Persist only after an explicit human approval in the API layer."""
    from qdrant_client.models import PointStruct
    client = _client(); _ensure_collection(client)
    root = report.get("root_cause", "")
    evidence = report.get("evidence", {})
    text = f"{report.get('question', '')} {root} {evidence}"
    incident_id = report.get("incident_id") or str(uuid.uuid4())
    client.upsert(COLLECTION, points=[PointStruct(id=incident_id, vector=embed(text), payload={"incident_id": incident_id, "question": report.get("question"), "root_cause": root, "remediation": report.get("remediation", []), "evidence": evidence})])
    return incident_id
