import os, sys, time
from decimal import Decimal
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

# ====== EDIT THESE ======
TOKEN_ADDR = "0x164239FA94aec9c4e437Bf6890ea8602b759fd74"  # VERONICA proxy on Base
RECIPIENT  = "0xB2dc590CB9Fca055A33Fcc02822f93Ad1725B3cA"
AMOUNT_TOKENS = "18"          # ignored if FULL_BALANCE=True
FULL_BALANCE  = False
AUTO_SPLIT_OVER_50K = False
MAX_PER_TX = Decimal("50000")
# If your RPC won't return balance/decimals, set this:
ASSUME_DECIMALS_IF_FAIL = 18
SKIP_BALANCE_CHECK_IF_FAIL = True
# ========================

ERC20_ABI = [
    {"name":"decimals","outputs":[{"type":"uint8"}],"inputs":[],"stateMutability":"view","type":"function"},
    {"name":"balanceOf","outputs":[{"type":"uint256"}],"inputs":[{"name":"a","type":"address"}],"stateMutability":"view","type":"function"},
    {"name":"transfer","outputs":[{"type":"bool"}],"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
]

def fees(w3: Web3):
    latest = w3.eth.get_block("latest")
    base = latest.get("baseFeePerGas", w3.eth.gas_price)
    tip  = w3.to_wei(1, "gwei")
    return {"maxFeePerGas": base + 2*tip, "maxPriorityFeePerGas": tip, "type": 2}

def safe_decimals(token):
    try:
        return token.functions.decimals().call()
    except Exception:
        print(f"[warn] decimals() failed; assuming {ASSUME_DECIMALS_IF_FAIL}")
        return ASSUME_DECIMALS_IF_FAIL

def safe_balance(token, addr):
    try:
        return token.functions.balanceOf(addr).call()
    except Exception:
        if SKIP_BALANCE_CHECK_IF_FAIL:
            print("[warn] balanceOf() failed; SKIPPING balance check.")
            return None
        raise

def ensure_contract(w3, addr):
    code = w3.eth.get_code(addr)
    if not code or len(code) == 0:
        print("[warn] get_code returned empty; continuing (some public RPCs are flaky).")

def send_chunk(w3, acct, token, to, human_amount, decimals, nonce):
    if Decimal(human_amount) > MAX_PER_TX:
        raise SystemExit(f"Refusing > {MAX_PER_TX} in one tx (requested {human_amount}).")
    value = int(Decimal(human_amount) * (10 ** decimals))
    fee = fees(w3)
    tx = token.functions.transfer(to, value).build_transaction({
        "chainId": int(os.getenv("CHAIN_ID", "8453")),
        "from": acct.address,
        "nonce": nonce,
        "maxFeePerGas": fee["maxFeePerGas"],
        "maxPriorityFeePerGas": fee["maxPriorityFeePerGas"],
    })
    try:
        tx["gas"] = w3.eth.estimate_gas(tx)
    except Exception:
        tx["gas"] = 120_000
    tx["type"] = 2
    signed = acct.sign_transaction(tx)
    # works on both v5 and v6
    raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction")
    txh = w3.eth.send_raw_transaction(raw)

    print(f"→ Sent {human_amount} tokens | tx: {txh.hex()}")
    rec = w3.eth.wait_for_transaction_receipt(txh)
    print("   Confirmed in block:", rec.blockNumber)

def main():
    # optional CLI override: python script.py 0xTO 12345.67
    to_arg  = sys.argv[1] if len(sys.argv) > 1 else RECIPIENT
    amt_arg = sys.argv[2] if len(sys.argv) > 2 else AMOUNT_TOKENS

    load_dotenv()
    RPC_URL = os.getenv("RPC_URL", "https://base-mainnet.g.alchemy.com/v2/YOUR_KEY")  # use a reliable RPC
    CHAIN_ID = int(os.getenv("CHAIN_ID", "8453"))
    PK = os.getenv("PRIVATE_KEY") or sys.exit("Missing PRIVATE_KEY in .env")

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    acct = Account.from_key(PK)
    token_addr = Web3.to_checksum_address(TOKEN_ADDR)
    to = Web3.to_checksum_address(to_arg)

    print("Using RPC:", RPC_URL)
    print("From:", acct.address)
    print("To:  ", to)

    ensure_contract(w3, token_addr)
    token = w3.eth.contract(token_addr, abi=ERC20_ABI)

    decimals = safe_decimals(token)
    bal_raw  = safe_balance(token, acct.address)
    if bal_raw is not None:
        bal = Decimal(bal_raw) / (10 ** decimals)
        print("Token balance:", bal)
    else:
        bal = None

    desired_total = bal if FULL_BALANCE and bal is not None else Decimal(amt_arg)
    if FULL_BALANCE and bal is None:
        sys.exit("FULL_BALANCE requested but balance check failed—disable FULL_BALANCE or provide amount.")
    if bal is not None and bal < desired_total:
        sys.exit(f"Insufficient token balance: have {bal}, want {desired_total}.")

    # Build chunks
    chunks, remaining = [], desired_total
    while remaining > 0:
        send_amt = min(MAX_PER_TX, remaining) if AUTO_SPLIT_OVER_50K else desired_total
        chunks.append(send_amt)
        remaining -= send_amt
        if not AUTO_SPLIT_OVER_50K: break

    nonce = w3.eth.get_transaction_count(acct.address)
    for amt in chunks:
        send_chunk(w3, acct, token, to, amt, decimals, nonce)
        nonce += 1
        time.sleep(0.2)
    print("All done.")

if __name__ == "__main__":
    main()
