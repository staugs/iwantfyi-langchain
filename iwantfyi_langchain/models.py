"""Pydantic v2 models for the iwant.fyi demand-side protocol v1.0 schema.

See https://iwant.fyi/protocol/v1 for the canonical spec.
"""

from __future__ import annotations
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

WantCategory = Literal["goods", "services", "other"]
SupplyMode = Literal["new", "used", "any"]
ListingCondition = Literal["new", "like-new", "good", "fair", "used", "unknown"]
DemandOutcomeEvent = Literal[
    "viewed",
    "clicked",
    "started_checkout",
    "purchased",
    "abandoned",
    "not_purchased",
]


class Location(BaseModel):
    model_config = ConfigDict(extra="allow")
    text: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    radius_km: Optional[float] = None


class Constraints(BaseModel):
    model_config = ConfigDict(extra="allow")
    rules: Optional[dict[str, Any]] = None
    negotiable: Optional[list[str]] = None
    auto_accept: Optional[dict[str, Any]] = None


class Origin(BaseModel):
    model_config = ConfigDict(extra="allow")
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    session_id: Optional[str] = None


class CreateWantInput(BaseModel):
    """Input shape for demand.create_want. Mirrors spec section 4."""

    model_config = ConfigDict(extra="allow")
    title: str = Field(min_length=5, max_length=200)
    description: Optional[str] = None
    price_cents: int = Field(ge=0)
    price_currency: str = "USD"
    category: Optional[WantCategory] = None
    vertical: Optional[str] = None
    mode: Optional[SupplyMode] = None
    location: Optional[Union[Location, str]] = None
    constraints: Optional[Constraints] = None
    origin: Optional[Origin] = None
    expires_at: Optional[str] = None


class Want(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    title: str
    price_cents: int
    price_currency: Optional[str] = "USD"
    description: Optional[str] = None
    category: Optional[WantCategory] = None
    vertical: Optional[str] = None
    mode: Optional[SupplyMode] = None
    protocol_version: Optional[str] = None
    created_at: Optional[str] = None


class Match(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    source: Optional[str] = None
    title: Optional[str] = None
    price_cents: Optional[int] = None
    price_currency: Optional[str] = None
    condition: Optional[ListingCondition] = None
    mode: Optional[SupplyMode] = None
    location: Optional[str] = None
    images: Optional[list[str]] = None
    url: Optional[str] = None
    direct_url: Optional[str] = None
    score: float = 0.0
    reasons: Optional[list[str]] = None
    attributes: Optional[dict[str, Any]] = None


class MatchResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    want_id: Optional[str] = None
    matches: list[Match] = Field(default_factory=list)
    match_count: int = 0
    sources_consulted: Optional[list[str]] = None
    generated_at: Optional[str] = None


class CreateWantResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    protocol_version: str
    want: Want
    matches: MatchResponse


class RecordOutcomeInput(BaseModel):
    model_config = ConfigDict(extra="allow")
    want_id: str
    match_id: str
    event: DemandOutcomeEvent
    match_source: Optional[str] = None
    timestamp: Optional[str] = None
    value_cents: Optional[int] = None
    metadata: Optional[dict[str, Any]] = None


class SearchInput(BaseModel):
    """Input for demand.search. Subset of CreateWantInput; not persisted."""

    model_config = ConfigDict(extra="allow")
    title: str
    description: Optional[str] = None
    price_cents: Optional[int] = None
    price_currency: Optional[str] = "USD"
    category: Optional[WantCategory] = None
    vertical: Optional[str] = None
    mode: Optional[SupplyMode] = None
    location: Optional[Union[Location, str]] = None
    constraints: Optional[Constraints] = None


class GetWantInput(BaseModel):
    want_id: str
