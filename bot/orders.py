"""
orders.py
---------

High-level order orchestration: validate -> summarize request -> place ->
summarize response.

This is the module the CLI talks to. It ties together validators.py (input
checking) and client.py (the actual API call), and is responsible for the
human-readable summaries printed before/after submission, plus DEBUG/INFO
logging of the whole lifecycle.
"""

import logging

from bot.client import BinanceFuturesTestnetClient
from bot.validators import validate_order_request

logger = logging.getLogger(__name__)


def build_request_summary(order: dict) -> str:
    """
    Build a human-readable, multi-line summary of an order request,
    printed to the console before submission so the user can double check
    what is about to be sent.
    """
    lines = [
        "Order Request Summary",
        "----------------------",
        f"  Symbol:      {order['symbol']}",
        f"  Side:        {order['side']}",
        f"  Type:        {order['type']}",
        f"  Quantity:    {order['quantity']}",
    ]
    if order.get("price") is not None:
        lines.append(f"  Price:       {order['price']}")
    if order.get("stop_price") is not None:
        lines.append(f"  Stop Price:  {order['stop_price']}")
    return "\n".join(lines)


def build_response_summary(response: dict) -> str:
    """
    Build a human-readable, multi-line summary of an order response,
    printed to the console after submission.

    Pulls out the fields the assignment specifically calls out: orderId,
    status, executedQty, avgPrice. Falls back gracefully if any field is
    missing from the response (defensive against API/testnet variability).
    """
    order_id = response.get("orderId", "N/A")
    status = response.get("status", "N/A")
    executed_qty = response.get("executedQty", "N/A")
    avg_price = response.get("avgPrice", "N/A")

    lines = [
        "Order Response Summary",
        "-----------------------",
        f"  Order ID:      {order_id}",
        f"  Status:        {status}",
        f"  Executed Qty:  {executed_qty}",
        f"  Avg Price:     {avg_price}",
    ]
    return "\n".join(lines)


def submit_order(
    symbol,
    side,
    order_type,
    quantity,
    price=None,
    stop_price=None,
    client: BinanceFuturesTestnetClient = None,
) -> dict:
    """
    Full order lifecycle: validate -> log/print request summary ->
    place via BinanceFuturesTestnetClient -> log/print response summary.

    Args:
        symbol, side, order_type, quantity, price, stop_price: raw CLI input,
            validated internally before any API call is made.
        client: an already-constructed BinanceFuturesTestnetClient. If not
            provided, one is constructed from environment credentials
            (see client.py). Accepting it as a parameter makes this function
            easy to unit test with a fake/mock client.

    Returns:
        The raw Binance order response dict on success.

    Raises:
        ValueError: if input validation fails (before any network call).
        RuntimeError: if the Binance API call fails for any reason.
    """
    logger.debug(
        "submit_order called with raw input: symbol=%r side=%r type=%r "
        "quantity=%r price=%r stop_price=%r",
        symbol, side, order_type, quantity, price, stop_price,
    )

    # 1. Validate BEFORE touching the network.
    order = validate_order_request(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
    )
    logger.info("Validated order: %s %s %s qty=%s", order["side"], order["type"], order["symbol"], order["quantity"])

    # 2. Print + log the request summary before submission.
    request_summary = build_request_summary(order)
    print(request_summary)
    logger.debug("Order request summary:\n%s", request_summary)

    # 3. Place the order.
    if client is None:
        client = BinanceFuturesTestnetClient()

    logger.info("Submitting order to Binance Futures Testnet...")
    try:
        response = client.place_order(order)
    except RuntimeError as exc:
        logger.error("Order submission FAILED: %s", exc)
        print(f"\nFAILED: {exc}")
        raise

    # 4. Print + log the response summary after submission.
    response_summary = build_response_summary(response)
    print("\n" + response_summary)
    logger.debug("Order response summary:\n%s", response_summary)

    status = response.get("status", "").upper()
    if status in ("FILLED", "NEW", "PARTIALLY_FILLED"):
        print(f"\nSUCCESS: Order placed (status={status}).")
        logger.info("Order placed successfully. orderId=%s status=%s", response.get("orderId"), status)
    else:
        print(f"\nWARNING: Order submitted but status is '{status}'. Check the response above.")
        logger.warning("Order submitted with unexpected status: %s", status)

    return response
