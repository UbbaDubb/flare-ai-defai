from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Tuple

from web3 import Web3
from flare_ai_defai.settings import settings

FLARE_CONTRACT_REGISTRY: Final[str] = "0xaD67FE66660Fb8dFE9d6b1b4240d8650e30F6019"
BTC_USD_FEED_ID_HEX: Final[str] = "0x014254432f55534400000000000000000000000000"  # BTC/USD bytes21

# Real FlareContractRegistry methods (these are what you can call off-chain)
FLARE_CONTRACT_REGISTRY_ABI = [
    {
        "name": "getContractAddressByName",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "_name", "type": "string"}],
        "outputs": [{"name": "", "type": "address"}],
    },
    {
        "name": "getAllContracts",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [
            {"name": "_names", "type": "string[]"},
            {"name": "_addresses", "type": "address[]"},
        ],
    },
]

# TestFtsoV2Interface (per docs, getFeedById returns value+decimals+timestamp)
TEST_FTSO_V2_ABI = [
    {
        "name": "getFeedById",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "_feedId", "type": "bytes21"}],
        "outputs": [
            {"name": "_value", "type": "uint256"},
            {"name": "_decimals", "type": "int8"},
            {"name": "_timestamp", "type": "uint64"},
        ],
    }
]

@dataclass(frozen=True)
class FlarePrice:
    price: float
    decimals: int
    timestamp: int  # unix seconds


def _resolve_ftso_v2_address(registry) -> str:
    """
    Prefer TestFtsoV2 on Coston2 (dev), fallback to FtsoV2 if not present.
    Uses getAllContracts so you don't have to guess the exact name string.
    """
    names, addrs = registry.functions.getAllContracts().call()
    name_to_addr = {n: a for n, a in zip(names, addrs)}

    # Common names seen in Flare periphery tooling/docs
    for candidate in ("TestFtsoV2", "FtsoV2", "FtsoV2Interface", "TestFtsoV2Interface"):
        if candidate in name_to_addr and int(name_to_addr[candidate], 16) != 0:
            return name_to_addr[candidate]

    # As a last resort, try partial match
    for n, a in name_to_addr.items():
        if "FtsoV2" in n and int(a, 16) != 0:
            return a

    raise RuntimeError("Could not find an FtsoV2/TestFtsoV2 address in FlareContractRegistry.getAllContracts().")


def get_btc_usd_price() -> FlarePrice:
    w3 = Web3(Web3.HTTPProvider(settings.web3_provider_url))
    if not w3.is_connected():
        raise RuntimeError(f"Web3 not connected to RPC: {settings.web3_provider_url}")

    registry = w3.eth.contract(
        address=Web3.to_checksum_address(FLARE_CONTRACT_REGISTRY),
        abi=FLARE_CONTRACT_REGISTRY_ABI,
    )

    ftso_v2_addr = _resolve_ftso_v2_address(registry)

    ftso = w3.eth.contract(
        address=Web3.to_checksum_address(ftso_v2_addr),
        abi=TEST_FTSO_V2_ABI,
    )

    feed_id = bytes.fromhex(BTC_USD_FEED_ID_HEX[2:])  # bytes21
    value, decimals, ts = ftso.functions.getFeedById(feed_id).call()

    d = int(decimals)
    px = float(value) / (10 ** d)
    return FlarePrice(price=px, decimals=d, timestamp=int(ts))
