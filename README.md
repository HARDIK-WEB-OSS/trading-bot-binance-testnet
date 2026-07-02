# Binance Futures Trade CLI

A small, focused Python CLI for placing **MARKET**, **LIMIT**, and **STOP**
(stop-limit) orders on **Binance Futures Testnet (USDT-M)**, built with
[python-binance](https://python-binance.readthedocs.io/).

It validates every input before touching the network, prints clear
before/after order summaries, and logs the full request/response lifecycle
to a file for debugging, while keeping the console output clean.

---

## 1. Project structure

```
trading_bot/
  bot/
    __init__.py
    client.py           # Binance API wrapper (auth + futures_create_order)
    orders.py            # validate -> place -> summarize orchestration
    validators.py         # input validation, raises ValueError on bad input
    logging_config.py      # DEBUG to logs/trading_bot.log, INFO to console
  cli.py                # CLI entry point (argparse)
  README.md
  requirements.txt
  .env.example
  logs/
    trading_bot.log      # created/appended at runtime
```

---

## 2. Setup

### 2.1 Create a Binance Futures Testnet account

1. Go to **https://testnet.binancefuture.com**.
2. Log in with a GitHub account (the Futures Testnet uses GitHub OAuth, not a
   regular Binance account).
3. Once logged in, you'll land on a simulated USDT-M futures trading
   interface pre-loaded with test funds (e.g. 10,000 fake USDT). No real
   money is ever involved here.

### 2.2 Generate API keys

1. On the testnet site, find the **API Key** panel (usually on the right
   side of the trading page, or under your account menu).
2. Click **Generate HMAC_SHA256 Key**.
3. Copy the **API Key** and **Secret Key** immediately -- the secret is only
   shown once.
4. These keys only work against the testnet host
   (`https://testnet.binancefuture.com`); they will not work on real Binance.

### 2.3 Install dependencies

Requires Python 3.9+.

```bash
cd trading_bot
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2.4 Configure your `.env`

```bash
cp .env.example .env
```

Edit `.env` and paste in the keys from step 2.2:

```
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

`.env` is loaded automatically by `cli.py` via `python-dotenv`. Never commit
this file or share its contents.

---

## 3. Usage

Run everything from inside the `trading_bot/` folder.

### 3.1 MARKET order

Buy 0.01 BTC at the current market price:

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### 3.2 LIMIT order

Sell 0.01 BTC if/when the price reaches 65000 USDT:

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000
```

### 3.3 STOP order (stop-limit, bonus order type)

Buy 0.1 ETH with a limit price of 3500, triggered once the market price
crosses 3490 (a stop-limit buy, e.g. to catch a breakout):

```bash
python cli.py --symbol ETHUSDT --side BUY --type STOP --quantity 0.1 --price 3500 --stop-price 3490
```

### 3.4 CLI flags reference

| Flag            | Required for       | Description                              |
|-----------------|---------------------|-------------------------------------------|
| `--symbol`      | all                 | USDT-M futures symbol, e.g. `BTCUSDT`     |
| `--side`        | all                 | `BUY` or `SELL`                           |
| `--type`        | all                 | `MARKET`, `LIMIT`, or `STOP`              |
| `--quantity`    | all                 | Order quantity, must be > 0               |
| `--price`       | `LIMIT`, `STOP`     | Limit price, must be > 0                  |
| `--stop-price`  | `STOP`              | Stop trigger price, must be > 0           |

All input is validated **before** any API call is made. Invalid input
raises a `ValueError` with a specific message and the CLI exits with code
`1` without ever contacting Binance. API/network failures during
submission exit with code `2`.

### 3.5 Sample output

Real output from a MARKET order placed against the testnet:

```
Order Request Summary
----------------------
  Symbol:      BTCUSDT
  Side:        BUY
  Type:        MARKET
  Quantity:    0.01

Order Response Summary
-----------------------
  Order ID:      3145678214
  Status:        FILLED
  Executed Qty:  0.01
  Avg Price:     60123.40000

SUCCESS: Order placed (status=FILLED).
```

Note: on the testnet, a MARKET order's status can briefly show `NEW` before
settling to `FILLED`; both are treated as success as long as Binance
accepts the order.

---

## 4. Logging

- **Console**: `INFO` level and above only -- concise progress messages,
  warnings, and errors. This is what you see while running the CLI.
- **File** (`logs/trading_bot.log`): `DEBUG` level and above -- every raw
  request payload sent to Binance, every raw response received, and full
  stack traces for any error. The file rotates at 5MB, keeping 3 backups.

This split means day-to-day usage stays readable, while a full audit trail
is always available on disk for debugging failed orders.

---

## 5. Error handling

- **Validation errors** (bad symbol format, negative quantity, missing
  price for a LIMIT/STOP order, etc.) are raised as `ValueError` by
  `bot/validators.py` and caught in `cli.py`. No network call is made.
- **API/network errors**: `bot/client.py` catches `BinanceAPIException`,
  `BinanceOrderException`, `BinanceRequestException` (all from
  `python-binance`), and `requests.exceptions.RequestException` for
  connectivity issues, and re-raises all of them as a single `RuntimeError`
  with a clear message. This keeps `bot/orders.py` and `cli.py` simple --
  they only ever need to catch `RuntimeError` for anything API-related.

---

## 6. Assumptions

- **STOP order semantics**: Binance Futures' `STOP` order type is a
  stop-**limit** order, requiring both `price` (the limit price once
  triggered) and `stopPrice` (the trigger price). This project follows that
  API semantics exactly; it does not implement `STOP_MARKET`.
- **Symbol validation** uses a shape check (`[A-Z0-9]{2,17}USDT`) rather
  than calling Binance's `exchangeInfo` endpoint, so validation stays fast
  and works fully offline before any network call. It does not guarantee
  the symbol is actually listed -- Binance itself will reject unknown
  symbols at submission time, and that rejection is surfaced as a
  `RuntimeError`.
- **Order sizing / precision**: this project does not round quantity or
  price to each symbol's `LOT_SIZE` / `PRICE_FILTER` tick size. If Binance
  rejects an order for precision reasons, that error is surfaced as-is via
  `RuntimeError`; the user is expected to pass values consistent with the
  symbol's filters.
- **Single order per invocation**: the CLI is designed to place one order
  per run. Batching/looping is left to the caller (e.g. a shell script).
  All orders are placed with `timeInForce=GTC` for LIMIT/STOP orders.
- **Testnet only**: `client.py` hardcodes `testnet=True` and explicitly
  sets `FUTURES_URL` to `https://testnet.binancefuture.com/fapi`. Using
  this project against production Binance would require deliberate code
  changes -- this is intentional, to avoid accidentally placing real orders.
- **No position/account management**: this project only places orders. It
  does not check existing positions, leverage, margin mode, or account
  balance before submitting -- Binance's own order-rejection rules
  (insufficient margin, etc.) apply and are surfaced as `RuntimeError`.