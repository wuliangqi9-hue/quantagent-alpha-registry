// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC721Receiver {
    function onERC721Received(address operator, address from, uint256 tokenId, bytes calldata data)
        external
        returns (bytes4);
}

/// @title SignalRegistry
/// @notice ERC-8004-inspired identity, validation, and reputation registry for QuantAgent.
/// @dev Hackathon MVP: the three ERC-8004 layers are composed in one inspectable contract.
/// It mints transferable ERC-721-style agent identities, anchors validation requests, and
/// records reputation feedback. It does not custody funds or execute trades.
contract SignalRegistry {
    string public constant name = "QuantAgent Trustless Agent";
    string public constant symbol = "QAGENT";

    struct Agent {
        address owner;
        address wallet;
        string agentURI;
        bool active;
    }

    struct Feedback {
        address clientAddress;
        int128 value;
        uint8 valueDecimals;
        string tag1;
        string tag2;
        bool isRevoked;
    }

    struct ValidationStatus {
        address validatorAddress;
        uint256 agentId;
        uint8 response;
        bytes32 responseHash;
        string tag;
        uint256 lastUpdate;
        bool exists;
    }

    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Approval(address indexed owner, address indexed approved, uint256 indexed tokenId);
    event ApprovalForAll(address indexed owner, address indexed operator, bool approved);

    event Registered(uint256 indexed agentId, string agentURI, address indexed owner);
    event URIUpdated(uint256 indexed agentId, string newURI, address indexed updatedBy);
    event MetadataSet(uint256 indexed agentId, string indexed indexedMetadataKey, string metadataKey, bytes metadataValue);

    event SignalRecorded(
        uint256 indexed agentId,
        bytes32 indexed signalHash,
        string symbol,
        string strategyId,
        string modelVersion,
        string mode,
        bytes32 proofHash,
        string proofURI,
        uint256 timestamp
    );

    event ValidationRequest(
        address indexed validatorAddress,
        uint256 indexed agentId,
        string requestURI,
        bytes32 indexed requestHash
    );

    event ValidationResponse(
        address indexed validatorAddress,
        uint256 indexed agentId,
        bytes32 indexed requestHash,
        uint8 response,
        string responseURI,
        bytes32 responseHash,
        string tag
    );

    event NewFeedback(
        uint256 indexed agentId,
        address indexed clientAddress,
        uint64 feedbackIndex,
        int128 value,
        uint8 valueDecimals,
        string indexed indexedTag1,
        string tag1,
        string tag2,
        string endpoint,
        string feedbackURI,
        bytes32 feedbackHash
    );

    uint256 public nextAgentId = 1;

    mapping(uint256 => Agent) private agents;
    mapping(address => uint256) private balances;
    mapping(uint256 => address) private tokenApprovals;
    mapping(address => mapping(address => bool)) private operatorApprovals;
    mapping(bytes32 => bool) public recorded;
    mapping(uint256 => bytes32[]) private agentSignals;
    mapping(uint256 => mapping(string => bytes)) private metadata;
    mapping(uint256 => Feedback[]) private feedbacks;
    mapping(uint256 => mapping(address => uint64)) private feedbackCountByClient;
    mapping(bytes32 => ValidationStatus) private validations;
    mapping(uint256 => bytes32[]) private agentValidationRequests;
    mapping(address => bytes32[]) private validatorRequests;

    modifier validAgent(uint256 agentId) {
        require(agents[agentId].owner != address(0), "unknown agent");
        _;
    }

    modifier onlyAgentOwner(uint256 agentId) {
        require(agents[agentId].owner == msg.sender, "not agent owner");
        _;
    }

    modifier onlyAgentController(uint256 agentId) {
        Agent storage agent = agents[agentId];
        require(agent.owner != address(0), "unknown agent");
        require(agent.owner == msg.sender || agent.wallet == msg.sender, "not agent controller");
        _;
    }

    function supportsInterface(bytes4 interfaceId) external pure returns (bool) {
        return interfaceId == 0x01ffc9a7 // ERC-165
            || interfaceId == 0x80ac58cd // ERC-721
            || interfaceId == 0x5b5e139f; // ERC-721 metadata
    }

    function register(string calldata agentURI) external returns (uint256 agentId) {
        return _mintAgent(msg.sender, msg.sender, agentURI);
    }

    function registerWithWallet(string calldata agentURI, address agentWallet) external returns (uint256 agentId) {
        require(agentWallet != address(0), "zero wallet");
        return _mintAgent(msg.sender, agentWallet, agentURI);
    }

    function ownerOf(uint256 agentId) public view validAgent(agentId) returns (address) {
        return agents[agentId].owner;
    }

    function balanceOf(address owner) external view returns (uint256) {
        require(owner != address(0), "zero owner");
        return balances[owner];
    }

    function tokenURI(uint256 agentId) external view validAgent(agentId) returns (string memory) {
        return agents[agentId].agentURI;
    }

    function approve(address to, uint256 agentId) external onlyAgentOwner(agentId) {
        tokenApprovals[agentId] = to;
        emit Approval(msg.sender, to, agentId);
    }

    function getApproved(uint256 agentId) public view validAgent(agentId) returns (address) {
        return tokenApprovals[agentId];
    }

    function setApprovalForAll(address operator, bool approved) external {
        require(operator != msg.sender, "self approval");
        operatorApprovals[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }

    function isApprovedForAll(address owner, address operator) public view returns (bool) {
        return operatorApprovals[owner][operator];
    }

    function transferFrom(address from, address to, uint256 agentId) public validAgent(agentId) {
        require(_isApprovedOrOwner(msg.sender, agentId), "not approved");
        require(agents[agentId].owner == from, "wrong owner");
        require(to != address(0), "zero to");
        _transfer(from, to, agentId);
    }

    function safeTransferFrom(address from, address to, uint256 agentId) external {
        safeTransferFrom(from, to, agentId, "");
    }

    function safeTransferFrom(address from, address to, uint256 agentId, bytes memory data) public {
        transferFrom(from, to, agentId);
        if (to.code.length > 0) {
            require(
                IERC721Receiver(to).onERC721Received(msg.sender, from, agentId, data)
                    == IERC721Receiver.onERC721Received.selector,
                "unsafe receiver"
            );
        }
    }

    function getAgentWallet(uint256 agentId) external view validAgent(agentId) returns (address) {
        return agents[agentId].wallet;
    }

    function setAgentURI(uint256 agentId, string calldata newURI) external onlyAgentOwner(agentId) {
        agents[agentId].agentURI = newURI;
        emit URIUpdated(agentId, newURI, msg.sender);
    }

    function setAgentWallet(uint256 agentId, address newWallet) external onlyAgentOwner(agentId) {
        require(newWallet != address(0), "zero wallet");
        agents[agentId].wallet = newWallet;
        emit MetadataSet(agentId, "agentWallet", "agentWallet", abi.encode(newWallet));
    }

    function getMetadata(uint256 agentId, string memory metadataKey)
        external
        view
        validAgent(agentId)
        returns (bytes memory)
    {
        return metadata[agentId][metadataKey];
    }

    function setMetadata(uint256 agentId, string calldata metadataKey, bytes calldata metadataValue)
        external
        onlyAgentOwner(agentId)
    {
        require(keccak256(bytes(metadataKey)) != keccak256(abi.encodePacked("agentWallet")), "reserved key");
        metadata[agentId][metadataKey] = metadataValue;
        emit MetadataSet(agentId, metadataKey, metadataKey, metadataValue);
    }

    /// @notice Backward-compatible signal recorder for early demos without an agent identity.
    function recordSignal(
        bytes32 signalHash,
        string calldata assetSymbol,
        string calldata strategyId,
        string calldata modelVersion,
        string calldata mode
    ) external {
        _recordSignal(0, signalHash, assetSymbol, strategyId, modelVersion, mode, bytes32(0), "");
    }

    /// @notice Record a signal and open an ERC-8004-style validation request for the agent.
    function recordSignalForAgent(
        uint256 agentId,
        bytes32 signalHash,
        string calldata assetSymbol,
        string calldata strategyId,
        string calldata modelVersion,
        string calldata mode,
        address validatorAddress,
        string calldata proofURI,
        bytes32 proofHash
    ) external onlyAgentController(agentId) {
        require(validatorAddress != address(0), "zero validator");
        _recordSignal(agentId, signalHash, assetSymbol, strategyId, modelVersion, mode, proofHash, proofURI);
        _validationRequest(validatorAddress, agentId, proofURI, signalHash);
    }

    function validationRequest(
        address validatorAddress,
        uint256 agentId,
        string calldata requestURI,
        bytes32 requestHash
    ) external onlyAgentController(agentId) {
        _validationRequest(validatorAddress, agentId, requestURI, requestHash);
    }

    function validationResponse(
        bytes32 requestHash,
        uint8 response,
        string calldata responseURI,
        bytes32 responseHash,
        string calldata tag
    ) external {
        ValidationStatus storage status = validations[requestHash];
        require(status.exists, "unknown request");
        require(status.validatorAddress == msg.sender, "not validator");
        require(response <= 100, "response > 100");
        status.response = response;
        status.responseHash = responseHash;
        status.tag = tag;
        status.lastUpdate = block.timestamp;
        emit ValidationResponse(msg.sender, status.agentId, requestHash, response, responseURI, responseHash, tag);
    }

    function giveFeedback(
        uint256 agentId,
        int128 value,
        uint8 valueDecimals,
        string calldata tag1,
        string calldata tag2,
        string calldata endpoint,
        string calldata feedbackURI,
        bytes32 feedbackHash
    ) external validAgent(agentId) {
        require(valueDecimals <= 18, "too many decimals");

        feedbacks[agentId].push(Feedback({
            clientAddress: msg.sender,
            value: value,
            valueDecimals: valueDecimals,
            tag1: tag1,
            tag2: tag2,
            isRevoked: false
        }));
        feedbackCountByClient[agentId][msg.sender] += 1;
        emit NewFeedback(
            agentId,
            msg.sender,
            feedbackCountByClient[agentId][msg.sender],
            value,
            valueDecimals,
            tag1,
            tag1,
            tag2,
            endpoint,
            feedbackURI,
            feedbackHash
        );
    }

    function getReputationSummary(uint256 agentId)
        external
        view
        validAgent(agentId)
        returns (uint64 count, int128 summaryValue, uint8 summaryValueDecimals)
    {
        Feedback[] storage list = feedbacks[agentId];
        int256 sum = 0;
        for (uint256 i = 0; i < list.length; i++) {
            if (!list[i].isRevoked) {
                count += 1;
                sum += list[i].value;
            }
        }
        summaryValue = count == 0 ? int128(0) : int128(sum / int256(uint256(count)));
        summaryValueDecimals = 4;
    }

    function getValidationStatus(bytes32 requestHash)
        external
        view
        returns (
            address validatorAddress,
            uint256 agentId,
            uint8 response,
            bytes32 responseHash,
            string memory tag,
            uint256 lastUpdate
        )
    {
        ValidationStatus storage status = validations[requestHash];
        return (
            status.validatorAddress,
            status.agentId,
            status.response,
            status.responseHash,
            status.tag,
            status.lastUpdate
        );
    }

    function getAgentValidations(uint256 agentId) external view returns (bytes32[] memory) {
        return agentValidationRequests[agentId];
    }

    function getValidatorRequests(address validatorAddress) external view returns (bytes32[] memory) {
        return validatorRequests[validatorAddress];
    }

    function getAgentSignals(uint256 agentId) external view returns (bytes32[] memory) {
        return agentSignals[agentId];
    }

    function _mintAgent(address to, address agentWallet, string calldata agentURI) private returns (uint256 agentId) {
        require(to != address(0), "zero owner");
        require(bytes(agentURI).length > 0, "empty uri");

        agentId = nextAgentId++;
        agents[agentId] = Agent({
            owner: to,
            wallet: agentWallet,
            agentURI: agentURI,
            active: true
        });
        balances[to] += 1;

        emit Transfer(address(0), to, agentId);
        emit Registered(agentId, agentURI, to);
        emit MetadataSet(agentId, "agentWallet", "agentWallet", abi.encode(agentWallet));
    }

    function _transfer(address from, address to, uint256 agentId) private {
        balances[from] -= 1;
        balances[to] += 1;
        agents[agentId].owner = to;
        agents[agentId].wallet = to;
        delete tokenApprovals[agentId];

        emit Transfer(from, to, agentId);
        emit MetadataSet(agentId, "agentWallet", "agentWallet", abi.encode(to));
    }

    function _isApprovedOrOwner(address spender, uint256 agentId) private view returns (bool) {
        address owner = agents[agentId].owner;
        return spender == owner || getApproved(agentId) == spender || isApprovedForAll(owner, spender);
    }

    function _recordSignal(
        uint256 agentId,
        bytes32 signalHash,
        string memory assetSymbol,
        string memory strategyId,
        string memory modelVersion,
        string memory mode,
        bytes32 proofHash,
        string memory proofURI
    ) private {
        require(signalHash != bytes32(0), "empty hash");
        require(!recorded[signalHash], "already recorded");
        if (agentId != 0) {
            require(agents[agentId].owner != address(0), "unknown agent");
            agentSignals[agentId].push(signalHash);
        }
        recorded[signalHash] = true;
        emit SignalRecorded(agentId, signalHash, assetSymbol, strategyId, modelVersion, mode, proofHash, proofURI, block.timestamp);
    }

    function _validationRequest(
        address validatorAddress,
        uint256 agentId,
        string memory requestURI,
        bytes32 requestHash
    ) private validAgent(agentId) {
        require(validatorAddress != address(0), "zero validator");
        require(requestHash != bytes32(0), "empty request hash");
        require(!validations[requestHash].exists, "request exists");
        validations[requestHash] = ValidationStatus({
            validatorAddress: validatorAddress,
            agentId: agentId,
            response: 0,
            responseHash: bytes32(0),
            tag: "requested",
            lastUpdate: block.timestamp,
            exists: true
        });
        agentValidationRequests[agentId].push(requestHash);
        validatorRequests[validatorAddress].push(requestHash);
        emit ValidationRequest(validatorAddress, agentId, requestURI, requestHash);
    }
}
