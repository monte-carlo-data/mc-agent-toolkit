from montecarlo_opentelemetry import setup as setup_mc

setup_mc(
    agent_name="direct",
    otlp_endpoint="https://example/v1/traces",
    instrumentors=[],
)
