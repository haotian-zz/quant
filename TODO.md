# TODO

## A Share Data Tables

Completed foundation:

- Stock list / stock master data
- Trade calendar
- Historical daily prices, adjustment factors, locally rebuilt qfq/hfq
- Historical minute prices (1m, 5m)
- Daily indicators (daily_basic)

Completed second generation (built by `scripts/workflows/build_extended_history.py`, see README "Extended Tables"):

- Trading constraints: limit prices, suspensions, ST list, limit-up/down statistics
- Universe / metadata: stock name history, company profiles, IPO list, stock-connect constituents, index metadata, Shenwan industry classification and membership history
- Benchmarks: index daily quotes, index valuation, index constituent weights, Shenwan industry index quotes
- Flows and positions: per-stock money flow, margin detail and summary, northbound holdings, north/south aggregate flow, dragon-tiger list and seats, block trades
- Fundamentals by report period: income, balance sheet, cash flow, financial indicators, forecasts, express reports, disclosure dates, top-10 holders / float holders; per stock: dividends, shareholder counts
- Macro: Shibor, GDP, CPI, PPI, money supply

### P0: Operations

1. Schedule `scripts/workflows/refresh_all.py` (cron/launchd, weekday evenings). The command itself exists and skips non-trading days.
2. Delisted stocks: all per-stock scripts accept `--statuses`; price layer backfill for delisted stocks ran on 2026-09-10 (check `logs/build_20260910/10_delisted_price_layer.log`).
3. Minute bars: `fetch_minute.py --update` appends to 1m/5m; `build_minute_derived.py` builds 15m/30m/60m none/hfq/qfq from 5m (first full build queued after the 2026-09-10 minute update). qfq minute files need periodic full rebuilds (weekly is enough).
4. Stock index futures added (`scripts/futures/fetch_futures.py`); options (`opt_daily`) and ETF daily (`fund_daily`) remain optional.

### P1: Data Quality

4. Cross-check local qfq/hfq against provider `stk_factor_pro` adjusted prices for a sample of stocks.
5. Validate `moneyflow` and `margin` totals against `margin_summary` / exchange statistics.
6. Add a lightweight coverage report (files, min/max dates, row counts per table) so gaps are visible after each build.

### P2: Strategy-Dependent Tables

7. `stk_factor_pro` technical factors (261 columns, ~8k rows per stock) — only if local factor computation proves insufficient.
8. `cyq_perf` / `cyq_chips` chip distribution (2018+).
9. Call/close auction data (`stk_auction_o`, `stk_auction_c`, 2009+).
10. `share_float` lock-up releases, `pledge_stat` pledges, `repurchase` buybacks, `stk_holdertrade` insider trades.
11. `bak_basic` historical stock list snapshots (2015+) for point-in-time industry/name checks.
12. Weekly/monthly bars — generate locally from daily data.

### P3: Defer

13. Realtime daily and realtime minute data (needs scheduling, overwrite rules and recovery logic).
14. Company management, compensation and shareholding tables.
15. News and announcement text (`news`, `anns_d`) — not enabled for the current token.
