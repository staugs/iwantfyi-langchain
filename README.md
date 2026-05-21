# iwantfyi-langchain

LangChain tools for [iwant.fyi](https://iwant.fyi) — the reference implementation of the [iwant.fyi demand-side protocol v1.0](https://iwant.fyi/protocol/v1).

> **iwant.fyi demand-side protocol** is an open standard for how AI agents express structured purchase intent on behalf of users, receive matched supply across multiple sources, and report outcomes back. This package wraps iwant.fyi as a set of LangChain `StructuredTool` objects that any LangChain agent can use.

## Install

```bash
pip install iwantfyi-langchain
```

## Quick start

```python
from iwantfyi_langchain import get_iwant_tools
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

tools = get_iwant_tools(api_key="iwant_ak_...")  # get a key at https://iwant.fyi

agent = create_react_agent(
    ChatOpenAI(model="gpt-4o-mini"),
    tools,
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Find me a 1/4-inch drive torque wrench under $150"}]
})
print(result["messages"][-1].content)
```

That's it. The agent now has seven tools wired in: `demand_create_want`, `demand_search`, `demand_get_want`, `demand_record_outcome`, `demand_list_verticals`, `demand_list_constraints`, `demand_health`.

## Get an API key

1. Visit [iwant.fyi](https://iwant.fyi) and sign in.
2. Register an agent (UI or `POST /api/agents`).
3. Save the returned key (format: `iwant_ak_...`).

## What you get

| Tool | Spec | Description |
|---|---|---|
| `demand_create_want` | §8.1 | Create a Want and run matching |
| `demand_search` | §8.1 | Ephemeral matching, no persistence |
| `demand_get_want` | §8.1 | Retrieve a Want by ID |
| `demand_record_outcome` | §8.1 | Report viewed/clicked/purchased outcome |
| `demand_list_verticals` | §8.2 | Discover supported verticals |
| `demand_list_constraints` | §8.2 | Discover constraint vocabulary |
| `demand_health` | §8.2 | Liveness + readiness |

All tools use Pydantic v2 args schemas, so LangChain will validate user inputs before invoking iwant.fyi.

## Direct client (no LangChain)

You can use the underlying `IwantClient` directly if you don't want LangChain in the loop:

```python
from iwantfyi_langchain import IwantClient

with IwantClient(api_key="iwant_ak_...") as client:
    health = client.health()
    print(health["status"])

    response = client.create_want(
        title='Torque wrench, 1/4" drive, 25-100 ft-lb',
        price_cents=15000,
        vertical="tools",
        mode="any",
    )
    print(f"Want {response['want']['id']} -> {response['matches']['match_count']} matches")
```

## Transports

By default the client uses MCP over HTTP (JSON-RPC). Switch to the REST fallback:

```python
client = IwantClient(api_key="...", transport="http")
```

Both transports cover all `demand.*` tools. Legacy iwant.fyi tools (`browse_wants`, `search_listings`, etc.) only work over MCP transport via `client.call_tool(...)`.

## Outcome events

Outcome events feed match-quality learning and (eventually) revenue-share attribution:

```python
client.record_outcome(want_id=w_id, match_id=m_id, event="clicked")
client.record_outcome(want_id=w_id, match_id=m_id, event="purchased", value_cents=12500)
```

Events are idempotent on the server side. Replays are no-ops.

## Errors

Typed exceptions from `iwantfyi_langchain.errors`:

```python
from iwantfyi_langchain import IwantError, UnauthorizedError, ValidationError, RateLimitedError

try:
    client.create_want(title="x", price_cents=1)
except UnauthorizedError:
    ...  # refresh key
except ValidationError as e:
    ...  # e.message, e.data
except RateLimitedError:
    ...  # back off
except IwantError as e:
    ...  # generic; e.code, e.message
```

## Specification

Full iwant.fyi demand-side protocol v1.0 specification: [iwant.fyi/protocol/v1](https://iwant.fyi/protocol/v1)

The protocol is published under Apache 2.0. iwant.fyi is the reference implementation; anyone may build their own.

## License

Apache 2.0
