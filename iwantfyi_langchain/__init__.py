"""iwantfyi-langchain -- LangChain tools for the iwant.fyi demand-side protocol v1.0.

Reference implementation of the protocol lives at https://iwant.fyi.
Spec: https://iwant.fyi/protocol/v1
"""

from iwantfyi_langchain.client import IwantClient
from iwantfyi_langchain.errors import (
    IwantError,
    UnauthorizedError,
    RateLimitedError,
    ValidationError,
    NotFoundError,
)
from iwantfyi_langchain.models import (
    Want,
    Match,
    Constraints,
    Location,
    Origin,
    DemandOutcomeEvent,
    SupplyMode,
    CreateWantInput,
    MatchResponse,
)
from iwantfyi_langchain.tools import get_iwant_tools

__version__ = "0.1.0"

__all__ = [
    "IwantClient",
    "IwantError",
    "UnauthorizedError",
    "RateLimitedError",
    "ValidationError",
    "NotFoundError",
    "Want",
    "Match",
    "Constraints",
    "Location",
    "Origin",
    "DemandOutcomeEvent",
    "SupplyMode",
    "CreateWantInput",
    "MatchResponse",
    "get_iwant_tools",
]
