"""OpenTelemetry instrumentation for FastAPI.

Traces every HTTP request, Agent decision step, and tool call.
Exports to Jaeger via OTLP gRPC (configurable in .env).
Falls back gracefully if opentelemetry packages aren't installed.
"""

from app.core.config import settings

_enabled = False
_provider = None

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.semconv.resource import ResourceAttributes
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


def setup_otel(app):
    """Initialize OpenTelemetry tracing for the FastAPI app."""
    global _provider, _enabled

    if not settings.ENABLE_METRICS:
        return
    if not OTEL_AVAILABLE:
        print("[OTel] Packages not installed — tracing disabled")
        return

    try:
        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: "agentforge",
            ResourceAttributes.SERVICE_VERSION: "0.1.0",
        })
        _provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
        _provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(_provider)
        FastAPIInstrumentor.instrument_app(app)
        _enabled = True
        print(f"[OTel] Tracing enabled -> {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
    except Exception as e:
        print(f"[OTel] Init failed (non-fatal): {e}")
        _enabled = False


def shutdown_otel():
    """Gracefully shut down the tracer provider."""
    global _provider
    if _provider and OTEL_AVAILABLE:
        _provider.shutdown()
        _provider = None


def get_tracer(name: str = "agentforge"):
    """Get a named tracer for creating custom spans."""
    if OTEL_AVAILABLE:
        return trace.get_tracer(name)
    return None


async def trace_agent_step(agent_name="", phase="", tool_name=None, user_query="", response=""):
    """Record a step in the Agent decision tree as a span."""
    if not _enabled or not OTEL_AVAILABLE:
        return
    t = get_tracer("agentforge.agent")
    if t is None:
        return
    with t.start_as_current_span(f"agent.{phase}") as span:
        span.set_attribute("agent.name", agent_name)
        span.set_attribute("agent.phase", phase)
        if tool_name:
            span.set_attribute("tool.name", tool_name)
        if user_query:
            span.set_attribute("user.query", user_query[:200])
        if response:
            span.set_attribute("agent.response", response[:200])
