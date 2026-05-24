from __future__ import annotations

from fastapi import APIRouter, Request

from ..agent_card import build_agent_card
from ..erc8004_adapter import build_erc8004_status

router = APIRouter(tags=["agent"])


def _api_base(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_host:
        return f"{forwarded_proto or request.url.scheme}://{forwarded_host}"
    return str(request.base_url).rstrip("/")


@router.get("/agent/card")
@router.get("/api/agent/card", include_in_schema=False)
async def agent_card(request: Request):
    return build_agent_card(_api_base(request))


@router.get("/agent/erc8004")
@router.get("/api/agent/erc8004", include_in_schema=False)
async def erc8004_status(request: Request):
    return build_erc8004_status(api_base=_api_base(request))
