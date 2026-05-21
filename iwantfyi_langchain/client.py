"""IwantClient -- synchronous + async Python client for the iwant.fyi demand-side protocol v1.0.

Mirrors the @iwantfyi/sdk TypeScript client. Default transport is MCP over
HTTP (JSON-RPC). HTTP fallback is available via transport="http".
"""

from __future__ import annotations
import json
from typing import Any, Literal, Optional

import httpx

from iwantfyi_langchain.errors import IwantError, error_from_code

Transport = Literal["mcp", "http"]

_HTTP_ROUTE_MAP: dict[str, tuple[str, str]] = {
    # tool_name -> (method, path_template)
    "demand.create_want": ("POST", "/api/v1/wants"),
    "demand.search": ("POST", "/api/v1/search"),
    "demand.get_want": ("GET", "/api/v1/wants/{want_id}"),
    "demand.record_outcome": ("POST", "/api/v1/outcomes"),
    "demand.list_verticals": ("GET", "/api/v1/verticals"),
    "demand.list_constraints": ("GET", "/api/v1/constraints"),
    "demand.health": ("GET", "/api/v1/health"),
}


class IwantClient:
    """Synchronous client for iwant.fyi's iwant.fyi demand-side protocol implementation.

    Most users will get tools via get_iwant_tools(), which constructs this
    internally. Use the client directly when you need typed responses outside
    a LangChain agent context.

    Example:
        client = IwantClient(api_key="iwant_ak_...")
        result = client.create_want(
            title="Torque wrench, 1/4\\" drive, 25-100 ft-lb",
            price_cents=15000,
            vertical="tools",
        )
        print(result["matches"]["match_count"])
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://iwant.fyi",
        transport: Transport = "mcp",
        timeout: float = 30.0,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        if not api_key:
            raise IwantError("api_key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.transport = transport
        self.timeout = timeout
        self._client = http_client or httpx.Client(timeout=timeout)
        self._owns_client = http_client is None
        self._rpc_id = 0

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "IwantClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ===== High-level methods =====

    def create_want(self, **kwargs: Any) -> dict[str, Any]:
        """Create a Want and run matching. See spec section 8.1."""
        return self._invoke_tool("demand.create_want", kwargs)

    def search(self, **kwargs: Any) -> dict[str, Any]:
        """Ephemeral matching, no persistence. See spec section 8.1."""
        return self._invoke_tool("demand.search", kwargs)

    def get_want(self, want_id: str) -> dict[str, Any]:
        """Retrieve a Want by ID. See spec section 8.1."""
        return self._invoke_tool("demand.get_want", {"want_id": want_id})

    def record_outcome(self, **kwargs: Any) -> dict[str, Any]:
        """Report an outcome event. See spec section 8.1 + section 7."""
        return self._invoke_tool("demand.record_outcome", kwargs)

    def list_verticals(self) -> dict[str, Any]:
        """Discover supported verticals. See spec section 8.2."""
        return self._invoke_tool("demand.list_verticals", {})

    def list_constraints(self) -> dict[str, Any]:
        """Discover supported constraint vocabulary. See spec section 8.2."""
        return self._invoke_tool("demand.list_constraints", {})

    def health(self) -> dict[str, Any]:
        """Liveness check. See spec section 8.2."""
        return self._invoke_tool("demand.health", {})

    # ===== Low-level escape hatch =====

    def call_tool(self, name: str, args: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Call any MCP tool by name. Use for legacy iwant.fyi tools (browse_wants, search_listings, etc.)."""
        return self._invoke_tool(name, args or {})

    # ===== Internals =====

    def _invoke_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if self.transport == "http":
            return self._http_invoke(name, args)
        return self._mcp_invoke(name, args)

    def _mcp_invoke(self, method: str, args: dict[str, Any]) -> dict[str, Any]:
        self._rpc_id += 1
        body = {
            "jsonrpc": "2.0",
            "id": self._rpc_id,
            "method": "tools/call",
            "params": {"name": method, "arguments": args},
        }
        res = self._client.post(
            f"{self.base_url}/api/mcp",
            json=body,
            headers={"authorization": f"Bearer {self.api_key}"},
        )
        try:
            parsed = res.json()
        except json.JSONDecodeError as e:
            raise IwantError(f"Invalid JSON response (status {res.status_code})") from e

        if parsed.get("error"):
            err = parsed["error"]
            raise error_from_code(err["code"], err["message"], err.get("data"))

        content = parsed.get("result", {}).get("content", [])
        if not content or not content[0].get("text"):
            raise IwantError("Empty response from MCP server")

        try:
            inner = json.loads(content[0]["text"])
        except json.JSONDecodeError as e:
            raise IwantError("Tool returned non-JSON content") from e

        # Tool-level error (validation, business rule)
        if isinstance(inner, dict) and isinstance(inner.get("error"), str):
            raise error_from_code(-32602, inner["error"])

        return inner

    def _http_invoke(self, method: str, args: dict[str, Any]) -> dict[str, Any]:
        route = _HTTP_ROUTE_MAP.get(method)
        if not route:
            raise IwantError(
                f'HTTP transport does not support tool: {method}. Use transport="mcp" or call_tool() via MCP.'
            )
        http_method, path_template = route
        path = path_template.format(**args) if "{" in path_template else path_template
        url = f"{self.base_url}{path}"

        headers = {"authorization": f"Bearer {self.api_key}"}
        if http_method == "GET":
            res = self._client.get(url, headers=headers)
        else:
            res = self._client.post(url, json=args, headers=headers)

        try:
            body = res.json()
        except json.JSONDecodeError as e:
            raise IwantError(f"HTTP {res.status_code}: invalid JSON response") from e

        if res.status_code >= 400:
            err = body.get("error") if isinstance(body, dict) else None
            if err:
                raise error_from_code(err["code"], err["message"], err.get("data"))
            raise IwantError(f"HTTP {res.status_code}")
        return body
