"""Unit tests for IwantClient using respx (httpx mock transport)."""

import json
import pytest
import httpx
import respx

from iwantfyi_langchain.client import IwantClient
from iwantfyi_langchain.errors import (
    IwantError,
    UnauthorizedError,
    ValidationError,
)


def _mcp_result(payload):
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": json.dumps(payload)}]},
    }


def _mcp_error(code, message):
    return {"jsonrpc": "2.0", "id": 1, "error": {"code": code, "message": message}}


@pytest.fixture
def client():
    c = IwantClient(api_key="iwant_ak_test", base_url="https://iwant.fyi")
    yield c
    c.close()


@pytest.fixture
def http_client():
    c = IwantClient(api_key="iwant_ak_test", base_url="https://iwant.fyi", transport="http")
    yield c
    c.close()


# ===== Construction =====


def test_requires_api_key():
    with pytest.raises(IwantError):
        IwantClient(api_key="")


def test_trims_trailing_slash():
    c = IwantClient(api_key="k", base_url="https://example.com/")
    assert c.base_url == "https://example.com"
    c.close()


# ===== MCP transport =====


@respx.mock
def test_mcp_create_want_sends_jsonrpc_with_bearer(client):
    route = respx.post("https://iwant.fyi/api/mcp").mock(
        return_value=httpx.Response(
            200,
            json=_mcp_result(
                {
                    "protocol_version": "1.0",
                    "want": {"id": "w1", "title": "x", "price_cents": 100},
                    "matches": {"matches": [], "match_count": 0},
                }
            ),
        )
    )

    result = client.create_want(title="torque wrench", price_cents=15000)
    assert result["want"]["id"] == "w1"
    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer iwant_ak_test"
    body = json.loads(sent.content)
    assert body["method"] == "tools/call"
    assert body["params"]["name"] == "demand.create_want"
    assert body["params"]["arguments"]["title"] == "torque wrench"


@respx.mock
def test_mcp_unauthorized_error_on_minus_32000(client):
    respx.post("https://iwant.fyi/api/mcp").mock(
        return_value=httpx.Response(200, json=_mcp_error(-32000, "no key"))
    )
    with pytest.raises(UnauthorizedError):
        client.create_want(title="x", price_cents=1)


@respx.mock
def test_mcp_validation_error_when_tool_returns_inner_error(client):
    respx.post("https://iwant.fyi/api/mcp").mock(
        return_value=httpx.Response(
            200,
            json=_mcp_result({"error": "price_cents must be at least 500"}),
        )
    )
    with pytest.raises(ValidationError):
        client.create_want(title="x", price_cents=100)


@respx.mock
def test_mcp_record_outcome(client):
    respx.post("https://iwant.fyi/api/mcp").mock(
        return_value=httpx.Response(
            200, json=_mcp_result({"received": True, "outcome_id": "o1"})
        )
    )
    r = client.record_outcome(want_id="w1", match_id="m1", event="viewed")
    assert r["received"] is True
    assert r["outcome_id"] == "o1"


@respx.mock
def test_mcp_list_verticals(client):
    respx.post("https://iwant.fyi/api/mcp").mock(
        return_value=httpx.Response(
            200,
            json=_mcp_result(
                {
                    "protocol_version": "1.0",
                    "verticals": [
                        {
                            "id": "tools",
                            "display_name": "Tools",
                            "description": "",
                            "supported_spec_keys": [],
                        }
                    ],
                }
            ),
        )
    )
    r = client.list_verticals()
    assert len(r["verticals"]) == 1
    assert r["verticals"][0]["id"] == "tools"


@respx.mock
def test_mcp_call_tool_works_for_legacy_tools(client):
    route = respx.post("https://iwant.fyi/api/mcp").mock(
        return_value=httpx.Response(200, json=_mcp_result({"wants": [], "total": 0}))
    )
    r = client.call_tool("browse_wants", {"page": 1})
    assert r["total"] == 0
    body = json.loads(route.calls.last.request.content)
    assert body["params"]["name"] == "browse_wants"


# ===== HTTP transport =====


@respx.mock
def test_http_create_want_hits_post_wants(http_client):
    route = respx.post("https://iwant.fyi/api/v1/wants").mock(
        return_value=httpx.Response(
            201,
            json={
                "protocol_version": "1.0",
                "want": {"id": "w1", "title": "x", "price_cents": 100},
                "matches": {"matches": [], "match_count": 0},
            },
        )
    )
    r = http_client.create_want(title="torque wrench", price_cents=15000)
    assert r["want"]["id"] == "w1"
    assert route.called


@respx.mock
def test_http_get_want_hits_get_wants_id(http_client):
    route = respx.get("https://iwant.fyi/api/v1/wants/w1").mock(
        return_value=httpx.Response(
            200, json={"want": {"id": "w1", "title": "x", "price_cents": 100}}
        )
    )
    http_client.get_want("w1")
    assert route.called


@respx.mock
def test_http_health_hits_get_health(http_client):
    respx.get("https://iwant.fyi/api/v1/health").mock(
        return_value=httpx.Response(
            200,
            json={
                "protocol_version": "1.0",
                "server": "ref",
                "version": "0.21",
                "status": "healthy",
            },
        )
    )
    r = http_client.health()
    assert r["status"] == "healthy"


def test_http_rejects_unsupported_tools(http_client):
    with pytest.raises(IwantError, match="HTTP transport"):
        http_client.call_tool("browse_wants")
