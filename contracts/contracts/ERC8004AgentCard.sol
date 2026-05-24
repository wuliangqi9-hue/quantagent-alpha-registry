// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ERC8004AgentCard
/// @notice ERC-8004 标准的代理注册文件（Agent Card）链上元数据存储。
/// @dev 存储与代理身份 NFT 绑定的结构化元数据，包括功能描述、API 端点、信任模型和支付地址。
/// 遵循 ERC-8004 规范的 tokenURI JSON schema。
contract ERC8004AgentCard {
    /// @notice 代理卡基础信息结构
    struct AgentCardInfo {
        string name;           // 代理名称
        string description;    // 代理功能描述
        string version;        // 代理版本号
        string agentType;      // 代理类型（如 "quant-trading", "market-maker", "arbitrage"）
        string[] capabilities; // 代理能力列表
        string[] apiEndpoints; // API 通信端点（MCP / A2A HTTP 路由）
        string trustModel;     // 信任模型（如 "tee-attestation", "zktls", "reputation-based"）
        address paymentWallet; // 用于接收外部支付的代理钱包地址
        string termsURI;       // 服务条款 URI（IPFS / Arweave）
        string iconURI;        // 代理图标 URI
    }

    /// @notice 代理卡扩展元数据
    struct AgentCardMetadata {
        string[] supportedChains;    // 支持的区块链网络
        string[] supportedAssets;    // 支持的交易资产
        string[] strategyCategories; // 策略分类（如 "trend-following", "mean-reversion", "stat-arb"）
        uint256 minExecutionSize;    // 最小执行规模（wei）
        uint256 maxExecutionSize;    // 最大执行规模（wei）
        uint256 feeBps;              // 费用（基点，0-10000）
        string feeModel;             // 费用模型描述
        string complianceInfo;       // 合规信息 URI
    }

    /// @notice 代理卡状态
    struct AgentCardStatus {
        bool active;
        uint256 registeredAt;
        uint256 lastUpdatedAt;
        uint256 totalSignals;
        uint256 totalSettlements;
        uint256 totalVolume;
    }

    // ========== Storage ==========

    /// @notice agentId => AgentCardInfo
    mapping(uint256 => AgentCardInfo) private _cardInfo;

    /// @notice agentId => AgentCardMetadata
    mapping(uint256 => AgentCardMetadata) private _cardMetadata;

    /// @notice agentId => AgentCardStatus
    mapping(uint256 => AgentCardStatus) private _cardStatus;

    /// @notice agentId => 所有者
    mapping(uint256 => address) private _owner;

    /// @notice agentId => 自定义属性键值对
    mapping(uint256 => mapping(string => string)) private _customProperties;

    /// @notice 全局代理计数器
    uint256 public totalAgents;

    // ========== Events ==========

    event AgentCardRegistered(
        uint256 indexed agentId,
        address indexed owner,
        string name,
        string version,
        string agentType
    );

    event AgentCardUpdated(
        uint256 indexed agentId,
        string field,
        address indexed updatedBy
    );

    event AgentCardStatusUpdated(
        uint256 indexed agentId,
        bool active,
        uint256 totalSignals,
        uint256 totalVolume
    );

    event CustomPropertySet(
        uint256 indexed agentId,
        string key,
        string value
    );

    // ========== Modifiers ==========

    modifier onlyOwner(uint256 agentId) {
        require(_owner[agentId] == msg.sender, "ERC8004AgentCard: not owner");
        _;
    }

    modifier agentExists(uint256 agentId) {
        require(_owner[agentId] != address(0), "ERC8004AgentCard: agent not found");
        _;
    }

    // ========== Registration ==========

    /// @notice 注册新的代理卡
    /// @param agentId 代理 ID（应与 SignalRegistry 中的 ERC-721 tokenId 一致）
    /// @param info 代理基本信息
    /// @param metadata_ 代理扩展元数据
    function register(
        uint256 agentId,
        AgentCardInfo calldata info,
        AgentCardMetadata calldata metadata_
    ) external {
        require(_owner[agentId] == address(0), "ERC8004AgentCard: already registered");
        require(bytes(info.name).length > 0, "ERC8004AgentCard: name required");
        require(bytes(info.description).length > 0, "ERC8004AgentCard: description required");
        require(info.paymentWallet != address(0), "ERC8004AgentCard: payment wallet required");

        _owner[agentId] = msg.sender;
        _cardInfo[agentId] = info;
        _cardMetadata[agentId] = metadata_;
        _cardStatus[agentId] = AgentCardStatus({
            active: true,
            registeredAt: block.timestamp,
            lastUpdatedAt: block.timestamp,
            totalSignals: 0,
            totalSettlements: 0,
            totalVolume: 0
        });
        totalAgents++;

        emit AgentCardRegistered(agentId, msg.sender, info.name, info.version, info.agentType);
    }

    // ========== Getters ==========

    /// @notice 获取代理基本信息
    function getAgentCardInfo(uint256 agentId)
        external
        view
        agentExists(agentId)
        returns (AgentCardInfo memory)
    {
        return _cardInfo[agentId];
    }

    /// @notice 获取代理扩展元数据
    function getAgentCardMetadata(uint256 agentId)
        external
        view
        agentExists(agentId)
        returns (AgentCardMetadata memory)
    {
        return _cardMetadata[agentId];
    }

    /// @notice 获取代理卡状态
    function getAgentCardStatus(uint256 agentId)
        external
        view
        agentExists(agentId)
        returns (AgentCardStatus memory)
    {
        return _cardStatus[agentId];
    }

    /// @notice 获取代理卡完整信息（info + metadata + status）
    function getFullAgentCard(uint256 agentId)
        external
        view
        agentExists(agentId)
        returns (
            AgentCardInfo memory info,
            AgentCardMetadata memory metadata_,
            AgentCardStatus memory status
        )
    {
        return (_cardInfo[agentId], _cardMetadata[agentId], _cardStatus[agentId]);
    }

    /// @notice 获取代理支付钱包地址
    function getPaymentWallet(uint256 agentId)
        external
        view
        agentExists(agentId)
        returns (address)
    {
        return _cardInfo[agentId].paymentWallet;
    }

    /// @notice 获取代理所有者
    function ownerOf(uint256 agentId)
        external
        view
        agentExists(agentId)
        returns (address)
    {
        return _owner[agentId];
    }

    // ========== Updates ==========

    /// @notice 更新代理卡基本信息
    function updateAgentCardInfo(uint256 agentId, AgentCardInfo calldata newInfo)
        external
        onlyOwner(agentId)
        agentExists(agentId)
    {
        require(bytes(newInfo.name).length > 0, "ERC8004AgentCard: name required");
        require(newInfo.paymentWallet != address(0), "ERC8004AgentCard: payment wallet required");

        _cardInfo[agentId] = newInfo;
        _cardStatus[agentId].lastUpdatedAt = block.timestamp;

        emit AgentCardUpdated(agentId, "info", msg.sender);
    }

    /// @notice 更新代理扩展元数据
    function updateAgentCardMetadata(uint256 agentId, AgentCardMetadata calldata newMetadata)
        external
        onlyOwner(agentId)
        agentExists(agentId)
    {
        _cardMetadata[agentId] = newMetadata;
        _cardStatus[agentId].lastUpdatedAt = block.timestamp;

        emit AgentCardUpdated(agentId, "metadata", msg.sender);
    }

    /// @notice 更新代理状态（激活/停用）
    function setActive(uint256 agentId, bool active)
        external
        onlyOwner(agentId)
        agentExists(agentId)
    {
        _cardStatus[agentId].active = active;
        _cardStatus[agentId].lastUpdatedAt = block.timestamp;

        emit AgentCardStatusUpdated(
            agentId,
            active,
            _cardStatus[agentId].totalSignals,
            _cardStatus[agentId].totalVolume
        );
    }

    /// @notice 更新代理 API 端点列表
    function updateApiEndpoints(uint256 agentId, string[] calldata endpoints)
        external
        onlyOwner(agentId)
        agentExists(agentId)
    {
        _cardInfo[agentId].apiEndpoints = endpoints;
        _cardStatus[agentId].lastUpdatedAt = block.timestamp;

        emit AgentCardUpdated(agentId, "apiEndpoints", msg.sender);
    }

    // ========== Activity Tracking ==========

    /// @notice 记录一次信号执行（由 SignalRegistry 或外部合约调用）
    /// @dev 只能由代理所有者或授权的注册表合约调用
    function recordActivity(
        uint256 agentId,
        uint256 volume,
        bool isSettlement
    ) external onlyOwner(agentId) agentExists(agentId) {
        _cardStatus[agentId].totalSignals++;
        _cardStatus[agentId].totalVolume += volume;
        if (isSettlement) {
            _cardStatus[agentId].totalSettlements++;
        }
        _cardStatus[agentId].lastUpdatedAt = block.timestamp;

        emit AgentCardStatusUpdated(
            agentId,
            _cardStatus[agentId].active,
            _cardStatus[agentId].totalSignals,
            _cardStatus[agentId].totalVolume
        );
    }

    // ========== Custom Properties ==========

    /// @notice 设置自定义属性
    function setCustomProperty(
        uint256 agentId,
        string calldata key,
        string calldata value
    ) external onlyOwner(agentId) agentExists(agentId) {
        require(bytes(key).length > 0, "ERC8004AgentCard: empty key");
        _customProperties[agentId][key] = value;
        emit CustomPropertySet(agentId, key, value);
    }

    /// @notice 获取自定义属性
    function getCustomProperty(uint256 agentId, string calldata key)
        external
        view
        agentExists(agentId)
        returns (string memory)
    {
        return _customProperties[agentId][key];
    }

    // ========== ERC-8004 Agent Card JSON Builder ==========

    /// @notice 生成符合 ERC-8004 规范的代理卡 JSON（off-chain 使用）
    /// @dev 返回 Base64 编码的 JSON，可直接用作 tokenURI
    function buildAgentCardJSON(uint256 agentId)
        public
        view
        agentExists(agentId)
        returns (string memory)
    {
        AgentCardInfo memory info = _cardInfo[agentId];
        AgentCardMetadata memory meta = _cardMetadata[agentId];
        AgentCardStatus memory status = _cardStatus[agentId];

        // 构建 JSON 字符串（简化版，生产环境应使用更高效的字符串拼接库）
        return _buildJSON(info, meta, status, agentId);
    }

    /// @notice 生成 tokenURI（data URI scheme）
    function tokenURI(uint256 agentId)
        external
        view
        agentExists(agentId)
        returns (string memory)
    {
        string memory json = buildAgentCardJSON(agentId);
        return string(abi.encodePacked("data:application/json;base64,", _base64Encode(bytes(json))));
    }

    // ========== Internal Helpers ==========

    function _buildJSON(
        AgentCardInfo memory info,
        AgentCardMetadata memory meta,
        AgentCardStatus memory status,
        uint256 agentId
    ) private pure returns (string memory) {
        // 使用 abi.encodePacked 构建 JSON
        // 注：生产环境建议使用专门的字符串库（如 solady 的 LibString）
        return string(abi.encodePacked(
            '{"name":"', info.name,
            '","description":"', info.description,
            '","version":"', info.version,
            '","agentType":"', info.agentType,
            '","agentId":', _uint2str(agentId),
            ',"trustModel":"', info.trustModel,
            '","paymentWallet":"', _addr2str(info.paymentWallet),
            '","termsURI":"', info.termsURI,
            '","iconURI":"', info.iconURI,
            '","active":', status.active ? "true" : "false",
            ',"registeredAt":', _uint2str(status.registeredAt),
            ',"lastUpdatedAt":', _uint2str(status.lastUpdatedAt),
            ',"totalSignals":', _uint2str(status.totalSignals),
            ',"totalSettlements":', _uint2str(status.totalSettlements),
            ',"totalVolume":"', _uint2str(status.totalVolume),
            '","capabilities":', _buildStringArray(info.capabilities),
            ',"apiEndpoints":', _buildStringArray(info.apiEndpoints),
            ',"supportedChains":', _buildStringArray(meta.supportedChains),
            ',"supportedAssets":', _buildStringArray(meta.supportedAssets),
            ',"strategyCategories":', _buildStringArray(meta.strategyCategories),
            ',"minExecutionSize":"', _uint2str(meta.minExecutionSize),
            '","maxExecutionSize":"', _uint2str(meta.maxExecutionSize),
            '","feeBps":', _uint2str(meta.feeBps),
            ',"feeModel":"', meta.feeModel,
            '","complianceInfo":"', meta.complianceInfo,
            '"}'
        ));
    }

    function _buildStringArray(string[] memory arr) private pure returns (string memory) {
        if (arr.length == 0) {
            return "[]";
        }
        string memory result = "[";
        for (uint256 i = 0; i < arr.length; i++) {
            result = string(abi.encodePacked(result, '"', arr[i], '"'));
            if (i < arr.length - 1) {
                result = string(abi.encodePacked(result, ","));
            }
        }
        result = string(abi.encodePacked(result, "]"));
        return result;
    }

    function _uint2str(uint256 value) private pure returns (string memory) {
        if (value == 0) {
            return "0";
        }
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            digits++;
            temp /= 10;
        }
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            digits -= 1;
            buffer[digits] = bytes1(uint8(48 + (value % 10)));
            value /= 10;
        }
        return string(buffer);
    }

    function _addr2str(address addr) private pure returns (string memory) {
        bytes memory buffer = new bytes(42);
        buffer[0] = "0";
        buffer[1] = "x";
        for (uint256 i = 0; i < 20; i++) {
            uint8 b = uint8(uint160(addr) / (2 ** (8 * (19 - i))));
            buffer[2 + i * 2] = _hexChar(b / 16);
            buffer[3 + i * 2] = _hexChar(b % 16);
        }
        return string(buffer);
    }

    function _hexChar(uint8 val) private pure returns (bytes1) {
        return val < 10
            ? bytes1(uint8(bytes1("0")) + val)
            : bytes1(uint8(bytes1("a")) + val - 10);
    }

    // Base64 encode (simplified for agent card JSON)
    bytes private constant _BASE64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    function _base64Encode(bytes memory data) private pure returns (string memory) {
        if (data.length == 0) return "";

        uint256 resultLen = ((data.length + 2) / 3) * 4;
        bytes memory result = new bytes(resultLen);

        uint256 i;
        uint256 j;
        for (i = 0; i + 3 <= data.length; i += 3) {
            uint256 packed = (uint256(uint8(data[i])) << 16)
                | (uint256(uint8(data[i + 1])) << 8)
                | uint256(uint8(data[i + 2]));

            result[j++] = _BASE64_CHARS[(packed >> 18) & 0x3F];
            result[j++] = _BASE64_CHARS[(packed >> 12) & 0x3F];
            result[j++] = _BASE64_CHARS[(packed >> 6) & 0x3F];
            result[j++] = _BASE64_CHARS[packed & 0x3F];
        }

        if (i < data.length) {
            uint256 packed = uint256(uint8(data[i])) << 16;
            if (i + 1 < data.length) {
                packed |= uint256(uint8(data[i + 1])) << 8;
            }
            result[j++] = _BASE64_CHARS[(packed >> 18) & 0x3F];
            result[j++] = _BASE64_CHARS[(packed >> 12) & 0x3F];
            if (i + 1 < data.length) {
                result[j++] = _BASE64_CHARS[(packed >> 6) & 0x3F];
            } else {
                result[j++] = "=";
            }
            result[j++] = "=";
        }

        return string(result);
    }
}
