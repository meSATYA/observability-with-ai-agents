"""Local runbook lookup; the sample runbook is the safe fallback when Qdrant is empty."""
from pathlib import Path
def runbook(context=""):
    context = str(context)
    if "payment provider timeout" in context:
        path = "runbooks/payment-provider-timeout.md"
    elif "card declined" in context:
        path = "runbooks/payment-card-declined.md"
    else:
        path = "runbooks/payment-db-pool.md"
    return Path(path).read_text()
