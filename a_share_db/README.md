# A Share DB

`a_share_db` is a local A-share research data warehouse. The storage plan is:

```text
CSV raw/temp layer -> Parquet formal data layer -> DuckDB query layer
```

Current ETL scripts still fetch into CSV first. Parquet will become the formal analysis layer. DuckDB is planned as the later SQL query layer over Parquet.

Formal tables use local domain fields only; provider-specific fields such as Tushare `ts_code` are converted inside ETL scripts and are not stored in formal tables.

Local data is written to the QuantDB volume by default:

```text
/Volumes/QuantDB/a_share_db/data/
```

The repository path `a_share_db/data` may be a symlink to that directory for compatibility with older commands. ETL scripts use `a_share_db.constant.paths.DATA_ROOT`, so default fetch, update, backup, log, Parquet, and warehouse paths stay on QuantDB. If the QuantDB volume is not mounted, scripts fail fast instead of recreating a large local data directory. Set `A_SHARE_DB_DATA_ROOT` only when intentionally overriding the data root.

Long-running commands share `a_share_db.utils.progress.ProgressReporter` and expose `--progress-every` for progress and ETA output.

## Setup

Install dependencies:

```bash
pip install -r a_share_db/requirements.txt
```

Set your Tushare token:

```bash
export TUSHARE_TOKEN="your_tushare_token"
```

Every fetch script also accepts `--token` if you do not want to use the environment variable.

## Data Layout

```text
a_share_db/data/
├── metadata/
│   ├── stock_basic.csv
│   ├── trade_calendar.csv
│   ├── stock_name_history.csv
│   ├── stock_company.csv
│   ├── ipo.csv
│   ├── stock_connect_constituent.csv
│   ├── index_basic.csv
│   ├── sw_industry.csv
│   └── sw_industry_member.csv
├── market_data/
│   ├── daily/
│   │   ├── none/
│   │   ├── qfq/
│   │   └── hfq/
│   ├── daily_basic/
│   ├── minute/
│   │   └── {frequency}/
│   │       ├── none/
│   │       ├── qfq/
│   │       └── hfq/
│   ├── adj_factor/
│   ├── limit_price/            {code}.csv   涨跌停价
│   ├── moneyflow/              {code}.csv   个股资金流向
│   ├── margin/                 {code}.csv   融资融券明细
│   ├── stock_connect_hold/     {code}.csv   北向持股
│   ├── suspend/                {year}.csv   停复牌
│   ├── st_stock/               {year}.csv   ST/风险警示名单
│   ├── dragon_tiger_list/      {year}.csv   龙虎榜
│   ├── dragon_tiger_inst/      {year}.csv   龙虎榜机构席位
│   ├── block_trade/            {year}.csv   大宗交易
│   ├── limit_list/             {year}.csv   涨跌停统计
│   ├── index_daily/            {index_code}.csv
│   ├── index_daily_basic/      {index_code}.csv
│   ├── index_weight/           {index_code}.csv
│   ├── sw_industry_daily/      {industry_index_code}.csv
│   ├── margin_summary.csv
│   └── stock_connect_flow.csv
├── financial/
│   ├── income/                 {period}.csv 利润表
│   ├── balance_sheet/          {period}.csv 资产负债表
│   ├── cash_flow/              {period}.csv 现金流量表
│   ├── indicator/              {period}.csv 财务指标
│   ├── forecast/               {period}.csv 业绩预告
│   ├── express/                {period}.csv 业绩快报
│   ├── disclosure_date/        {period}.csv 财报披露日期
│   ├── top10_holders/          {period}.csv
│   ├── top10_float_holders/    {period}.csv
│   ├── dividend/               {code}.csv   分红送股
│   └── holder_number/          {code}.csv   股东户数
├── macro/
│   ├── shibor.csv
│   ├── gdp.csv
│   ├── cpi.csv
│   ├── ppi.csv
│   └── money_supply.csv
├── parquet/
│   ├── metadata/
│   ├── daily/
│   ├── daily_basic/
│   ├── minute/
│   ├── adj_factor/
│   ├── financial/
│   ├── macro/
│   └── {extended table}/
├── raw/
├── warehouse/
│   └── a_share.duckdb
├── backups/
└── logs/
```

Raw provider output is off by default. Add `--with-raw` only when you need to keep third-party source rows for debugging or reconstruction.

Parquet and DuckDB are not built by the current fetch commands yet. The current priority is completing CSV collection, then adding Parquet build scripts from those CSV files.

The first Parquet builder mirrors the CSV layout: one formal CSV file becomes one Parquet file. Example:

```text
market_data/daily/none/600519.csv -> parquet/daily/none/600519.parquet
market_data/daily_basic/600519.csv -> parquet/daily_basic/600519.parquet
market_data/minute/1m/none/600519.csv -> parquet/minute/1m/none/600519.parquet
```

## Recommended Build Order

1. Build stock master data.
2. Build trade calendar.
3. Fetch unadjusted daily prices.
4. Fetch adjustment factors.
5. Fetch daily basic indicators.
6. Build qfq/hfq daily prices locally.
7. Build the extended tables (`scripts/workflows/build_extended_history.py`).
8. Build Parquet (`--tables all`).

```bash
python3 a_share_db/scripts/metadata/fetch_stock_basic.py --statuses L D P G

python3 a_share_db/scripts/metadata/fetch_trade_calendar.py \
  --exchanges SSE SZSE \
  --start-date 19901219 \
  --end-date 20260510

python3 a_share_db/scripts/market/fetch_daily.py \
  --all-stocks \
  --start-date 19900101 \
  --end-date 20260510 \
  --resume \
  --request-interval 0.13 \
  --progress-every 50 \
  --max-retries 3 \
  --retry-interval 5

python3 a_share_db/scripts/market/fetch_adj_factor.py \
  --all-stocks \
  --start-date 19900101 \
  --end-date 20260510 \
  --resume \
  --request-interval 0.13 \
  --progress-every 50 \
  --max-retries 3 \
  --retry-interval 5

python3 a_share_db/scripts/market/fetch_daily_basic.py \
  --all-stocks \
  --start-date 19900101 \
  --end-date 20260510 \
  --resume \
  --request-interval 0.13 \
  --progress-every 50 \
  --max-retries 3 \
  --retry-interval 5

python3 a_share_db/scripts/market/build_adjusted_daily.py \
  --all-stocks \
  --resume \
  --progress-every 50
```

If a long job fails midway, rerun the same command with `--resume`. Existing non-empty per-stock files will be skipped.

After the initial build, use the incremental update command instead of fetching full history again:

```bash
python3 a_share_db/scripts/market/update_daily.py \
  --all-stocks \
  --end-date 20260510 \
  --request-interval 0.13 \
  --progress-every 50 \
  --max-retries 3 \
  --retry-interval 5
```

## Common Commands

These wrappers choose the project defaults for routine workflows. You can run them without remembering the full parameter list.

Daily database update. This updates `daily/none`, updates `adj_factor`, and incrementally merges `daily/hfq`. It does not rebuild `qfq`.

```bash
python3 a_share_db/scripts/workflows/update_daily_data.py
```

Dry-run daily update:

```bash
python3 a_share_db/scripts/workflows/update_daily_data.py --dry-run
```

Rebuild qfq/hfq from local `none + adj_factor` data. This is a maintenance command, not something that has to run every day.

```bash
python3 a_share_db/scripts/workflows/rebuild_adjusted_daily_data.py
```

Rebuild only qfq:

```bash
python3 a_share_db/scripts/workflows/rebuild_adjusted_daily_data.py --adjust-types qfq
```

Build Parquet from existing CSV files:

```bash
python3 a_share_db/scripts/warehouse/build_parquet.py \
  --tables metadata daily adj_factor daily_basic \
  --resume \
  --progress-every 100
```

Build minute Parquet after minute CSV files exist:

```bash
python3 a_share_db/scripts/warehouse/build_parquet.py \
  --tables minute \
  --frequencies 1m \
  --adjust-types none \
  --resume \
  --progress-every 50
```

Refresh stock master data and trade calendar:

```bash
python3 a_share_db/scripts/metadata/refresh_metadata.py
```

## Extended Tables (Second Generation)

After the price layer, the warehouse adds the tables a systematic A-share strategy needs for realistic backtests and factor research. They are built by one command, in priority order, with resume semantics:

```bash
python3 a_share_db/scripts/workflows/build_extended_history.py
```

Run a subset with `--groups`:

```bash
python3 a_share_db/scripts/workflows/build_extended_history.py --groups metadata index
```

| Group | Why it matters | Tables |
| ----- | -------------- | ------ |
| `metadata` | universes, point-in-time names, IPO age filters, industry/benchmark reference | stock_name_history, stock_company, ipo, stock_connect_constituent, index_basic, sw_industry, sw_industry_member, stock_connect_flow, margin_summary, macro |
| `index` | benchmark returns, index universes, industry neutralization | index_daily, index_daily_basic, index_weight, sw_industry_daily |
| `financial` | fundamental factors with announce dates for point-in-time joins | income, balance_sheet, cash_flow, indicator, forecast, express, disclosure_date, top10_holders, top10_float_holders |
| `stock` | tradability and flow factors, per stock | limit_price, moneyflow, margin, stock_connect_hold, dividend, holder_number |
| `daily` | suspension/ST filters and event studies, per trade date | suspend, st_stock, dragon_tiger_list, dragon_tiger_inst, block_trade, limit_list |

All second-generation scripts share `a_share_db/utils/etl_common.py` (pagination, conversion, atomic writes, logging), `a_share_db/utils/etl_runners.py` (per-stock / per-date / per-key / single-table loops) and `a_share_db/utils/cli.py` (common flags). A new table therefore needs only a constant module with the provider-to-local field map plus a ~100 line script.

Every script accepts the same operational flags as the first-generation scripts (`--dry-run`, `--resume`, `--request-interval`, `--progress-every`, `--max-retries`, `--retry-interval`, `--no-log`, `--backup`, `--with-raw`). Per-stock scripts add `--codes/--codes-file/--all-stocks/--limit-stocks/--statuses`; per-date scripts add `--trade-calendar/--limit-days`; per-period scripts add `--periods/--refresh-recent-days`.

Layout rules:

- Per-stock time series stay one file per stock (`{code}.csv`), like `daily/`.
- Sparse per-day tables (suspensions, ST list, events) are one file per year (`{year}.csv`); resume skips complete years and always re-fetches the last year.
- Financial statements are one file per report period (`{period}.csv`) because Tushare bulk interfaces return the whole market for a period in one request; resume re-fetches periods ending within `--refresh-recent-days` (default 400) so late filings and restatements are picked up.
- Index and industry identifiers keep the Wind-style suffix (`000300.SH`, `801010.SI`) because the six-digit part is not unique across publishers.
- Units follow the first-generation convention: shares in 股, money in 元, ratios in %.

Provider-to-local field maps are the single source of truth and live in `a_share_db/constant/{limit_price,suspend,st_stock,name_change,stock_company,ipo,stock_connect,moneyflow,margin,index,industry,events,holders,financial,macro}.py`.

Build Parquet for the new tables after the CSV build:

```bash
python3 a_share_db/scripts/warehouse/build_parquet.py --tables extended --resume --progress-every 100
```

`--tables all` now includes the extended tables; `financial` and `macro` are group shortcuts.

## Scripts

### `scripts/metadata/fetch_stock_basic.py`

Fetches Tushare `stock_basic` and writes the local stock master table:

```text
a_share_db/data/metadata/stock_basic.csv
```

Use this table as the project-level stock universe. It intentionally stores local fields such as `code`, `exchange`, `board`, and `status`, not provider-specific identifiers.

Smoke test without writing files:

```bash
python3 a_share_db/scripts/metadata/fetch_stock_basic.py \
  --statuses L \
  --limit 20 \
  --dry-run
```

Refresh all statuses:

```bash
python3 a_share_db/scripts/metadata/fetch_stock_basic.py \
  --statuses L D P G
```

Also keep raw Tushare rows:

```bash
python3 a_share_db/scripts/metadata/fetch_stock_basic.py \
  --statuses L D P G \
  --with-raw
```

Import example:

```python
import os
from a_share_db.scripts.metadata.fetch_stock_basic import run_stock_basic_etl

result = run_stock_basic_etl(
    token=os.environ["TUSHARE_TOKEN"],
    statuses=["L"],
    limit=20,
    dry_run=True,
)
print(result["row_count"])
```

### `scripts/metadata/fetch_trade_calendar.py`

Fetches Tushare `trade_cal` and writes:

```text
a_share_db/data/metadata/trade_calendar.csv
```

Default exchanges are `SSE` and `SZSE`. Tushare does not expose `BSE` in this calendar interface, so BSE logic should reuse the SSE calendar when needed.

Smoke test:

```bash
python3 a_share_db/scripts/metadata/fetch_trade_calendar.py \
  --exchanges SSE SZSE \
  --start-date 20260101 \
  --end-date 20260131 \
  --dry-run
```

Build the local calendar:

```bash
python3 a_share_db/scripts/metadata/fetch_trade_calendar.py \
  --exchanges SSE SZSE \
  --start-date 19901219 \
  --end-date 20260510
```

Import example:

```python
import os
from a_share_db.scripts.metadata.fetch_trade_calendar import run_trade_calendar_etl

result = run_trade_calendar_etl(
    token=os.environ["TUSHARE_TOKEN"],
    exchanges=["SSE", "SZSE"],
    start_date="20260101",
    end_date="20260131",
    dry_run=True,
)
print(result["row_count"])
```

### `scripts/market/fetch_daily.py`

Fetches Tushare `daily` and writes unadjusted daily bars by stock:

```text
a_share_db/data/market_data/daily/none/{code}.csv
```

The formal output converts Tushare units:

```text
vol    手   -> volume 股
amount 千元 -> amount 元
```

Single-stock smoke test:

```bash
python3 a_share_db/scripts/market/fetch_daily.py \
  --codes 600519 \
  --start-date 20260101 \
  --end-date 20260131 \
  --dry-run
```

Fetch a few stocks for testing:

```bash
python3 a_share_db/scripts/market/fetch_daily.py \
  --all-stocks \
  --limit-stocks 5 \
  --start-date 20260101 \
  --end-date 20260131 \
  --resume
```

Fetch full history with resume and rate limiting:

```bash
python3 a_share_db/scripts/market/fetch_daily.py \
  --all-stocks \
  --start-date 19900101 \
  --end-date 20260510 \
  --resume \
  --request-interval 0.13 \
  --progress-every 50 \
  --max-retries 3 \
  --retry-interval 5
```

Import example:

```python
import os
from a_share_db.scripts.market.fetch_daily import run_daily_etl

result = run_daily_etl(
    token=os.environ["TUSHARE_TOKEN"],
    codes=["600519"],
    start_date="20260101",
    end_date="20260131",
    dry_run=True,
)
print(result["row_count"])
```

### `scripts/market/fetch_adj_factor.py`

Fetches Tushare `adj_factor` and writes local adjustment factors by stock:

```text
a_share_db/data/market_data/adj_factor/{code}.csv
```

Adjustment factors are kept in a separate table so qfq/hfq data can be rebuilt locally without depending on provider-specific adjusted price tables.

Single-stock smoke test:

```bash
python3 a_share_db/scripts/market/fetch_adj_factor.py \
  --codes 600519 \
  --start-date 20260101 \
  --end-date 20260131 \
  --dry-run
```

Fetch full history:

```bash
python3 a_share_db/scripts/market/fetch_adj_factor.py \
  --all-stocks \
  --start-date 19900101 \
  --end-date 20260510 \
  --resume \
  --request-interval 0.13 \
  --progress-every 50 \
  --max-retries 3 \
  --retry-interval 5
```

Import example:

```python
import os
from a_share_db.scripts.market.fetch_adj_factor import run_adj_factor_etl

result = run_adj_factor_etl(
    token=os.environ["TUSHARE_TOKEN"],
    codes=["600519"],
    start_date="20260101",
    end_date="20260131",
    dry_run=True,
)
print(result["row_count"])
```

### `scripts/market/fetch_daily_basic.py`

Fetches Tushare `daily_basic` and writes local daily indicators by stock:

```text
a_share_db/data/market_data/daily_basic/{code}.csv
```

Formal output uses local fields and units. Tushare share counts are converted from `万股` to `股`; market values are converted from `万元` to `元`.

When both `--start-date` and `--end-date` are provided, the script automatically splits long history into request windows to stay below the provider row limit, then merges by `code + trade_date`.

Single-stock smoke test:

```bash
python3 a_share_db/scripts/market/fetch_daily_basic.py \
  --codes 600519 \
  --start-date 20260101 \
  --end-date 20260131 \
  --dry-run
```

Fetch full history:

```bash
python3 a_share_db/scripts/market/fetch_daily_basic.py \
  --all-stocks \
  --start-date 19900101 \
  --end-date 20260510 \
  --resume \
  --request-interval 0.13 \
  --progress-every 50 \
  --max-retries 3 \
  --retry-interval 5
```

Import example:

```python
import os
from a_share_db.scripts.market.fetch_daily_basic import run_daily_basic_etl

result = run_daily_basic_etl(
    token=os.environ["TUSHARE_TOKEN"],
    codes=["600519"],
    start_date="20260101",
    end_date="20260131",
    dry_run=True,
)
print(result["row_count"])
```

### `scripts/market/fetch_minute.py`

Fetches Tushare `stk_mins` and writes unadjusted minute bars by stock and frequency:

```text
a_share_db/data/market_data/minute/{frequency}/none/{code}.csv
```

Formal output keeps local fields only. Tushare `ts_code` and provider `freq` are converted inside the script.

Request windows are sized by frequency using local `trade_calendar.csv` so each Tushare request stays below 8000 rows while covering as many trading days as possible. Defaults are `1m=33`, `5m=163`, `15m=470`, `30m=888`, `60m=1599` trading days per request. Use `--window-trading-days` only when you need to override this.

For each stock, the effective start time is `max(--start-date, stock_basic.list_date)`, so full-market history jobs do not waste requests before a stock was listed.

Single-stock smoke test:

```bash
python3 a_share_db/scripts/market/fetch_minute.py \
  --codes 600519 \
  --frequencies 1m \
  --start-date "2026-01-05 09:30:00" \
  --end-date "2026-01-05 15:00:00" \
  --dry-run
```

Fetch a short multi-frequency sample:

```bash
python3 a_share_db/scripts/market/fetch_minute.py \
  --codes 600519 000001 \
  --frequencies 1m 5m \
  --start-date 20260101 \
  --end-date 20260131 \
  --progress-every 1
```

Fetch historical minute data with resume and rate limiting:

```bash
python3 a_share_db/scripts/market/fetch_minute.py \
  --all-stocks \
  --frequencies 1m \
  --start-date 20160101 \
  --end-date 20260510 \
  --resume \
  --request-interval 0.13 \
  --progress-every 10 \
  --max-retries 3 \
  --retry-interval 5
```

Import example:

```python
import os
from a_share_db.scripts.market.fetch_minute import run_minute_etl

result = run_minute_etl(
    token=os.environ["TUSHARE_TOKEN"],
    codes=["600519"],
    frequencies=["1m"],
    start_date="2026-01-05 09:30:00",
    end_date="2026-01-05 15:00:00",
    dry_run=True,
)
print(result["row_count"])
```

### `scripts/market/build_adjusted_daily.py`

Builds qfq and hfq daily bars from local unadjusted daily data plus local adjustment factors:

```text
a_share_db/data/market_data/daily/qfq/{code}.csv
a_share_db/data/market_data/daily/hfq/{code}.csv
```

No provider API is called by this script.

Build one stock:

```bash
python3 a_share_db/scripts/market/build_adjusted_daily.py \
  --codes 600519
```

Build only qfq:

```bash
python3 a_share_db/scripts/market/build_adjusted_daily.py \
  --codes 600519 \
  --adjust-types qfq
```

Build all stocks with resume:

```bash
python3 a_share_db/scripts/market/build_adjusted_daily.py \
  --all-stocks \
  --resume \
  --progress-every 50
```

Progress output prints processed stocks, percent, elapsed time, ETA, rows, skipped count, and failures.

Import example:

```python
from a_share_db.scripts.market.build_adjusted_daily import run_build_adjusted_daily

result = run_build_adjusted_daily(codes=["600519"], adjust_types=["qfq"], dry_run=True)
print(result["row_count"])
```

### `scripts/market/update_daily.py`

Incrementally updates existing daily files. For each stock, it reads the max local `trade_date` from:

```text
a_share_db/data/market_data/daily/none/{code}.csv
```

Then it fetches from the next calendar day through `--end-date`, merges by `code + trade_date`, sorts the file, and rewrites the same CSV path atomically. This keeps file names stable and avoids downloading full history every time.

By default it also updates `adj_factor` and incrementally merges `hfq` rows for missing trade dates. It does not rebuild `qfq` by default, because qfq prices depend on the latest adjustment factor and can require historical rows to be recalculated.

Use `build_adjusted_daily.py` to manually or periodically rebuild qfq/hfq from local `none + adj_factor` data.

Smoke test a few stocks without writing files:

```bash
python3 a_share_db/scripts/market/update_daily.py \
  --all-stocks \
  --limit-stocks 5 \
  --end-date 20260510 \
  --dry-run
```

Update all existing local daily files:

```bash
python3 a_share_db/scripts/market/update_daily.py \
  --all-stocks \
  --end-date 20260510 \
  --request-interval 0.13 \
  --progress-every 50 \
  --max-retries 3 \
  --retry-interval 5
```

Initialize missing stocks during an update:

```bash
python3 a_share_db/scripts/market/update_daily.py \
  --all-stocks \
  --init-missing \
  --start-date 19900101 \
  --end-date 20260510
```

Only update unadjusted daily files and adjustment factors, and skip hfq/qfq outputs:

```bash
python3 a_share_db/scripts/market/update_daily.py \
  --all-stocks \
  --no-adjusted
```

Explicitly rebuild qfq for changed stocks during an update. This is slower and normally should be reserved for manual maintenance windows:

```bash
python3 a_share_db/scripts/market/update_daily.py \
  --all-stocks \
  --end-date 20260510 \
  --adjust-types hfq qfq \
  --progress-every 50
```

Import example:

```python
import os
from a_share_db.scripts.market.update_daily import run_update_daily

result = run_update_daily(
    token=os.environ["TUSHARE_TOKEN"],
    codes=["600519"],
    end_date="20260510",
    dry_run=True,
)
print(result["daily_new_rows"])
```

### `a_share_db/utils/provider_codes.py`

Converts local stock fields into provider-specific symbols at runtime. Use this module instead of storing provider codes in formal tables.

```python
from a_share_db.utils.provider_codes import (
    build_eastmoney_secid,
    build_sina_symbol,
    build_tencent_symbol,
    build_tushare_ts_code,
)

print(build_tushare_ts_code("600519", "SSE"))   # 600519.SH
print(build_sina_symbol("600519", "SSE"))       # sh600519
print(build_eastmoney_secid("600519", "SSE"))   # 1.600519
```

### Second-generation fetch scripts

Each script writes the formal table listed and supports `--dry-run` for a smoke test. Smoke-test examples:

```bash
# market_data, per stock
python3 a_share_db/scripts/market/fetch_limit_price.py --codes 600519 --start-date 20240101 --end-date 20240131 --dry-run
python3 a_share_db/scripts/market/fetch_moneyflow.py --codes 600519 --start-date 20240101 --end-date 20240131 --dry-run
python3 a_share_db/scripts/market/fetch_margin.py --tables detail --codes 600519 --start-date 20240101 --end-date 20240131 --dry-run
python3 a_share_db/scripts/market/fetch_stock_connect_hold.py --codes 600519 --start-date 20240101 --end-date 20240131 --dry-run

# market_data, per trade date (yearly files)
python3 a_share_db/scripts/market/fetch_suspend.py --start-date 20240102 --end-date 20240105 --dry-run
python3 a_share_db/scripts/market/fetch_st_stock.py --start-date 20240102 --end-date 20240103 --dry-run
python3 a_share_db/scripts/market/fetch_market_events.py --tables block_trade limit_list --start-date 20240102 --end-date 20240103 --dry-run

# market_data, single files
python3 a_share_db/scripts/market/fetch_margin.py --tables summary --dry-run
python3 a_share_db/scripts/market/fetch_stock_connect_flow.py --dry-run

# metadata
python3 a_share_db/scripts/metadata/fetch_name_change.py --dry-run
python3 a_share_db/scripts/metadata/fetch_stock_company.py --dry-run
python3 a_share_db/scripts/metadata/fetch_ipo.py --dry-run
python3 a_share_db/scripts/metadata/fetch_stock_connect_constituent.py --dry-run

# index and industry
python3 a_share_db/scripts/index/fetch_index_basic.py --dry-run
python3 a_share_db/scripts/index/fetch_index_daily.py --index-codes 000300.SH --start-date 20240101 --end-date 20240131 --dry-run
python3 a_share_db/scripts/index/fetch_index_weight.py --index-codes 000300.SH --start-date 20240101 --end-date 20240301 --dry-run
python3 a_share_db/scripts/index/fetch_sw_industry.py --dry-run
python3 a_share_db/scripts/index/fetch_sw_industry_daily.py --index-codes 801010.SI --start-date 20240101 --end-date 20240131 --dry-run

# financial
python3 a_share_db/scripts/financial/fetch_financial_statements.py --periods 20231231 --tables income --dry-run
python3 a_share_db/scripts/financial/fetch_dividend.py --codes 600519 --dry-run
python3 a_share_db/scripts/financial/fetch_holder_number.py --codes 600519 --dry-run
python3 a_share_db/scripts/financial/fetch_top10_holders.py --periods 20231231 --dry-run

# macro
python3 a_share_db/scripts/macro/fetch_macro.py --dry-run
```

Routine refresh in one command (skips non-trading days unless `--force`; schedule it every evening):

```bash
python3 a_share_db/scripts/workflows/refresh_all.py                 # prices, daily_basic, extended tables, 1m/5m minute bars, Parquet
python3 a_share_db/scripts/workflows/refresh_all.py --skip-minute   # same without minute bars
```

Stock selection on every per-stock script (first and second generation) accepts `--statuses`; the default is `listed`, and `--statuses delisted` backfills delisted stocks so point-in-time universes are free of survivorship bias.

Minute bars are updated in place with `fetch_minute.py --update`: the last `bar_end_time` is read from the tail of each file and only newer bars are appended, so a daily update does not rewrite hundreds of gigabytes.

Incremental updates. Per-stock trade-date tables (`limit_price`, `moneyflow`, `margin`, `stock_connect_hold`) accept `--update`: each existing file is extended from its max `trade_date`, missing files are fetched in full. `daily_basic` has its own incremental command. Bringing everything to today therefore is:

```bash
python3 a_share_db/scripts/workflows/update_daily_data.py                       # daily/none, adj_factor, hfq
python3 a_share_db/scripts/market/update_daily_basic.py --all-stocks             # daily_basic
python3 a_share_db/scripts/workflows/build_extended_history.py --update          # all extended tables
python3 a_share_db/scripts/warehouse/build_parquet.py --tables metadata daily adj_factor daily_basic extended
```

`build_extended_history.py --update` re-fetches the last year of per-date tables, recent report periods of financial tables, all single-file tables, and refreshes `dividend`/`holder_number` in full because those provider interfaces have no date filter.

Full-history commands are what `build_extended_history.py` runs; use the individual scripts when you need to rebuild one table, for example:

```bash
python3 a_share_db/scripts/market/fetch_limit_price.py --all-stocks --resume --request-interval 0.15 --progress-every 200
python3 a_share_db/scripts/financial/fetch_financial_statements.py --tables income balance_sheet cash_flow indicator --resume
python3 a_share_db/scripts/market/fetch_suspend.py --resume
```

Import example:

```python
import os
from a_share_db.scripts.financial.fetch_financial_statements import run_financial_table_etl

result = run_financial_table_etl("income", token=os.environ["TUSHARE_TOKEN"], periods=["20231231"], dry_run=True)
print(result["row_count"])
```

Notes on provider behaviour discovered while building these tables:

- `suspend_d` per stock is truncated to 100 rows, so suspensions are fetched by trade date.
- `stock_st` history starts in 2005; earlier ST status can be derived from `stock_name_history` names containing `ST`.
- `new_share` coverage starts in 2008.
- Bulk financial interfaces (`*_vip`) repeat rows for the same filing; rows are de-duplicated on `code + report_period + statement_type + actual_announce_date`, preferring `is_update = 1`.
- Only `statement_type = consolidated` (provider `report_type=1`) is fetched by default; pass `--report-types 1 4` to keep prior-period consolidated statements as well.
- Per-stock scripts default to `--statuses listed`; pass `--statuses listed delisted` to include delisted stocks and reduce survivorship bias.

## Operational Notes

`--dry-run` fetches and converts data but does not write CSV files or logs.

`--limit` is for single-output scripts such as stock basic and calendar. `--limit-stocks` is for per-stock scripts.

`--resume` skips existing non-empty per-stock output files. It is the default tool for long full-market jobs.

`--request-interval 0.13` keeps requests under roughly 500 calls per minute, before retries and provider-side variance.

`--progress-every 50` prints progress and ETA every 50 stocks for long-running commands. Use `--progress-every 10` for more frequent updates, or `--progress-every 0` to disable it.

`--stop-on-error` is useful for debugging. Without it, per-stock jobs record failures and continue; rerun with `--resume` after fixing the issue.

Existing output files are not backed up by default. Pass `--backup` to move previous files to `a_share_db/data/backups/` before replacement.

Development convention: any new command that loops over many stocks should reuse `a_share_db.utils.progress.ProgressReporter` and expose a `--progress-every` option.

Reusable logic should live in package modules instead of being copied across scripts. Keep `scripts/` command files focused on CLI parsing and orchestration; shared behavior such as progress reporting, provider code conversion, date/file helpers, merge logic, and constants should be extracted into importable modules.
