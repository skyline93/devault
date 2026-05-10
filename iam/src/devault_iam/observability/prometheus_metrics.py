from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, REGISTRY, generate_latest

HTTP_REQUESTS_TOTAL = Counter(
    "devault_iam_http_requests_total",
    "Total HTTP requests handled by IAM",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "devault_iam_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


def metrics_response_body() -> tuple[bytes, str]:
    data = generate_latest(REGISTRY)
    return data, CONTENT_TYPE_LATEST
