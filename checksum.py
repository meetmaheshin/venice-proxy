# probe_token_robust.py
from web3 import Web3
from decimal import Decimal

ADDR  = "0x4106DBe31e9cf790D4dD221E627BDe55c8de195E"  # your wallet
TOKEN = "0x164239f9a4aec9c4e437bf6890ea8602b759fd74"  # VERONICA proxy (the Contract address)

RPCS = [
    "https://mainnet.base.org",
    # Fallback public nodes (no key needed):
    "https://base-rpc.publicnode.com",
    "https://rpc.ankr.com/base",
]

def pad32(x: bytes) -> bytes:
    return b"\x00"*(32-len(x)) + x

def hex0x(b: bytes) -> str:
    return "0x" + b.hex()

# Method selectors
# decimals(): 0x313ce567
# balanceOf(address): 0x70a08231
SEL_DECIMALS = bytes.fromhex("313ce567")
SEL_BALANCE  = bytes.fromhex("70a08231")

def raw_decimals(w3, token):
    data = SEL_DECIMALS
    res = w3.eth.call({"to": token, "data": hex0x(data)})
    if len(res) < 66:  # 0x + 64 hex chars == 32 bytes
        raise RuntimeError(f"decimals() returned too little data: {res}")
    return int(res, 16)

def raw_balance_of(w3, token, addr):
    a = bytes.fromhex(addr[2:])
    data = SEL_BALANCE + pad32(a)
    res = w3.eth.call({"to": token, "data": hex0x(data)})
    if len(res) < 66:
        raise RuntimeError(f"balanceOf() returned too little data: {res}")
    return int(res, 16)

for rpc in RPCS:
    print("\n--- Trying RPC:", rpc)
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 20}))
    try:
        print("chainId:", w3.eth.chain_id)
        token = Web3.to_checksum_address(TOKEN)
        addr  = Web3.to_checksum_address(ADDR)

        code = w3.eth.get_code(token)
        print("contract code length:", len(code))

        d = raw_decimals(w3, token)
        bal_raw = raw_balance_of(w3, token, addr)
        bal = Decimal(bal_raw) / (10 ** d)

        print("decimals:", d)
        print("balance:", bal)
        break
    except Exception as e:
        print("RPC failed:", repr(e))
