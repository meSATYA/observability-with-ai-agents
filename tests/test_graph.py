from workflow.graph import build_graph
def test_graph_compiles():
    assert build_graph() is not None
