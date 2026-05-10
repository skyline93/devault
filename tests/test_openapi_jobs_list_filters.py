"""OpenAPI 登记 GET /api/v1/jobs 的 kind/status 查询参数（十五-23）；无 DB。"""

from __future__ import annotations

from devault.api.main import app


def test_openapi_jobs_list_declares_kind_status_query() -> None:
    spec = app.openapi()
    params = spec["paths"]["/api/v1/jobs"]["get"]["parameters"]
    by_name = {p["name"]: p for p in params}
    assert "kind" in by_name
    assert "status" in by_name
    assert by_name["kind"]["in"] == "query"
    assert by_name["status"]["in"] == "query"
