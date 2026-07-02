#!/usr/bin/env python3
"""Run SignOra known-plaintext challenge server."""

from __future__ import annotations

import argparse
import os

import uvicorn

from signora.challenge.server import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="SignOra challenge server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--data-dir", default="./data/challenges")
    args = parser.parse_args()

    secret = os.getenv("SIGNORA_CHALLENGE_SECRET")
    app = create_app(data_dir=args.data_dir, master_secret=secret)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
