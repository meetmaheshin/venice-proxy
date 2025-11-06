# send_native_base.py
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv()
w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL","https://mainnet.base.org")))
acct = Account.from_key(os.getenv("PRIVATE_KEY"))
to = "0x0cA07c2A3eCb48F8dcbC4D6afC75687db56e99d0"   # change this
value = w3.to_wei("0.0002", "ether")

latest = w3.eth.get_block("latest")
tip = w3.to_wei(1, "gwei")
tx = {
  "to": Web3.to_checksum_address(to),
  "value": value,
  "nonce": w3.eth.get_transaction_count(acct.address),
  "chainId": 8453,
  "type": 2,
  "maxPriorityFeePerGas": tip,
  "maxFeePerGas": latest.get("baseFeePerGas", w3.eth.gas_price) + 2*tip,
  "gas": 21000,
}
signed = acct.sign_transaction(tx)
raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction")
h = w3.eth.send_raw_transaction(raw)
print("tx:", h.hex())
