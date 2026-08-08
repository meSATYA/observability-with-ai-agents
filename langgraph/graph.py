from langgraph.graph import StateGraph, END
from .state import IncidentState
from . import nodes
def build_graph():
    g=StateGraph(IncidentState)
    for name in ("supervisor","metrics","logs","traces","correlate","knowledge","rootcause","remediate","report"): g.add_node(name,getattr(nodes,name))
    g.set_entry_point("supervisor")
    for a,b in zip(("supervisor","metrics","logs","traces","correlate","knowledge","rootcause","remediate"),("metrics","logs","traces","correlate","knowledge","rootcause","remediate","report")): g.add_edge(a,b)
    g.add_edge("report",END); return g.compile()
