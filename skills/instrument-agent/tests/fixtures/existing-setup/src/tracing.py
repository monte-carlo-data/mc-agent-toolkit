import montecarlo_opentelemetry as mc

mc.setup(
    agent_name="x",
    otlp_endpoint="https://example/v1/traces",
    instrumentors=[],
)
