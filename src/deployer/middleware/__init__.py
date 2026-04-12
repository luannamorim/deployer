BYPASS_PATHS: frozenset[str] = frozenset(
    {"/health", "/health/ready", "/metrics", "/docs", "/openapi.json", "/redoc"}
)
