from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from pragma.config import get_settings
from pragma.utils.logging import logger

settings = get_settings()


def setup_telemetry(app, service_name: str | None = None) -> TracerProvider:
    """Configure OpenTelemetry with OTLP exporter."""
    # Create a resource with service information
    resource = Resource.create(
        {
            "service.name": service_name or settings.otel_service_name,
            "service.version": "1.0.0",
            "deployment.environment": settings.environment,
        }
    )

    # Initialize TracerProvider with the resource
    tracer_provider = TracerProvider(resource=resource)

    # Always add console exporter for development/debugging
    tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    if otlp_endpoint := settings.otel_exporter_otlp_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=True,  # For development
                timeout=5,  # 5 seconds timeout
            )
            tracer_provider.add_span_processor(
                BatchSpanProcessor(
                    otlp_exporter,
                    max_queue_size=1000,
                    max_export_batch_size=100,
                    schedule_delay_millis=5000,  # 5 seconds
                )
            )
            logger.info(f"OpenTelemetry OTLP exporter configured with endpoint: {otlp_endpoint}")
        except Exception as e:
            logger.warning(f"Failed to initialize OTLP exporter: {e}")
            logger.info("Continuing with console exporter only")

    # Set the TracerProvider as the global default
    trace.set_tracer_provider(tracer_provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

    # Instrument logging
    LoggingInstrumentor().instrument(tracer_provider=tracer_provider)

    return tracer_provider
