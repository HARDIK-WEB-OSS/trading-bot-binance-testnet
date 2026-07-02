"""
validators.py
--------------

Pure, side-effect-free input validation for order parameters.

Every function here either returns a normalized value or raises a ValueError
with a clear, user-facing message. Nothing in this module talks to the
network or the Binance API -- that keeps validation fast, testable, and
guaranteed to run BEFORE any API call is made.
"""

import re

VALID_SIDES = {"BUY", "SELL"}
VALID_TYPES = {"MARKET", "LIMIT", "STOP"}

# Basic USDT-M perpetual futures symbol shape, e.g. BTCUSDT, ETHUSDT, 1000SHIBUSDT.
# Binance symbols are uppercase alphanumerics ending in the quote asset (USDT).
# The base asset portion is allowed to be 2-17 characters (covers short bases
# like "BTC" up through longer ones like "1000SHIB").
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,17}USDT$")


def validate_symbol(symbol: str) -> str:
    """
    Validate and normalize a trading symbol.

    Rules:
        - Must be a non-empty string.
        - Normalized to uppercase.
        - Must match the USDT-M futures symbol shape (e.g. BTCUSDT).

    Returns the normalized (uppercase) symbol.
    Raises ValueError if invalid.
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol is required and must be a string (e.g. 'BTCUSDT').")

    normalized = symbol.strip().upper()

    if not _SYMBOL_RE.match(normalized):
        raise ValueError(
            f"Invalid symbol '{symbol}'. Expected a USDT-M futures symbol like "
            f"'BTCUSDT' or 'ETHUSDT' (uppercase letters/digits ending in USDT)."
        )
    return normalized


def validate_side(side: str) -> str:
    """
    Validate and normalize an order side.

    Must be 'BUY' or 'SELL' (case-insensitive on input).
    Returns the normalized uppercase side.
    Raises ValueError if invalid.
    """
    if not side or not isinstance(side, str):
        raise ValueError("Side is required and must be a string ('BUY' or 'SELL').")

    normalized = side.strip().upper()
    if normalized not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of {sorted(VALID_SIDES)}."
        )
    return normalized


def validate_order_type(order_type: str) -> str:
    """
    Validate and normalize an order type.

    Must be one of 'MARKET', 'LIMIT', 'STOP' (case-insensitive on input).
    Returns the normalized uppercase order type.
    Raises ValueError if invalid.
    """
    if not order_type or not isinstance(order_type, str):
        raise ValueError(
            f"Order type is required and must be a string. "
            f"Must be one of {sorted(VALID_TYPES)}."
        )

    normalized = order_type.strip().upper()
    if normalized not in VALID_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. Must be one of {sorted(VALID_TYPES)}."
        )
    return normalized


def validate_quantity(quantity) -> float:
    """
    Validate order quantity.

    Rules:
        - Must be convertible to float.
        - Must be strictly positive (> 0).

    Returns the quantity as a float.
    Raises ValueError if invalid.
    """
    if quantity is None:
        raise ValueError("Quantity is required.")

    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValueError(f"Quantity must be a number, got '{quantity}'.")

    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got {qty}.")

    return qty


def validate_price(price, required: bool, field_name: str = "price"):
    """
    Validate an optional/required price-like field (price or stop_price).

    Args:
        price: The raw value to validate (may be None).
        required: If True, a missing price raises ValueError.
        field_name: Used in error messages ('price' or 'stop_price').

    Returns:
        float(price) if provided, else None (only possible when required=False).
    Raises ValueError if invalid.
    """
    if price is None:
        if required:
            raise ValueError(f"{field_name} is required for this order type.")
        return None

    try:
        value = float(price)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a number, got '{price}'.")

    if value <= 0:
        raise ValueError(f"{field_name} must be positive, got {value}.")

    return value


def validate_order_request(symbol, side, order_type, quantity, price=None, stop_price=None):
    """
    Validate a full order request in one call. This is the main entry point
    used by bot.orders before any API call is made.

    Type-specific rules:
        - MARKET: price and stop_price are not required (ignored if given).
        - LIMIT:  price is required. stop_price is not used.
        - STOP:   both price and stop_price are required (stop-limit order).

    Returns a dict of normalized values:
        {
            "symbol": str,
            "side": str,
            "type": str,
            "quantity": float,
            "price": float | None,
            "stop_price": float | None,
        }
    Raises ValueError on any invalid field, with a message identifying the
    problem clearly enough for a CLI user to fix their input.
    """
    normalized_symbol = validate_symbol(symbol)
    normalized_side = validate_side(side)
    normalized_type = validate_order_type(order_type)
    normalized_quantity = validate_quantity(quantity)

    if normalized_type == "MARKET":
        normalized_price = None
        normalized_stop_price = None

    elif normalized_type == "LIMIT":
        normalized_price = validate_price(price, required=True, field_name="price")
        normalized_stop_price = None

    elif normalized_type == "STOP":
        normalized_price = validate_price(price, required=True, field_name="price")
        normalized_stop_price = validate_price(
            stop_price, required=True, field_name="stop_price"
        )

    else:  # pragma: no cover - unreachable, validate_order_type already guards this
        raise ValueError(f"Unhandled order type '{normalized_type}'.")

    return {
        "symbol": normalized_symbol,
        "side": normalized_side,
        "type": normalized_type,
        "quantity": normalized_quantity,
        "price": normalized_price,
        "stop_price": normalized_stop_price,
    }
