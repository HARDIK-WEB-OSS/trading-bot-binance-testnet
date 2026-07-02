"""
trading_bot.bot
================

Core package for the Binance Futures Testnet (USDT-M) trading bot.

Modules:
    client         - Thin wrapper around python-binance's Client, configured for testnet.
    orders         - High level order orchestration (validate -> place -> summarize).
    validators     - Pure input validation helpers, raise ValueError on bad input.
    logging_config - Central logging setup (DEBUG to file, INFO to console).
"""

__version__ = "1.0.0"
