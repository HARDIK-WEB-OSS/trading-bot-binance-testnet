#!/usr/bin/env python3
"""
cli.py
------

Command-line entry point for the Binance Futures Testnet (USDT-M) trading
bot.

Usage examples:

    # MARKET order
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

    # LIMIT order
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT \\
        --quantity 0.01 --price 65000

    # STOP (stop-limit) order
    python cli.py --symbol ETHUSDT --side BUY --type STOP \\
        --quantity 0.1 --price 3500 --stop-price 3490

Exit codes:
    0  -> order placed successfully
    1  -> validation error (bad input, no API call made)
    2  -> Binance API / network error (order was attempted, but failed)
"""

import argparse
import logging
import sys

from dotenv import load_dotenv

from bot.logging_config import setup_logging
from bot.orders import submit_order


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Place MARKET, LIMIT, or STOP orders on Binance Futures Testnet (USDT-M).",
    )
    parser.add_argument(
        "--symbol", required=True,
        help="Trading symbol, e.g. BTCUSDT, ETHUSDT.",
    )
    parser.add_argument(
        "--side", required=True, choices=["BUY", "SELL", "buy", "sell"],
        help="Order side.",
    )
    parser.add_argument(
        "--type", required=True, dest="order_type",
        choices=["MARKET", "LIMIT", "STOP", "market", "limit", "stop"],
        help="Order type.",
    )
    parser.add_argument(
        "--quantity", required=True, type=float,
        help="Order quantity (must be positive).",
    )
    parser.add_argument(
        "--price", required=False, type=float, default=None,
        help="Limit price. Required for LIMIT and STOP orders.",
    )
    parser.add_argument(
        "--stop-price", required=False, type=float, default=None, dest="stop_price",
        help="Stop trigger price. Required for STOP orders.",
    )
    return parser


def main(argv=None) -> int:
    # Load .env as early as possible so BINANCE_API_KEY / BINANCE_API_SECRET
    # are available before the client is constructed.
    load_dotenv()

    setup_logging()
    logger = logging.getLogger(__name__)

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logger.debug("Parsed CLI args: %s", vars(args))

    try:
        submit_order(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        # Validation failure: no API call was made.
        print(f"\nInvalid input: {exc}", file=sys.stderr)
        logger.debug("Validation error, exiting with code 1.", exc_info=True)
        return 1
    except RuntimeError as exc:
        # API / network failure: submit_order already printed/logged details.
        logger.debug("Runtime error, exiting with code 2.", exc_info=True)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
