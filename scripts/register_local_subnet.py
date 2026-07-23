#!/usr/bin/env python3
"""
Register SignOra subnet on local subtensor and enable emissions.

Requires local node at ws://127.0.0.1:9944 (see scripts/local_devnet.sh).

Uses Substrate dev account //Alice by default.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Register SignOra on local subtensor")
    parser.add_argument("--endpoint", default="ws://127.0.0.1:9944")
    parser.add_argument("--wallet-uri", default="//Alice", help="Dev account URI")
    parser.add_argument("--wallet-name", default="signora-local")
    parser.add_argument("--hotkey-name", default="default")
    args = parser.parse_args()

    from bittensor import Subtensor
    from bittensor_wallet import Wallet

    sub = Subtensor(network=args.endpoint)
    block = sub.get_current_block()
    print(f"Connected — block {block}")

    wallet = Wallet(name=args.wallet_name, hotkey=args.hotkey_name)
    try:
        wallet.create_if_nonexistent(coldkey_use_password=False, hotkey_use_password=False)
    except Exception:
        pass

    # Fund from Alice if needed (local dev)
    try:
        from substrateinterface import Keypair

        alice = Keypair.create_from_uri(args.wallet_uri)
        # Transfer is optional on localnet — Alice often has funds
    except Exception:
        alice = None

    print("Registering subnet...")
    resp = sub.register_subnet(
        wallet=wallet,
        mev_protection=False,
        wait_for_inclusion=True,
        wait_for_finalization=True,
    )
    if not resp.success:
        print(f"register_subnet failed: {resp.message}")
        sys.exit(1)

    netuid = sub.get_total_subnets() - 1
    print(f"Registered netuid={netuid}")

    print("Calling start_call...")
    start = sub.start_call(netuid=netuid, wallet=wallet, mev_protection=False)
    if not start.success:
        print(f"start_call failed: {start.message}")
        sys.exit(1)

    print(f"\nSignOra local subnet ready: netuid={netuid}")
    print(f"Endpoint: {args.endpoint}")
    print(f"Wallet: {args.wallet_name}/{args.hotkey_name}")
    print("\nMiner:")
    print(
        f"  python neurons/miner.py --netuid {netuid} "
        f"--subtensor.chain_endpoint {args.endpoint} "
        f"--wallet.name {args.wallet_name} --wallet.hotkey {args.hotkey_name}"
    )
    print("\nValidator:")
    print(
        f"  python neurons/validator.py --netuid {netuid} "
        f"--subtensor.chain_endpoint {args.endpoint} "
        f"--wallet.name {args.wallet_name} --wallet.hotkey {args.hotkey_name}"
    )

    out = ROOT / "data" / "local_netuid.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(str(netuid))
    print(f"\nSaved netuid → {out}")


if __name__ == "__main__":
    main()
