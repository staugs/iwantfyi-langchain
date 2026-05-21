"""LangChain Tool factory for the iwant.fyi demand-side protocol.

Usage:
    from iwantfyi_langchain import get_iwant_tools

    tools = get_iwant_tools(api_key="iwant_ak_...")
    # Pass `tools` to any LangChain agent that accepts a list of tools.
"""

from __future__ import annotations
import json
from typing import Any, Optional

from langchain_core.tools import StructuredTool

from iwantfyi_langchain.client import IwantClient
from iwantfyi_langchain.models import (
    CreateWantInput,
    GetWantInput,
    RecordOutcomeInput,
    SearchInput,
)


def _serialize(result: Any) -> str:
    """LangChain tools traditionally return strings. We JSON-encode dict responses
    so the agent can parse them; pure strings (rare) pass through."""
    if isinstance(result, str):
        return result
    return json.dumps(result, default=str)


def get_iwant_tools(
    api_key: str,
    base_url: str = "https://iwant.fyi",
    transport: str = "mcp",
    client: Optional[IwantClient] = None,
) -> list[StructuredTool]:
    """Return a list of LangChain StructuredTools wired to iwant.fyi.

    Args:
        api_key: An iwant.fyi API key (format iwant_ak_...). Get one at https://iwant.fyi.
        base_url: Override the iwant.fyi host (default: https://iwant.fyi).
        transport: "mcp" (default) or "http" for the REST fallback.
        client: Reuse an existing IwantClient. Useful for testing and connection pooling.

    Returns:
        A list of StructuredTool objects for: create_want, search, get_want,
        record_outcome, list_verticals, list_constraints, health.
    """
    c = client or IwantClient(api_key=api_key, base_url=base_url, transport=transport)  # type: ignore[arg-type]

    def _create_want(**kwargs: Any) -> str:
        # Pydantic validation -- raises ValidationError if input shape is wrong
        validated = CreateWantInput(**kwargs)
        result = c.create_want(**validated.model_dump(exclude_none=True))
        return _serialize(result)

    def _search(**kwargs: Any) -> str:
        validated = SearchInput(**kwargs)
        result = c.search(**validated.model_dump(exclude_none=True))
        return _serialize(result)

    def _get_want(want_id: str) -> str:
        validated = GetWantInput(want_id=want_id)
        result = c.get_want(validated.want_id)
        return _serialize(result)

    def _record_outcome(**kwargs: Any) -> str:
        validated = RecordOutcomeInput(**kwargs)
        result = c.record_outcome(**validated.model_dump(exclude_none=True))
        return _serialize(result)

    def _list_verticals() -> str:
        return _serialize(c.list_verticals())

    def _list_constraints() -> str:
        return _serialize(c.list_constraints())

    def _health() -> str:
        return _serialize(c.health())

    return [
        StructuredTool.from_function(
            func=_create_want,
            name="demand_create_want",
            description=(
                "Create a buyer Want (structured purchase intent) on iwant.fyi and return matched "
                "supply. Use this when the user articulates what they want to buy. "
                "Required: title (str, 5-200 chars), price_cents (int). "
                "Recommended: vertical (tools|auto_parts), mode (new|used|any), "
                "location (object with text/lat/lng/radius_km), constraints (object with rules/negotiable). "
                "Returns: { want, matches: { matches[], match_count, sources_consulted } }."
            ),
            args_schema=CreateWantInput,
        ),
        StructuredTool.from_function(
            func=_search,
            name="demand_search",
            description=(
                "Search for matched supply against a query without persisting a Want. "
                "Use for ephemeral discovery when the user is browsing. "
                "Required: title. Optional: same fields as demand_create_want. "
                "Returns: { matches[], match_count, sources_consulted }."
            ),
            args_schema=SearchInput,
        ),
        StructuredTool.from_function(
            func=_get_want,
            name="demand_get_want",
            description=(
                "Retrieve an existing Want by ID, including its current matches and constraints. "
                "Use to follow up on a Want created earlier in the conversation."
            ),
            args_schema=GetWantInput,
        ),
        StructuredTool.from_function(
            func=_record_outcome,
            name="demand_record_outcome",
            description=(
                "Report a user-facing outcome event back to iwant.fyi for attribution and "
                "match-quality learning. Call after the user views, clicks, or completes a "
                "purchase against a Match. "
                "Required: want_id, match_id, event (viewed|clicked|started_checkout|"
                "purchased|abandoned|not_purchased). value_cents required for 'purchased'."
            ),
            args_schema=RecordOutcomeInput,
        ),
        StructuredTool.from_function(
            func=_list_verticals,
            name="demand_list_verticals",
            description=(
                "List verticals supported by this iwant.fyi instance (e.g., tools, auto_parts) "
                "with supported spec keys per vertical. Call once at agent startup to discover "
                "capabilities."
            ),
        ),
        StructuredTool.from_function(
            func=_list_constraints,
            name="demand_list_constraints",
            description=(
                "List the constraint vocabulary supported by this iwant.fyi instance. "
                "Reference when constructing constraints.rules for demand_create_want."
            ),
        ),
        StructuredTool.from_function(
            func=_health,
            name="demand_health",
            description="Liveness + readiness check. Returns protocol version, server info, and active supply sources.",
        ),
    ]
