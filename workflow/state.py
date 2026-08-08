from typing import TypedDict, Any
class IncidentState(TypedDict, total=False):
    incident_id: str; question: str; metrics: Any; logs: Any; traces: Any; correlation: Any; similar_incidents: Any; knowledge: str; root_cause: str; llm_summary: str; llm_status: str; llm_error: str; remediation: list[str]; report: Any
