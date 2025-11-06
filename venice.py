#!/usr/bin/env python3
"""
test_venice.py

Simple tester for Venice.ai (OpenAI-compatible) chat/completions endpoint.

Usage:
  export VENICE_API_KEY="wvOH0kYOVHG7Nqgjd3Ft4nagJztR30fsOLgg5W2TaN"
  python3 test_venice.py --model qwen3-235b --prompt "Say hello in one line"

Requirements:
  pip install requests
"""

import os
import sys
import json
import argparse
import requests

DEFAULT_BASE = "https://api.venice.ai/api/v1"
DEFAULT_MODEL = "qwen3-4b"

def main():
    p = argparse.ArgumentParser(description="Test Venice (OpenAI-compatible) chat/completions")
    p.add_argument("--base", default=os.getenv("VENICE_BASE_URL", DEFAULT_BASE),
                   help=f"Venice base URL (default {DEFAULT_BASE})")
    p.add_argument("--key", default=os.getenv("VENICE_API_KEY"),
                   help="Venice API key (or set VENICE_API_KEY environment variable)")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Model id (default {DEFAULT_MODEL})")
    p.add_argument("--prompt", default="Say hello in one line", help="Prompt to send as user message")
    p.add_argument("--max-tokens", type=int, default=500, help="max_tokens (increased default for better responses)")
    p.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout (seconds)")
    p.add_argument("--strip-thinking", action="store_true", help="Strip thinking content from response")
    args = p.parse_args()

    if not args.key:
        print("ERROR: No API key provided. Set VENICE_API_KEY or pass --key.", file=sys.stderr)
        sys.exit(2)

    url = args.base.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {args.key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": args.model,
        "messages": [
            {"role": "user", "content": args.prompt}
        ],
        "max_tokens": args.max_tokens,
        "venice_parameters": {
            "strip_thinking_response": args.strip_thinking,
            "disable_thinking": False,
            "include_venice_system_prompt": True
        }
    }

    print(f"POST {url}")
    # don't print the key
    print(f"Using model: {args.model}; prompt: {args.prompt!r}")

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=args.timeout)
    except requests.RequestException as e:
        print("Network error while calling Venice:", e, file=sys.stderr)
        sys.exit(3)

    print("HTTP", resp.status_code)
    # Try to pretty-print JSON if possible
    ct = resp.headers.get("Content-Type", "")
    body_text = resp.text.strip()
    if "application/json" in ct or (body_text.startswith("{") or body_text.startswith("[")):
        try:
            j = resp.json()
            print(json.dumps(j, indent=2, ensure_ascii=False))
        except Exception:
            print("Response not valid JSON; raw body below:\n")
            print(body_text)
    else:
        print("Non-JSON response:\n")
        print(body_text)

    # Quick diagnostic: if validation error present, try to show details
    if resp.status_code == 400:
        try:
            j = resp.json()
            # Venice often provides helpful validation messages
            if isinstance(j, dict):
                if "errors" in j:
                    print("\nValidation errors:")
                    print(json.dumps(j["errors"], indent=2, ensure_ascii=False))
                elif "message" in j:
                    print("\nMessage:", j.get("message"))
                elif "validation" in j:
                    print("\nValidation detail:")
                    print(json.dumps(j["validation"], indent=2, ensure_ascii=False))
        except Exception:
            pass

if __name__ == "__main__":
    main()
