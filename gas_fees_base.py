# gas_fees_base.py
import os, sys, csv, time
from decimal import Decimal, getcontext
from dotenv import load_dotenv
from web3 import Web3

getcontext().prec = 50  # high precision for ETH math

# ----- Config -----
DEFAULT_RPC = "https://mainnet.base.org"  # Consider Alchemy/Infura for reliability
INPUT_FILE  = "hashes.txt"                # optional: one tx hash per line
OUTPUT_FILE = "gas_fees.csv"
MAX_RETRIES = 3
SLEEP_BETWEEN = 0.5
# -------------------

def load_hashes():
    # Priority: CLI args after script name; else hashes.txt
    if len(sys.argv) > 1:
        return [h.strip() for h in sys.argv[1:] if h.strip()]
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    raise SystemExit(f"No hashes provided. Pass them as args or put them in {INPUT_FILE}")

def wei_to_eth(wei: int) -> Decimal:
    return Decimal(wei) / Decimal(10**18)

def wei_to_gwei(wei: int) -> Decimal:
    return Decimal(wei) / Decimal(10**9)

def get_receipt_with_retry(w3, h):
    last_err = None
    for _ in range(MAX_RETRIES):
        try:
            rcpt = w3.eth.get_transaction_receipt(h)
            return rcpt
        except Exception as e:
            last_err = e
            time.sleep(SLEEP_BETWEEN)
    raise last_err

def get_tx_with_retry(w3, h):
    last_err = None
    for _ in range(MAX_RETRIES):
        try:
            tx = w3.eth.get_transaction(h)
            return tx
        except Exception as e:
            last_err = e
            time.sleep(SLEEP_BETWEEN)
    raise last_err

def main():
    load_dotenv()
    rpc = os.getenv("RPC_URL", DEFAULT_RPC)
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 25}))
    try:
        chain_id = w3.eth.chain_id
    except Exception:
        chain_id = "?"
    print(f"Using RPC: {rpc} (chainId: {chain_id})")

    hashes = load_hashes()
    rows = []
    total_fee_eth = Decimal(0)

    for h in hashes:
        if not h.startswith("0x") or len(h) != 66:
            print(f"[skip] Not a valid tx hash: {h}")
            continue
        try:
            rcpt = get_receipt_with_retry(w3, h)
            tx   = get_tx_with_retry(w3, h)
        except Exception as e:
            print(f"[err] Failed to fetch {h}: {e}")
            continue

        status = rcpt.status  # 1=success, 0=revert
        gas_used = rcpt.gasUsed
        # effectiveGasPrice for EIP-1559 networks; fallback to tx.gasPrice if missing
        eff_price = getattr(rcpt, "effectiveGasPrice", None)
        if eff_price is None:
            eff_price = rcpt.get("effectiveGasPrice")  # dict-style if needed
        if eff_price is None:
            # legacy fallback
            eff_price = tx.get("gasPrice") or w3.eth.gas_price

        fee_wei = int(gas_used) * int(eff_price)
        fee_eth = wei_to_eth(fee_wei)
        total_fee_eth += fee_eth

        method_id = tx["input"][:10] if tx.get("input") else ""
        to_addr = tx.get("to")
        frm = tx.get("from")
        block = rcpt.blockNumber

        row = {
            "tx_hash": h,
            "block": block,
            "status": status,
            "from": frm,
            "to": to_addr,
            "method_id": method_id,
            "gas_used": gas_used,
            "effective_gas_price_wei": eff_price,
            "effective_gas_price_gwei": str(wei_to_gwei(eff_price)),
            "fee_eth": str(fee_eth),
        }
        rows.append(row)
        print(f"{h[:10]}… | block {block} | status {status} | gas {gas_used} | fee {fee_eth} ETH")

    # Write CSV
    if rows:
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nSaved: {OUTPUT_FILE}")
        print(f"Total gas paid across {len(rows)} txs: {total_fee_eth} ETH")
    else:
        print("No rows to write.")

if __name__ == "__main__":
    main()
