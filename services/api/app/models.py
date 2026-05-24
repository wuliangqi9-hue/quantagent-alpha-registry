from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    symbol: str = Field(default="BTC", examples=["BTC"])
    mode: Literal["auto", "live", "offline-demo"] | None = "auto"


class RecordSignalRequest(BaseModel):
    symbol: str | None = None
    useLastAnalysis: bool = True
    signalHash: str | None = None
    strategyId: str | None = None
    modelVersion: str | None = None
    mode: str | None = None


class AgentRegisterRequest(BaseModel):
    agentURI: str | None = None


class SettleRequest(BaseModel):
    useLastAnalysis: bool = True
    exitPrice: float | None = None


class HealthResponse(BaseModel):
    status: str
    contractConfigured: bool
    walletConfigured: bool
    agentId: int | None
    agentConfigured: bool
    proofMode: str
    supportedAssets: list[str]
    byreal: dict[str, Any]
    apiPrefixes: list[str]


class AssetsResponse(BaseModel):
    assets: list[str]