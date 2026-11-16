import montecarlo_opentelemetry as mco

mco.setup(
    agent_name="alias",
    otlp_endpoint="https://example/v1/traces",
    instrumentors=[],
)
