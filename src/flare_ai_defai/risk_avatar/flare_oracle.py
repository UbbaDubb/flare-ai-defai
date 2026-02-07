from web3 import Web3

FLARE_RPC = "https://coston2-api.flare.network/ext/C/rpc"

FTSO_REGISTRY_ADDRESS = Web3.to_checksum_address(
    "0x1000000000000000000000000000000000000003"
)
# 👆 Official FTSO Registry on Coston2

FTSO_REGISTRY_ABI = [
    {
        "inputs": [{"internalType": "string", "name": "_symbol", "type": "string"}],
        "name": "getCurrentPriceWithDecimals",
        "outputs": [
            {"internalType": "uint256", "name": "_price", "type": "uint256"},
            {"internalType": "uint256", "name": "_timestamp", "type": "uint256"},
            {"internalType": "uint256", "name": "_decimals", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    }
]

def get_btc_price() -> tuple[float, int]:
    w3 = Web3(Web3.HTTPProvider(FLARE_RPC))
    registry = w3.eth.contract(
        address=FTSO_REGISTRY_ADDRESS,
        abi=FTSO_REGISTRY_ABI,
    )

    price, timestamp, decimals = registry.functions.getCurrentPriceWithDecimals(
        "BTC/USD"
    ).call()

    return price / (10 ** decimals), timestamp

