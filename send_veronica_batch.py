import os, sys, csv, time, math
from decimal import Decimal
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

# ====== SETTINGS ======
INPUT_CSV  = sys.argv[1] if len(sys.argv) > 1 else "payouts.csv"
OUTPUT_CSV = sys.argv[2] if len(sys.argv) > 2 else "payouts_out.csv"

TOKEN_ADDR = "0x164239FA94aec9c4e437Bf6890ea8602b759fd74"   # VERONICA proxy on Base
MAX_PER_TX = Decimal("150000")
AUTO_SPLIT_OVER_50K = False          # True => split large amounts into <=50k chunks
ASSUME_DECIMALS_IF_FAIL = 18         # fallback if decimals() fails
WAIT_FOR_RECEIPT = True              # False => just broadcast; faster, but no fee/block
SLEEP_BETWEEN = 0.2                  # seconds between txs to keep mempool happy
# ======================

ERC20_ABI = [
    {"name":"decimals","outputs":[{"type":"uint8"}],"inputs":[],"stateMutability":"view","type":"function"},
    {"name":"balanceOf","outputs":[{"type":"uint256"}],"inputs":[{"name":"a","type":"address"}],"stateMutability":"view","type":"function"},
    {"name":"transfer","outputs":[{"type":"bool"}],"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
]

def fees(w3: Web3):
    latest = w3.eth.get_block("latest")
    base = latest.get("baseFeePerGas", w3.eth.gas_price)
    tip  = w3.to_wei(1, "gwei")
    return {"maxFeePerGas": base + 2*tip, "maxPriorityFeePerGas": tip}

def load_env_and_web3():
    load_dotenv()
    rpc = os.getenv("RPC_URL", "https://base-mainnet.g.alchemy.com/v2/YOUR_KEY")
    pk  = os.getenv("PRIVATE_KEY")
    if not pk:
        raise SystemExit("Missing PRIVATE_KEY in .env")
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    acct = Account.from_key(pk)
    return w3, acct, rpc

def get_decimals(token):
    try:
        return token.functions.decimals().call()
    except Exception:
        print(f"[warn] decimals() failed; assuming {ASSUME_DECIMALS_IF_FAIL}")
        return ASSUME_DECIMALS_IF_FAIL

def send_one(w3, acct, token, to, human_amount: Decimal, decimals: int, nonce: int):
    if human_amount > MAX_PER_TX:
        raise SystemExit(f"Refusing > {MAX_PER_TX} in one tx (requested {human_amount}).")

    value = int(human_amount * (10 ** decimals))
    fee_fields = fees(w3)

    tx = token.functions.transfer(to, value).build_transaction({
        "chainId": int(os.getenv("CHAIN_ID", "8453")),
        "from": acct.address,
        "nonce": nonce,
        "maxFeePerGas": fee_fields["maxFeePerGas"],
        "maxPriorityFeePerGas": fee_fields["maxPriorityFeePerGas"],
        "type": 2,
    })
    try:
        tx["gas"] = w3.eth.estimate_gas(tx)
    except Exception:
        tx["gas"] = 120_000  # safe fallback

    signed = acct.sign_transaction(tx)
    raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction")
    txh = w3.eth.send_raw_transaction(raw)

    if not WAIT_FOR_RECEIPT:
        return txh.hex(), "", "", "", "sent"

    rcpt = w3.eth.wait_for_transaction_receipt(txh)
    egp = rcpt.get("effectiveGasPrice") or getattr(rcpt, "effectiveGasPrice", None) or w3.eth.gas_price
    fee_eth = str(Decimal(rcpt.gasUsed) * Decimal(egp) / Decimal(10**18))
    return txh.hex(), rcpt.blockNumber, rcpt.gasUsed, fee_eth, ("confirmed" if rcpt.status == 1 else "reverted")

def main():
    w3, acct, rpc = load_env_and_web3()
    token = w3.eth.contract(Web3.to_checksum_address(TOKEN_ADDR), abi=ERC20_ABI)
    decimals = get_decimals(token)

    print("Using RPC:", rpc)
    print("From:", acct.address)

    # Read input CSV
    if not os.path.exists(INPUT_CSV):
        raise SystemExit(f"Input CSV not found: {INPUT_CSV}")

    with open(INPUT_CSV, "r", newline="", encoding="utf-8-sig") as f_in, \
         open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_out:

        reader = csv.DictReader(f_in)
        fieldnames = list(reader.fieldnames or [])
        # Ensure expected columns
        if "to" not in fieldnames or "amount" not in fieldnames:
            raise SystemExit('CSV must have headers: to,amount')
        # Add output columns
        for col in ["tx_hashes", "status", "block", "gas_used", "fee_eth", "error"]:
            if col not in fieldnames:
                fieldnames.append(col)

        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        nonce = w3.eth.get_transaction_count(acct.address)

        for row in reader:
            out = dict(row)  # copy input columns forward

            to_raw = (row.get("to") or "").strip()
            amt_raw = (row.get("amount") or "").strip()
            if not to_raw or not amt_raw:
                out.update({"status":"skip","error":"missing to/amount"})
                writer.writerow(out); continue

            # Skip if already has tx_hashes/status=confirmed
            if (row.get("status","").lower() in {"confirmed","sent"}) and row.get("tx_hashes"):
                writer.writerow(out); continue

            # Normalize inputs
            try:
                to = Web3.to_checksum_address(to_raw)
            except Exception:
                out.update({"status":"error","error":f"invalid address: {to_raw}"})
                writer.writerow(out); continue

            try:
                human_amt = Decimal(amt_raw)
                if human_amt <= 0:
                    raise ValueError
            except Exception:
                out.update({"status":"error","error":f"invalid amount: {amt_raw}"})
                writer.writerow(out); continue

            # Chunking
            chunks = []
            if AUTO_SPLIT_OVER_50K and human_amt > MAX_PER_TX:
                n = math.ceil(human_amt / MAX_PER_TX)
                for i in range(n):
                    chunks.append(min(MAX_PER_TX, human_amt - i*MAX_PER_TX))
            else:
                if human_amt > MAX_PER_TX:
                    out.update({"status":"error","error":f"amount>{MAX_PER_TX} and autosplit disabled"})
                    writer.writerow(out); continue
                chunks = [human_amt]

            tx_hashes = []
            last_block = last_gas = last_fee = ""
            try:
                for c in chunks:
                    txh, block, gas, fee, status = send_one(w3, acct, token, to, c, decimals, nonce)
                    nonce += 1
                    tx_hashes.append(txh)
                    last_block, last_gas, last_fee = block, gas, fee
                    print(f"→ {to} | {c} | {txh}")
                    time.sleep(SLEEP_BETWEEN)

                out.update({
                    "tx_hashes": ";".join(tx_hashes),
                    "status": status,
                    "block": last_block,
                    "gas_used": last_gas,
                    "fee_eth": last_fee,
                    "error": ""
                })
            except Exception as e:
                out.update({"status":"error","error":repr(e)})

            writer.writerow(out)

    print(f"Done. Wrote results to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
