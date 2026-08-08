def trace_url(trace_id): return f"http://localhost:3000/explore?left={{\"datasource\":\"tempo\",\"queries\":[{{\"query\":\"{trace_id}\"}}]}}"
