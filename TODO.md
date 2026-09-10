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

1. One routine daily command
   - Incremental paths exist (`update_daily_data.py`, `update_daily_basic.py`, `build_extended_history.py --update`); fold them into a single scheduled workflow with a trading-day check.

2. Delisted stocks
   - First-generation daily/adj_factor/daily_basic and the per-stock second-generation tables cover `status=listed` only. Backfill with `--statuses listed delisted` to remove survivorship bias in point-in-time universes.

3. Bring the price layer current
   - `daily/none`, `adj_factor` and `daily_basic` were last updated in May 2026; run `update_daily_data.py` and a `fetch_daily_basic.py` incremental.

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
