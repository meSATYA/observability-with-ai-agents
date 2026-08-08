"""One service image, configured as frontend/gateway/checkout/inventory/payment."""
import logging, os, random, time
import requests
from fastapi import FastAPI, HTTPException
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry import metrics
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider

name, downstream = os.environ["SERVICE_NAME"], os.getenv("DOWNSTREAM_URL")
provider = TracerProvider(resource=Resource.create({"service.name": name, "deployment.environment": "local"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"])))
trace.set_tracer_provider(provider); tracer = trace.get_tracer(name)
# A short interval keeps this incident lab responsive after “Inject Failure”.
reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=os.environ["OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"]),
    export_interval_millis=5_000,
)
metrics.set_meter_provider(MeterProvider(resource=Resource.create({"service.name": name}), metric_readers=[reader]))
meter = metrics.get_meter(name); stages = meter.create_counter("checkout_stage_total"); duration = meter.create_histogram("checkout_stage_duration_seconds", unit="s")
log_provider = LoggerProvider(resource=Resource.create({"service.name": name}))
log_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=os.environ["OTEL_EXPORTER_OTLP_LOGS_ENDPOINT"])))
set_logger_provider(log_provider)
# Uvicorn configures the root logger before importing this module, so basicConfig
# would be ignored. Attach the OTLP handler to the app-specific logger instead.
app_logger = logging.getLogger(name)
app_logger.setLevel(logging.INFO)
app_logger.propagate = False
app_logger.addHandler(LoggingHandler(logger_provider=log_provider))
app = FastAPI(title=name); FastAPIInstrumentor.instrument_app(app); RequestsInstrumentor().instrument()
failure_mode = "off"
SERVICE_FAULTS = {
    "frontend": {"frontend_overloaded": (503, "frontend worker saturation", 0.4, "frontend worker pool saturated", "frontend")},
    "gateway": {"gateway_rate_limited": (429, "gateway rate limit exceeded", 0.1, "gateway rate limit exceeded", "gateway")},
    "checkout": {"redis_timeout": (503, "checkout session cache unavailable", 0.8, "redis session cache timeout", "redis")},
    "inventory": {"inventory_unavailable": (503, "inventory service unavailable", 0.6, "inventory reservation database unavailable", "inventory-db")},
    "payment": {
        "db_pool": (503, "payment database unavailable", 1.1, "payment database connection pool exhausted", "postgres"),
        "gateway_timeout": (504, "payment provider timed out", 2.0, "payment provider timeout", "payment-provider"),
        "card_declined": (402, "card payment declined", 0.15, "card declined by payment provider", "payment-provider"),
    },
}

def log(level, message, **attrs):
    ctx = trace.get_current_span().get_span_context()
    data = {"service_name": name, "level": level, "message": message, **attrs}
    if ctx.is_valid: data["trace_id"] = f"{ctx.trace_id:032x}"
    app_logger.info(__import__("json").dumps(data))

@app.get("/health")
def health(): return {"service": name, "failure_mode": failure_mode}

@app.get("/checkout")
def checkout():
    started = time.perf_counter()
    with tracer.start_as_current_span(f"{name}.handle_checkout") as span:
        active_fault = SERVICE_FAULTS.get(name, {}).get(failure_mode)
        if active_fault:
            status, detail, delay, message, dependency = active_fault
            span.set_attribute("error.type", failure_mode)
            span.set_attribute("fault.mode", failure_mode)
            log("error", message, dependency=dependency, fault=failure_mode)
            time.sleep(delay)
            attrs = {"service": name, "outcome": "error", "fault": failure_mode}
            stages.add(1, attrs); duration.record(time.perf_counter()-started, attrs)
            raise HTTPException(status, detail)
        if downstream:
            try:
                result = requests.get(downstream + "/checkout", timeout=4)
                result.raise_for_status()
            except requests.RequestException as exc:
                log("error", "downstream checkout failed", downstream=downstream, error=str(exc))
                raise HTTPException(502, "checkout dependency failed")
        time.sleep(random.uniform(.02, .08))
        log("info", "checkout stage complete")
        stages.add(1, {"service": name, "outcome": "ok"}); duration.record(time.perf_counter()-started, {"service": name, "outcome": "ok"})
        return {"service": name, "status": "ok"}

@app.post("/control/failure/{mode}")
def set_failure(mode: str):
    global failure_mode
    mode = "db_pool" if mode == "on" else mode  # backwards-compatible API.
    allowed = ("off", *SERVICE_FAULTS.get(name, {}))
    if mode not in allowed: raise HTTPException(400, f"mode must be one of: {', '.join(allowed)}")
    failure_mode = mode; log("warn", "failure mode changed", failure_mode=mode)
    return {"service": name, "failure_mode": failure_mode}
