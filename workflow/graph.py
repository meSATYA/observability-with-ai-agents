"""Executable LangGraph runtime; separate to avoid shadowing the langgraph PyPI package."""
from langgraph.graph import StateGraph, END
from .state import IncidentState
from . import nodes

def build_graph():
    graph = StateGraph(IncidentState)
    node_functions = {
        "supervisor_agent": nodes.supervisor,
        "metrics_agent": nodes.metrics,
        "logs_agent": nodes.logs,
        "traces_agent": nodes.traces,
        "correlation_agent": nodes.correlate,
        "knowledge_agent": nodes.knowledge,
        "rootcause_agent": nodes.rootcause,
        "remediation_agent": nodes.remediate,
        "report_agent": nodes.report,
    }
    for name, function in node_functions.items(): graph.add_node(name, function)
    graph.set_entry_point("supervisor_agent")
    chain = tuple(node_functions)
    for source, target in zip(chain, chain[1:]): graph.add_edge(source, target)
    graph.add_edge("report_agent", END)
    return graph.compile()
