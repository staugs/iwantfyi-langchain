"""Tests for the LangChain tool factory."""

import json
import pytest
import httpx
import respx

from iwantfyi_langchain.tools import get_iwant_tools
from iwantfyi_langchain.client import IwantClient


def _mcp_result(payload):
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": json.dumps(payload)}]},
    }


class TestToolFactory:
    def test_returns_seven_tools(self):
        tools = get_iwant_tools(api_key="iwant_ak_test")
        names = [t.name for t in tools]
        assert "demand_create_want" in names
        assert "demand_search" in names
        assert "demand_get_want" in names
        assert "demand_record_outcome" in names
        assert "demand_list_verticals" in names
        assert "demand_list_constraints" in names
        assert "demand_health" in names
        assert len(tools) == 7

    def test_all_tools_have_descriptions(self):
        tools = get_iwant_tools(api_key="iwant_ak_test")
        for t in tools:
            assert t.description
            assert len(t.description) > 50  # non-trivial description

    def test_create_want_tool_has_args_schema(self):
        tools = get_iwant_tools(api_key="iwant_ak_test")
        create_want = next(t for t in tools if t.name == "demand_create_want")
        assert create_want.args_schema is not None
        # Pydantic v2 -- model_fields exposes the schema
        fields = create_want.args_schema.model_fields
        assert "title" in fields
        assert "price_cents" in fields
        assert "vertical" in fields
        assert "constraints" in fields

    @respx.mock
    def test_create_want_tool_invokes_client(self):
        respx.post("https://iwant.fyi/api/mcp").mock(
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
        tools = get_iwant_tools(api_key="iwant_ak_test")
        create_want = next(t for t in tools if t.name == "demand_create_want")
        # Invoke as LangChain would
        result_str = create_want.invoke(
            {"title": "torque wrench", "price_cents": 15000}
        )
        parsed = json.loads(result_str)
        assert parsed["want"]["id"] == "w1"

    @respx.mock
    def test_health_tool_invokes_client(self):
        respx.post("https://iwant.fyi/api/mcp").mock(
            return_value=httpx.Response(
                200,
                json=_mcp_result(
                    {
                        "protocol_version": "1.0",
                        "server": "ref",
                        "version": "0.21",
                        "status": "healthy",
                    }
                ),
            )
        )
        tools = get_iwant_tools(api_key="iwant_ak_test")
        health = next(t for t in tools if t.name == "demand_health")
        result_str = health.invoke({})
        parsed = json.loads(result_str)
        assert parsed["status"] == "healthy"

    def test_reuses_provided_client(self):
        client = IwantClient(api_key="iwant_ak_test")
        tools = get_iwant_tools(api_key="iwant_ak_test", client=client)
        # If client was passed through, both clients should reuse it
        # We don't have an easy public surface to assert this; smoke test it
        # by confirming no exception on construction
        assert len(tools) == 7
        client.close()
