"""
Centralized contract addresses, chain config, and protocol constants.

All on-chain addresses and endpoints referenced by the auction engine,
MCP server, scripts, and worker live here. These are public blockchain
constants, not secrets.
"""

# ---------------------------------------------------------------------------
# ERC-8004 Identity Registry (same address on all Base chains)
# ---------------------------------------------------------------------------
IDENTITY_REGISTRY = "0x8004A818BFB912233c491871b3d84c89A494BD9e"
GET_AGENT_WALLET_SELECTOR = "0x00339509"

# ---------------------------------------------------------------------------
# EAS (Ethereum Attestation Service) — Base predeploy
# ---------------------------------------------------------------------------
EAS_ADDRESS = "0x4200000000000000000000000000000000000021"
EAS_SCHEMA_REGISTRY = "0x4200000000000000000000000000000000000020"
EAS_SCHEMA_UID = "0x70a6cca5fbf857df1196dbbf7b0e460ff38f83788e3338a2c96cbb6feb3d711a"

# ---------------------------------------------------------------------------
# USDC token addresses by chain ID
# ---------------------------------------------------------------------------
USDC_ADDRESSES = {
    8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # Base mainnet
    1: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # Ethereum mainnet
    84532: "0x036CbD53842c5426634e7929541eC2318f3dCF7e",  # Base Sepolia
    11155111: "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238",  # Eth Sepolia
}

# ---------------------------------------------------------------------------
# Platform wallets (public addresses — NOT secrets)
# ---------------------------------------------------------------------------
PLATFORM_WALLET = "0xe33356d0d16c107eac7da1fc7263350cbdb548e5"
RELAY_WALLET = "0x4b5974229f96ac5987d6e31065d73d6fd8e130d9"

# ---------------------------------------------------------------------------
# RPC endpoints (public)
# ---------------------------------------------------------------------------
RPC_URLS = {
    8453: "https://mainnet.base.org",
    1: "https://ethereum-rpc.publicnode.com",
    84532: "https://sepolia.base.org",
    11155111: "https://ethereum-sepolia-rpc.publicnode.com",
}

# ---------------------------------------------------------------------------
# The Graph subgraph URLs (ERC-8004 indexing)
# ---------------------------------------------------------------------------
SUBGRAPH_URLS = {
    1: "https://gateway.thegraph.com/api/7fd2e7d89ce3ef24cd0d4590298f0b2c/subgraphs/id/FV6RR6y13rsnCxBAicKuQEwDp8ioEGiNaWaZUmvr1F8k",
    8453: "https://gateway.thegraph.com/api/536c6d8572876cabea4a4ad0fa49aa57/subgraphs/id/43s9hQRurMGjuYnC1r2ZwS6xSQktbFyXMPMqGKUFJojb",
    11155111: "https://gateway.thegraph.com/api/00a452ad3cd1900273ea62c1bf283f93/subgraphs/id/6wQRC7geo9XYAhckfmfo8kbMRLeWU8KQd3XsJqFKmZLT",
    84532: "https://gateway.thegraph.com/api/536c6d8572876cabea4a4ad0fa49aa57/subgraphs/id/4yYAvQLFjBhBtdRCY7eUWo181VNoTSLLFd5M7FXQAi6u",
}

# ---------------------------------------------------------------------------
# EAS GraphQL endpoints
# ---------------------------------------------------------------------------
EAS_ENDPOINTS = {
    8453: "https://base.easscan.org/graphql",
    84532: "https://base-sepolia.easscan.org/graphql",
}

# ---------------------------------------------------------------------------
# Chain metadata
# ---------------------------------------------------------------------------
CHAIN_NAMES = {
    8453: "Base",
    1: "Ethereum",
    84532: "Base Sepolia",
    11155111: "Sepolia",
}

# Fleet provider filter value (hex-encoded "yakrover")
YAKROVER_HEX = "0x79616b726f766572"
