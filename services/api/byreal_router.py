import subprocess
import math
import logging
import shutil

from .app.config import BYREAL_PERPS_LIVE_ENABLED


logger = logging.getLogger(__name__)
ALLOWED_SIDES = {"long", "short", "buy", "sell"}


def calculate_cvar_limit(current_capital: float, confidence_level: float = 0.95) -> float:
    historical_returns = [-0.05, -0.02, 0.01, 0.04, -0.08, 0.03]

    sorted_returns = sorted(historical_returns)
    k = int((1 - confidence_level) * len(sorted_returns))
    cvar_slice = sorted_returns[: k + 1]
    cvar_value = sum(cvar_slice) / len(cvar_slice)
    max_exposure = current_capital * abs(cvar_value)

    return float(max_exposure)


def byreal_perps_health() -> dict:
    cli_path = shutil.which("byreal-perps-cli")
    return {
        "cliAvailable": bool(cli_path),
        "cliPath": cli_path,
        "liveEnabled": BYREAL_PERPS_LIVE_ENABLED,
        "mode": "live" if BYREAL_PERPS_LIVE_ENABLED else "dry-run",
    }


async def execute_perps_order(side: str, requested_size: float, symbol: str, capital: float):
    normalized_side = side.lower().strip()
    if normalized_side not in ALLOWED_SIDES:
        return {
            "ok": False,
            "error": f"Unsupported side '{side}'. Allowed values: {sorted(ALLOWED_SIDES)}",
            "side": normalized_side,
            "requestedSize": requested_size,
            "actualSize": 0.0,
            "cvarLimit": calculate_cvar_limit(capital),
            "returnCode": None,
            "stdout": "",
            "stderr": "",
            "timedOut": False,
            "executionMode": "rejected",
        }

    limit = calculate_cvar_limit(capital)

    if requested_size > limit:
        actual_size = limit
        logger.info(
            "Risk intercept applied: requested_size=%s exceeds cvar_limit=%s; actual_size=%s",
            requested_size,
            limit,
            actual_size,
        )
    else:
        actual_size = requested_size
        logger.info(
            "Risk intercept passed: requested_size=%s within cvar_limit=%s; actual_size=%s",
            requested_size,
            limit,
            actual_size,
        )

    cmd = [
        "byreal-perps-cli",
        "trade",
        "--side",
        normalized_side,
        "--size",
        str(actual_size),
        "--symbol",
        symbol,
    ]

    health = byreal_perps_health()
    base = {
        "side": normalized_side,
        "requestedSize": float(requested_size),
        "actualSize": float(actual_size),
        "cvarLimit": float(limit),
        "command": cmd,
        "cliAvailable": health["cliAvailable"],
        "liveEnabled": health["liveEnabled"],
    }

    if not BYREAL_PERPS_LIVE_ENABLED:
        return {
            **base,
            "ok": True,
            "returnCode": 0,
            "stdout": "Dry-run only. Set BYREAL_PERPS_LIVE_ENABLED=true to submit a live Byreal Perps order.",
            "stderr": "",
            "timedOut": False,
            "executionMode": "dry-run",
        }

    if not health["cliAvailable"]:
        return {
            **base,
            "ok": False,
            "returnCode": None,
            "stdout": "",
            "stderr": "byreal-perps-cli not found on PATH.",
            "timedOut": False,
            "executionMode": "live-unavailable",
        }

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return {
            **base,
            "ok": result.returncode == 0,
            "returnCode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timedOut": False,
            "executionMode": "live",
        }
    except subprocess.TimeoutExpired as exc:
        logger.error("Byreal perps CLI timed out: %s", exc)
        return {
            **base,
            "ok": False,
            "returnCode": None,
            "stdout": exc.stdout or "",
            "stderr": f"Byreal perps CLI timed out after 10 seconds: {exc}",
            "timedOut": True,
            "executionMode": "live-timeout",
        }
