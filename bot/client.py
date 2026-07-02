"""
client.py
---------

Thin wrapper around python-binance's Client, configured for the Binance
Futures Testnet (USDT-M).

Responsibilities:
    - Load API credentials from environment (.env via python-dotenv).
    - Construct a python-binance Client pointed at the Futures Testnet.
    - Expose a single `place_order()` method that bot.orders calls, which
      translates our internal normalized order dict into the correct
      `futures_create_order` call for MARKET / LIMIT / STOP.
    - Catch every Binance-specific and network-related exception and
      re-raise as a single RuntimeError with a clear message, so callers
      (the CLI, orders.py) never need to know about python-binance's
      exception hierarchy.

Nothing in this module does input validation -- that is validators.py's job.
By the time place_order() is called, the order dict is assumed to already
be validated.
"""

import logging
import os

from binance.client import Client
from binance.exceptions import (
    BinanceAPIException,
    BinanceOrderException,
    BinanceRequestException,
)
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

# Official Binance Futures Testnet base URL (USDT-M).
FUTURES_TESTNET_URL = "https://testnet.binancefuture.com"


class BinanceFuturesTestnetClient:
    """
    Wraps a python-binance Client instance configured for the Futures
    Testnet, and exposes a single, simple place_order() method.
    """

    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        Create the underlying python-binance Client.

        Args:
            api_key: Binance Testnet API key. Falls back to the
                BINANCE_API_KEY environment variable if not provided.
            api_secret: Binance Testnet API secret. Falls back to the
                BINANCE_API_SECRET environment variable if not provided.

        Raises:
            RuntimeError: if no API key/secret can be found anywhere.
        """
        api_key = api_key or os.environ.get("BINANCE_API_KEY")
        api_secret = api_secret or os.environ.get("BINANCE_API_SECRET")

        if not api_key or not api_secret:
            raise RuntimeError(
                "Missing Binance API credentials. Set BINANCE_API_KEY and "
                "BINANCE_API_SECRET in your .env file (see .env.example)."
            )

        logger.debug("Initializing Binance client (testnet=True).")

        # python-binance's `testnet=True` flag points spot endpoints at the
        # spot testnet. For USDT-M Futures we additionally set FUTURES_URL
        # explicitly to guarantee requests go to the futures testnet host,
        # regardless of python-binance version defaults.
        self._client = Client(api_key, api_secret, testnet=True)
        self._client.FUTURES_URL = FUTURES_TESTNET_URL + "/fapi"

        logger.debug("Binance client initialized. FUTURES_URL=%s", self._client.FUTURES_URL)

    def place_order(self, order: dict) -> dict:
        """
        Submit a validated order dict to Binance Futures Testnet.

        Args:
            order: A normalized order dict as produced by
                validators.validate_order_request(), i.e.:
                {
                    "symbol": "BTCUSDT",
                    "side": "BUY" | "SELL",
                    "type": "MARKET" | "LIMIT" | "STOP",
                    "quantity": float,
                    "price": float | None,
                    "stop_price": float | None,
                }

        Returns:
            The raw order response dict from Binance
            (contains orderId, status, executedQty, avgPrice, etc.).

        Raises:
            RuntimeError: wraps any BinanceAPIException, BinanceOrderException,
                BinanceRequestException, or network-level error with a clear
                message. This is the ONLY exception type callers need to catch.
        """
        params = self._build_request_params(order)

        logger.debug("Submitting futures_create_order with params: %s", params)

        try:
            response = self._client.futures_create_order(**params)
        except (BinanceAPIException, BinanceOrderException, BinanceRequestException) as exc:
            logger.error("Binance rejected the order request.", exc_info=True)
            raise RuntimeError(f"Binance API error while placing order: {exc}") from exc
        except RequestException as exc:
            logger.error("Network error while contacting Binance Futures Testnet.", exc_info=True)
            raise RuntimeError(f"Network error while placing order: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - final safety net, re-raised as RuntimeError
            logger.error("Unexpected error while placing order.", exc_info=True)
            raise RuntimeError(f"Unexpected error while placing order: {exc}") from exc

        logger.debug("Received order response: %s", response)
        return response

    @staticmethod
    def _build_request_params(order: dict) -> dict:
        """
        Translate our normalized internal order dict into the keyword
        arguments expected by python-binance's futures_create_order().

        MARKET -> symbol, side, type, quantity
        LIMIT  -> symbol, side, type, quantity, price, timeInForce=GTC
        STOP   -> symbol, side, type=STOP, quantity, price, stopPrice,
                  timeInForce=GTC   (stop-limit: triggers a limit order at
                  `price` once the mark price crosses `stop_price`)
        """
        params = {
            "symbol": order["symbol"],
            "side": order["side"],
            "type": order["type"],
            "quantity": order["quantity"],
        }

        if order["type"] == "LIMIT":
            params["price"] = order["price"]
            params["timeInForce"] = "GTC"

        elif order["type"] == "STOP":
            # Binance Futures STOP = stop-limit order: needs both a trigger
            # (stopPrice) and the limit price to execute at once triggered.
            params["price"] = order["price"]
            params["stopPrice"] = order["stop_price"]
            params["timeInForce"] = "GTC"

        # MARKET orders need nothing further.
        return params
