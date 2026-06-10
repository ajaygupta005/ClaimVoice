"""OpenTelemetry tracing setup."""
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

_initialized = False


def setup_tracer(service: str):
    """Configure OTel for this service. Idempotent."""
    global _initialized
    if _initialized:
        return trace.get_tracer(service)

    resource = Resource.create({"service.name": service})
    provider = TracerProvider(resource=resource)

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    else:
        # Dev default: print spans to stdout
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _initialized = True
    return trace.get_tracer(service)


def get_tracer(name: str | None = None):
    return trace.get_tracer(name or __name__)
