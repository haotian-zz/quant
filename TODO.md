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

Completed third generation on 2026-09-13 (registry-driven, `scripts/warehouse/fetch_tables.py --tiers 1 2`; 54 tables, 111M rows, Parquet built): broker research forecasts, audit opinions, main business composition, lock-up releases, insider trades, repurchases, pledges, managers and compensation, fund master/quotes/NAV/shares/holdings, Eastmoney and Tonghuashun sectors, CITIC and global indices, sector/market money flow, options, futures settlement and member positions, call auctions, chip distribution, provider technical factors, market summaries, Stock Connect leaderboards, hot money and hot lists, limit streaks, convertible bonds, LPR/PMI/social financing/US treasury/economic calendar.

### P0: Operations

1. Schedule `scripts/workflows/refresh_all.py` (launchd/cron, weekday evenings after 18:00). The command exists, skips non-trading days, and covers prices, daily_basic, extended and registered tables, futures, minute bars, derived minute bars and Parquet. Needs a chosen run time.
2. Weekly maintenance: `build_minute_derived.py --all-stocks --adjust-types qfq` and `build_adjusted_daily.py --all-stocks --adjust-types qfq` (qfq depends on the latest factor and is not part of the daily refresh).
3. Northbound holdings (`stock_connect_hold`) end on 2026-06-30 at the provider; check periodically whether Tushare resumed the series.

### P1: Data Quality

4. Cross-check local qfq/hfq against provider `technical_factor` (`close_qfq`/`close_hfq`) for a sample of stocks.
5. Validate `moneyflow` and `margin` totals against `margin_summary` / `market_summary`.
6. Add a lightweight coverage report (files, min/max dates, row counts per table) so gaps are visible after each build; the ad-hoc version used on 2026-09-13 lives only in the session notes.
7. `holder_number` contains a few provider rows with impossible dates (1900, 2027); decide whether to filter at load time or in ETL.
8. Delisted stocks are covered in every per-stock table, but `minute` bars exist only for listed stocks.

### P2: Optional

9. `bak_basic` historical stock list snapshots (2015+) for point-in-time name/industry checks.
10. Weekly/monthly bars — generate locally from daily data.
11. `cyq_chips` per-stock daily chip curves (~500k requests) only if a chip-based strategy needs the full curve; `chip_distribution` (cyq_perf summary) is already in place.
12. Open-market funds (`market=O`) NAV/portfolio beyond ETFs, if fund-flow research needs them.

### P3: Defer

13. Realtime daily and realtime minute data (needs scheduling, overwrite rules and recovery logic).
14. News and announcement text (`news`, `anns_d`) — not enabled for the current token.
15. Index and futures minute bars (`idx_mins`, `ft_mins`) — not enabled for the current token.
