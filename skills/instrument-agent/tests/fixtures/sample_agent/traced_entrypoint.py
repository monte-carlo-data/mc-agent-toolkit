import montecarlo_opentelemetry as mc


@mc.trace_with_workflow()
def run_workflow() -> str:
    return "ok"
