from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from fastapi import APIRouter

from ..byreal_router import byreal_perps_health, calculate_cvar_limit, execute_perps_order


router = APIRouter(tags=["byreal-perps"])


class ByrealPerpsOrderRequest(BaseModel):
    side: Literal["long", "short", "buy", "sell"] = Field(examples=["long"])
    requested_size: float = Field(gt=0, examples=[125.0])
    symbol: str = Field(examples=["ETH-USDT"])
    capital: float = Field(gt=0, examples=[1000.0])


@router.get("/byreal/perps/cvar-limit")
@router.get("/api/byreal/perps/cvar-limit", include_in_schema=False)
async def byreal_perps_cvar_limit(capital: float, confidence_level: float = 0.95):
    return {
        "capital": capital,
        "confidenceLevel": confidence_level,
        "maxExposure": calculate_cvar_limit(capital, confidence_level),
    }


@router.get("/byreal/perps/health")
@router.get("/api/byreal/perps/health", include_in_schema=False)
async def byreal_perps_health_check():
    return byreal_perps_health()


@router.post("/byreal/perps/execute")
@router.post("/api/byreal/perps/execute", include_in_schema=False)
async def byreal_perps_execute(body: ByrealPerpsOrderRequest):
    result = await execute_perps_order(
        side=body.side,
        requested_size=body.requested_size,
        symbol=body.symbol,
        capital=body.capital,
    )
    return {
        "side": body.side,
        "requestedSize": body.requested_size,
        "symbol": body.symbol,
        "capital": body.capital,
        "cvarLimit": calculate_cvar_limit(body.capital),
        "execution": result,
    }
