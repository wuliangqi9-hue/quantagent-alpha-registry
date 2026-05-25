from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .config import BLOCKY402_FACILITATOR_URL, X402_MAX_AUTO_PAY_USD, X402_WALLET_ADDRESS


@dataclass(slots=True)
class X402PaymentSchema:
    amountUsd: float
    asset: str
    network: str
    recipient: str
    resource: str


class X402Client:
    """x402 Payment Required middleware.

    It parses HTTP 402 payment metadata and creates a facilitator payload.
    The current implementation is deterministic and offline-safe; a live
    Blocky402 call can replace `prepare_payment` without touching callers.
    """

    VERSION = "x402-client-1.0.0"

    def status(self) -> dict[str, Any]:
        return {
            "configured": bool(BLOCKY402_FACILITATOR_URL and X402_WALLET_ADDRESS),
            "facilitator": BLOCKY402_FACILITATOR_URL or None,
            "wallet": X402_WALLET_ADDRESS or None,
            "maxAutoPayUsd": X402_MAX_AUTO_PAY_USD,
        }

    def parse_schema(self, response_headers: dict[str, str], body: dict[str, Any] | None = None) -> X402PaymentSchema | None:
        body = body or {}
        raw_amount = body.get("amountUsd") or response_headers.get("x-402-amount-usd")
        recipient = body.get("recipient") or response_headers.get("x-402-recipient")
        if raw_amount is None or not recipient:
            return None
        return X402PaymentSchema(
            amountUsd=float(raw_amount),
            asset=str(body.get("asset") or response_headers.get("x-402-asset") or "USDC"),
            network=str(body.get("network") or response_headers.get("x-402-network") or "mantle"),
            recipient=str(recipient),
            resource=str(body.get("resource") or response_headers.get("x-402-resource") or "premium-factor-data"),
        )

    def should_pay(self, schema: X402PaymentSchema, alpha_value_bps: float) -> bool:
        decision = self.payment_policy(schema, alpha_value_bps=alpha_value_bps)
        return bool(decision["approved"])

    def prepare_payment(self, schema: X402PaymentSchema, *, alpha_value_bps: float) -> dict[str, Any]:
        policy = self.payment_policy(schema, alpha_value_bps=alpha_value_bps)
        approved = bool(policy["approved"])
        return {
            "schema": "quantagent.x402-payment-intent.v1",
            "clientVersion": self.VERSION,
            "approved": approved,
            "mode": "facilitator" if self.status()["configured"] else "simulation",
            "facilitator": BLOCKY402_FACILITATOR_URL or None,
            "payer": X402_WALLET_ADDRESS or "demo-agent-wallet",
            "payment": {
                "amountUsd": schema.amountUsd,
                "asset": schema.asset,
                "network": schema.network,
                "recipient": schema.recipient,
                "resource": schema.resource,
            },
            "alphaValueBps": alpha_value_bps,
            "paymentAudit": policy,
            "payload": (
                f"partial-signature:{schema.network}:{schema.asset}:{schema.amountUsd}:{schema.recipient}"
                if approved
                else None
            ),
        }

    def payment_policy(
        self,
        schema: X402PaymentSchema,
        *,
        alpha_value_bps: float,
        notional_usd: float = 1000.0,
        gas_cost_usd: float = 0.02,
        safety_margin_usd: float = 0.03,
    ) -> dict[str, Any]:
        expected_alpha_usd = estimate_alpha_value_usd(alpha_value_bps, notional_usd)
        total_cost = float(schema.amountUsd) + gas_cost_usd + safety_margin_usd
        approved = schema.amountUsd <= X402_MAX_AUTO_PAY_USD and expected_alpha_usd > total_cost
        return {
            "schema": "quantagent.x402-payment-policy.v1",
            "approved": approved,
            "resource": schema.resource,
            "amountUsd": schema.amountUsd,
            "notionalUsd": notional_usd,
            "alphaValueBps": alpha_value_bps,
            "expectedAlphaUsd": round(expected_alpha_usd, 6),
            "gasCostUsd": gas_cost_usd,
            "safetyMarginUsd": safety_margin_usd,
            "totalCostUsd": round(total_cost, 6),
            "maxAutoPayUsd": X402_MAX_AUTO_PAY_USD,
            "reason": (
                "expected alpha exceeds data cost plus gas and safety margin"
                if approved
                else "payment held: expected alpha or max-auto-pay policy did not justify purchase"
            ),
        }


    async def submit_to_facilitator(self, payment: dict[str, Any]) -> dict[str, Any]:
        """将部分签名的支付 payload 提交至 Blocky402 Facilitator 中继网络。

        Facilitator 负责：
        1. 验证签名
        2. 代为支付底层 Gas 费用
        3. 处理不同网络间稳定币兑换
        4. 在 Mantle/Solana/Base 上完成原子结算

        在未配置 Facilitator 时返回模拟成功结果。
        """
        payload = payment.get("payload")
        if not payload:
            return {
                "submitted": False,
                "mode": "no-payload",
                "message": "No signed payload to submit — payment was not approved.",
            }

        if not self.status()["configured"]:
            return {
                "submitted": True,
                "mode": "simulation",
                "facilitator": None,
                "payment": payment["payment"],
                "receipt": f"sim-receipt:{payment['payment']['network']}:{payment['payment']['asset']}:{payment['payment']['amountUsd']}",
                "message": "x402 Facilitator submission simulated (BLOCKY402_FACILITATOR_URL not configured).",
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{BLOCKY402_FACILITATOR_URL}/pay",
                    json={
                        "payload": payload,
                        "payer": X402_WALLET_ADDRESS,
                        "payment": payment["payment"],
                    },
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                result = resp.json()
                return {
                    "submitted": True,
                    "mode": "live-facilitator",
                    "facilitator": BLOCKY402_FACILITATOR_URL,
                    "payment": payment["payment"],
                    "receipt": result.get("receipt") or result.get("txHash"),
                    "facilitatorResponse": result,
                    "message": "x402 payment submitted to Blocky402 Facilitator and confirmed on-chain.",
                }
        except Exception as exc:
            return {
                "submitted": False,
                "mode": "facilitator-error",
                "facilitator": BLOCKY402_FACILITATOR_URL,
                "payment": payment["payment"],
                "error": str(exc),
                "message": "x402 Facilitator submission failed; payment could not be relayed.",
            }


def estimate_alpha_value_usd(alpha_value_bps: float, notional_usd: float) -> float:
    return max(0.0, float(alpha_value_bps)) / 10000.0 * max(0.0, float(notional_usd))
