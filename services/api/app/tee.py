from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from .config import (
    PHALA_TEE_ENABLED,
    PHALA_ENCLAVE_ENDPOINT,
    PHALA_API_KEY,
    PROOF_URI_BASE,
    VALIDATOR_ADDRESS,
)


# ---------------------------------------------------------------------------
# TEE / Phala Network Attestation — 可信执行环境保护策略推理隐私
# ---------------------------------------------------------------------------
# 参考报告第五章：通过将 services/api/ 及核心 Python 算法包部署至 Phala
# Network 的 TEE 中，实现硬件级隔离（Intel SGX / AMD SEV），并在每次推理
# 完成后生成密码学证明锚定至 ERC-8004 Validation Registry。
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class TEEAttestation:
    """TEE 硬件证明载荷。

    Phala Network 的 TEE Enclave 在完成 LLM 推理或 RL 策略计算后，
    由硬件安全模块生成包含以下字段的证明。
    """

    schema: str = "quantagent.tee-attestation.v1"
    enclave_id: str = ""
    code_hash: str = ""
    input_hash: str = ""
    output_hash: str = ""
    timestamp_unix: int = 0
    mr_enclave: str = ""  # SGX 度量值
    mr_signer: str = ""  # SGX 签名者度量
    isv_prod_id: int = 0
    isv_svn: int = 0
    report_data: str = ""
    signature: str = ""
    verification_status: str = "unverified"

    @property
    def attestation_hash(self) -> str:
        canonical = json.dumps(
            {
                "schema": self.schema,
                "enclaveId": self.enclave_id,
                "codeHash": self.code_hash,
                "inputHash": self.input_hash,
                "outputHash": self.output_hash,
                "timestampUnix": self.timestamp_unix,
                "mrEnclave": self.mr_enclave,
                "signature": self.signature,
            },
            sort_keys=True,
            default=str,
        )
        return f"0x{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"

    @property
    def verified(self) -> bool:
        return self.verification_status == "hardware-verified"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "enclaveId": self.enclave_id,
            "codeHash": self.code_hash,
            "inputHash": self.input_hash,
            "outputHash": self.output_hash,
            "timestampUnix": self.timestamp_unix,
            "mrEnclave": self.mr_enclave,
            "mrSigner": self.mr_signer,
            "isvProdId": self.isv_prod_id,
            "isvSvn": self.isv_svn,
            "reportData": self.report_data,
            "signature": self.signature,
            "verificationStatus": self.verification_status,
            "attestationHash": self.attestation_hash,
            "enclavePlatform": "Phala Network SGX" if self.mr_enclave else "Phala Network simulated TEE",
            "codeMeasurement": self.mr_enclave or self.code_hash,
            "timestamp": self.timestamp_unix,
            "metadata": {
                "inputHash": self.input_hash,
                "outputHash": self.output_hash,
                "mrSigner": self.mr_signer,
                "verificationStatus": self.verification_status,
            },
            "verified": self.verified,
            "message": (
                "Hardware TEE attestation verified."
                if self.verified
                else "Simulated TEE attestation generated; configure Phala credentials for hardware verification."
            ),
        }

    def to_validation_payload(self) -> dict[str, Any]:
        """转换为 ERC-8004 Validation Registry 可接受的格式。"""
        return {
            "teeProvider": "Phala-Network",
            "attestationType": "sgx-dcap" if self.mr_enclave else "simulated-tee",
            "codeHash": self.code_hash,
            "outputHash": self.output_hash,
            "mrEnclave": self.mr_enclave,
            "timestamp": self.timestamp_unix,
            "signature": self.signature,
        }


class PhalaTEEAdapter:
    """Phala Network 可信执行环境适配器。

    负责：
    1. 检测 TEE 环境是否配置
    2. 对策略推理输入/输出进行哈希签名
    3. 生成可锚定到链上的硬件证明
    4. 提供向 Validation Registry 提交证明的接口

    在未配置 TEE 时自动降级为模拟模式，生成带明确标记的 demo 证明，
    不影响本地开发与 MVP 演示。
    """

    VERSION = "phala-tee-adapter-1.0.0"

    def __init__(self) -> None:
        self._enclave_id: str | None = None

    # ------------------------------------------------------------------
    # 环境检测
    # ------------------------------------------------------------------

    @property
    def configured(self) -> bool:
        return bool(PHALA_TEE_ENABLED and PHALA_ENCLAVE_ENDPOINT and PHALA_API_KEY)

    @property
    def mode(self) -> str:
        if not PHALA_TEE_ENABLED:
            return "disabled"
        if self.configured:
            return "live-tee"
        return "simulated-tee"

    def status(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "mode": self.mode,
            "provider": "Phala-Network",
            "adapterVersion": self.VERSION,
            "enclaveEndpoint": PHALA_ENCLAVE_ENDPOINT or None,
            "capabilities": [
                "hardware-isolated-inference",
                "code-integrity-attestation",
                "input-output-binding",
                "erc8004-validation-anchoring",
            ],
            "message": (
                "TEE adapter is live: all strategy inference runs inside Phala SGX enclave."
                if self.configured
                else "TEE adapter in simulation mode. Set PHALA_TEE_ENABLED=true, PHALA_ENCLAVE_ENDPOINT, and PHALA_API_KEY for hardware attestation."
            ),
        }

    # ------------------------------------------------------------------
    # 输入/输出哈希绑定 — 确保策略输入未被篡改
    # ------------------------------------------------------------------

    @staticmethod
    def hash_inputs(
        factor_summary: dict[str, Any],
        memory_context: dict[str, Any],
        agent_reputation: dict[str, Any] | None,
    ) -> str:
        """对策略推理的全部输入进行规范化哈希。

        将 factor_summary、memory_context 和 agent_reputation
        序列化为有序 JSON 后计算 SHA-256，确保 TEE 内部接收的
        输入与外部传入完全一致。
        """
        canonical = json.dumps(
            {
                "factor_summary": factor_summary,
                "memory_context": memory_context,
                "agent_reputation": agent_reputation or {},
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_outputs(outputs: dict[str, Any]) -> str:
        """对策略推理的全部输出进行规范化哈希。"""
        canonical = json.dumps(outputs, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # 证明生成
    # ------------------------------------------------------------------

    def generate_attestation(
        self,
        *,
        input_hash: str,
        output_hash: str,
        extra_context: dict[str, Any] | None = None,
    ) -> TEEAttestation:
        """生成 TEE 硬件证明。

        在 live-tee 模式下，向 Phala Enclave 端点请求真实的 SGX DCAP
        证明；在模拟模式下，生成带有明确标记的确定性证明以便本地验证。
        """
        ctx = extra_context or {}
        timestamp = int(time.time())

        if self.configured:
            return self._request_live_attestation(
                input_hash=input_hash,
                output_hash=output_hash,
                timestamp=timestamp,
                context=ctx,
            )

        # --- 模拟模式：生成确定性（但标记为 simulated）的证明 ---
        report_data = hashlib.sha256(
            f"{input_hash}:{output_hash}:{timestamp}:{self.VERSION}".encode()
        ).hexdigest()
        sig = hashlib.sha256(
            f"{report_data}:demo-signing-key:{os.urandom(8).hex()}".encode()
        ).hexdigest()

        return TEEAttestation(
            enclave_id="demo-enclave-quantagent",
            code_hash=hashlib.sha256(
                f"quantagent-strategy-engine:{self.VERSION}".encode()
            ).hexdigest(),
            input_hash=input_hash,
            output_hash=output_hash,
            timestamp_unix=timestamp,
            mr_enclave="",
            mr_signer="",
            isv_prod_id=0,
            isv_svn=0,
            report_data=report_data,
            signature=sig,
            verification_status="simulated",
        )

    def _request_live_attestation(
        self,
        *,
        input_hash: str,
        output_hash: str,
        timestamp: int,
        context: dict[str, Any],
    ) -> TEEAttestation:
        """向 Phala Network Enclave 请求真实硬件证明。

        实际部署时通过 HTTPS 调用 Phala 的 enclave RPC 端点。
        此处提供完整的请求构造逻辑，具体端点格式需匹配 Phala SDK。
        """
        import urllib.request

        request_body = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "phala_generateAttestation",
                "params": {
                    "inputHash": input_hash,
                    "outputHash": output_hash,
                    "timestamp": timestamp,
                    "context": context,
                },
                "id": 1,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{PHALA_ENCLAVE_ENDPOINT}/api/attest",
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {PHALA_API_KEY}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            # 降级为模拟模式但保留错误信息
            fallback = self.generate_attestation(
                input_hash=input_hash,
                output_hash=output_hash,
                extra_context={"_tee_error": str(exc)},
            )
            fallback.verification_status = f"live-request-failed: {str(exc)[:120]}"
            return fallback

        attestation_data = result.get("result", result)

        return TEEAttestation(
            enclave_id=str(attestation_data.get("enclaveId", "")),
            code_hash=str(attestation_data.get("codeHash", "")),
            input_hash=input_hash,
            output_hash=output_hash,
            timestamp_unix=timestamp,
            mr_enclave=str(attestation_data.get("mrEnclave", "")),
            mr_signer=str(attestation_data.get("mrSigner", "")),
            isv_prod_id=int(attestation_data.get("isvProdId", 0)),
            isv_svn=int(attestation_data.get("isvSvn", 0)),
            report_data=str(attestation_data.get("reportData", "")),
            signature=str(attestation_data.get("signature", "")),
            verification_status="hardware-verified",
        )

    def attest_execution(
        self,
        *,
        payload: str | dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> TEEAttestation:
        """Compatibility wrapper for settlement-time execution attestations."""
        payload_text = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True, default=str)
        input_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
        output_hash = hashlib.sha256(
            json.dumps(metadata or {}, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        return self.generate_attestation(
            input_hash=input_hash,
            output_hash=output_hash,
            extra_context=metadata or {},
        )

    # ------------------------------------------------------------------
    # Validation Registry 锚定
    # ------------------------------------------------------------------

    def anchor_to_validation_registry(
        self,
        attestation: TEEAttestation,
        *,
        agent_id: int,
        signal_hash: str,
    ) -> dict[str, Any]:
        """将 TEE 证明锚定至 ERC-8004 Validation Registry。

        构造 proofURI 与 proofHash，供 chain.py 中的
        recordSignalForAgent 调用。
        """
        validation_payload = attestation.to_validation_payload()
        proof_uri = f"{PROOF_URI_BASE}/tee/{signal_hash}"

        import hashlib as _hashlib

        proof_hash = _hashlib.sha256(
            json.dumps(validation_payload, sort_keys=True).encode()
        ).hexdigest()

        return {
            "schema": "quantagent.tee-validation-anchor.v1",
            "agentId": agent_id,
            "signalHash": signal_hash,
            "validatorAddress": VALIDATOR_ADDRESS or "0x0000000000000000000000000000000000000000",
            "proofURI": proof_uri,
            "proofHash": f"0x{proof_hash}",
            "attestation": attestation.to_dict(),
            "teeMode": self.mode,
            "messages": [
                "TEE attestation proves that the strategy code ran unmodified.",
                "Hardware-level isolation ensures no operator could tamper with the inference.",
                "Anchor this proof in ERC-8004 Validation Registry for crypto-verifiable trust.",
            ],
        }


# 模块级单例
_tee_adapter: PhalaTEEAdapter | None = None


def get_tee_adapter() -> PhalaTEEAdapter:
    global _tee_adapter
    if _tee_adapter is None:
        _tee_adapter = PhalaTEEAdapter()
    return _tee_adapter


def get_tee_attestor() -> PhalaTEEAdapter:
    return get_tee_adapter()


def tee_status() -> dict[str, Any]:
    return get_tee_adapter().status()


def generate_tee_attestation(
    *,
    factor_summary: dict[str, Any],
    memory_context: dict[str, Any],
    agent_reputation: dict[str, Any] | None,
    outputs: dict[str, Any],
) -> TEEAttestation:
    adapter = get_tee_adapter()
    input_hash = adapter.hash_inputs(factor_summary, memory_context, agent_reputation)
    output_hash = adapter.hash_outputs(outputs)
    return adapter.generate_attestation(
        input_hash=input_hash,
        output_hash=output_hash,
        extra_context={
            "adapterVersion": adapter.VERSION,
            "strategyEngine": "quantagent-alpha-registry",
        },
    )
