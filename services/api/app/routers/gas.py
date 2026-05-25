"""Gas estimation endpoint for Mantle network transactions."""

from __future__ import annotations

from fastapi import APIRouter

from ..gas_estimator import get_gas_display

router = APIRouter(prefix="/gas", tags=["gas"])


@router.get("")
@router.get("/")
async def gas_status():
    """Return current Mantle gas fee estimates."""
    return await get_gas_display()