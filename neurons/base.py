"""Shared neuron utilities."""

from __future__ import annotations

import argparse
from typing import Optional

import bittensor as bt

from signora.core.config import SignoraConfig


def add_signora_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--netuid", type=int, default=0, help="Subnet netuid")
    parser.add_argument(
        "--signora.phase",
        type=str,
        default="launch",
        choices=["launch", "phase_1b", "steady"],
        help="Emission phase",
    )
    parser.add_argument(
        "--signora.model_dir",
        type=str,
        default="./models",
        help="Directory for translation / lookup models",
    )
    return parser


def base_config(role: str) -> bt.Config:
    parser = argparse.ArgumentParser(description=f"SignOra {role}")
    parser = add_signora_args(parser)
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)
    bt.axon.add_args(parser)
    return bt.config(parser)


def load_metagraph(config: bt.Config) -> tuple[bt.Subtensor, bt.Metagraph]:
    subtensor = bt.subtensor(config=config)
    metagraph = subtensor.metagraph(config.netuid)
    bt.logging.info(f"Loaded metagraph netuid={config.netuid} n={metagraph.n}")
    return subtensor, metagraph


def get_current_block_hash(subtensor: bt.Subtensor) -> str:
    block = subtensor.get_current_block()
    block_hash = subtensor.substrate.get_block_hash(block)
    if isinstance(block_hash, str):
        return block_hash
    return str(block_hash)
