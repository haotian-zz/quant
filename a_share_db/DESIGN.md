````markdown
# A 股本地数据仓库 LLD

## 1. 目标

从 0 构建一个本地 A 股数据仓库。当前采用三层数据格式：

```text
CSV raw/临时层 -> Parquet 正式数据层 -> DuckDB 查询层
```

第一阶段仍先用 CSV 跑通抓取、转换和断点续跑：

```text
股票基础信息 → 交易日历 → 日线行情 → 增量更新 → 日志记录
````

随后构建 Parquet 正式数据层。DuckDB 暂时不作为落地目标，只作为后续 SQL 查询层读取 Parquet。

---

## 2. 目录结构

```text
a_share_db/
├── data/
│   ├── metadata/
│   │   ├── stock_basic.csv
│   │   ├── raw_tushare_stock_basic.csv
│   │   ├── raw_tushare_trade_calendar.csv
│   │   └── trade_calendar.csv
│   │
│   ├── market_data/
│   │   ├── daily/
│   │   │   ├── none/
│   │   │   ├── qfq/
│   │   │   └── hfq/
│   │   ├── daily_basic/
│   │   ├── minute/
│   │   │   └── {frequency}/
│   │   │       ├── none/
│   │   │       ├── qfq/
│   │   │       └── hfq/
│   │   └── adj_factor/
│   │
│   ├── parquet/
│   │   ├── metadata/
│   │   ├── daily/
│   │   │   └── {adjust_type}/
│   │   │       └── {code}.parquet
│   │   ├── daily_basic/
│   │   │   └── {code}.parquet
│   │   ├── minute/
│   │   │   └── {frequency}/
│   │   │       └── {adjust_type}/
│   │   │           └── {code}.parquet
│   │   └── adj_factor/
│   │       └── {code}.parquet
│   │
│   ├── raw/
│   │   ├── daily/
│   │   │   └── {provider}/
│   │   │       └── {adjust_type}/
│   │   ├── daily_basic/
│   │   │   └── {provider}/
│   │   ├── minute/
│   │   │   └── {provider}/
│   │   │       └── {frequency}/
│   │   └── adj_factor/
│   │       └── {provider}/
│   │
│   ├── backups/
│   │   └── {timestamp}/
│   │
│   ├── warehouse/
│   │   └── a_share.duckdb
│   │
│   └── logs/
│       ├── etl_log.csv
│       └── update_status.csv
│
├── constant/
│   ├── stock_basic.py / daily.py / daily_basic.py / minute.py / trade_calendar.py
│   ├── limit_price.py / suspend.py / st_stock.py / name_change.py / stock_company.py / ipo.py
│   ├── stock_connect.py / moneyflow.py / margin.py / index.py / industry.py / events.py
│   ├── holders.py / financial.py / macro.py
│   ├── paths.py
│   ├── warehouse.py
│   └── commands.py
│
├── utils/
│   ├── progress.py
│   ├── provider_codes.py
│   ├── etl_common.py       # 分页、字段映射转换、原子写、日志、股票选择
│   ├── etl_runners.py      # per-stock / per-date / per-key / single-table 通用循环
│   └── cli.py              # 通用命令行参数
│
└── scripts/
    ├── metadata/
    │   ├── fetch_stock_basic.py / fetch_trade_calendar.py / refresh_metadata.py
    │   ├── fetch_name_change.py / fetch_stock_company.py / fetch_ipo.py
    │   └── fetch_stock_connect_constituent.py
    ├── market/
    │   ├── fetch_adj_factor.py / fetch_daily.py / fetch_minute.py / fetch_daily_basic.py
    │   ├── build_adjusted_daily.py / update_daily.py
    │   ├── fetch_limit_price.py / fetch_moneyflow.py / fetch_margin.py / fetch_stock_connect_hold.py
    │   ├── fetch_suspend.py / fetch_st_stock.py / fetch_market_events.py
    │   └── fetch_stock_connect_flow.py
    ├── index/
    │   ├── fetch_index_basic.py / fetch_index_daily.py / fetch_index_weight.py
    │   └── fetch_sw_industry.py / fetch_sw_industry_daily.py
    ├── financial/
    │   ├── fetch_financial_statements.py / fetch_dividend.py
    │   └── fetch_holder_number.py / fetch_top10_holders.py
    ├── macro/
    │   └── fetch_macro.py
    ├── workflows/
    │   ├── update_daily_data.py
    │   ├── rebuild_adjusted_daily_data.py
    │   └── build_extended_history.py
    └── warehouse/
        └── build_parquet.py
```

第二代数据目录（同样位于 `data/` 下）：

```text
data/
├── metadata/        stock_name_history.csv, stock_company.csv, ipo.csv, stock_connect_constituent.csv,
│                    index_basic.csv, sw_industry.csv, sw_industry_member.csv
├── market_data/     limit_price/{code}.csv, moneyflow/{code}.csv, margin/{code}.csv, stock_connect_hold/{code}.csv,
│                    suspend/{year}.csv, st_stock/{year}.csv, dragon_tiger_list/{year}.csv, dragon_tiger_inst/{year}.csv,
│                    block_trade/{year}.csv, limit_list/{year}.csv,
│                    index_daily/{index_code}.csv, index_daily_basic/{index_code}.csv, index_weight/{index_code}.csv,
│                    sw_industry_daily/{industry_index_code}.csv, margin_summary.csv, stock_connect_flow.csv
├── financial/       income/{period}.csv, balance_sheet/{period}.csv, cash_flow/{period}.csv, indicator/{period}.csv,
│                    forecast/{period}.csv, express/{period}.csv, disclosure_date/{period}.csv,
│                    top10_holders/{period}.csv, top10_float_holders/{period}.csv,
│                    dividend/{code}.csv, holder_number/{code}.csv
├── macro/           shibor.csv, gdp.csv, cpi.csv, ppi.csv, money_supply.csv
└── raw/tushare/     可选的第三方原始行（--with-raw）
```

---

## 3. 数据文件设计

### 3.0 存储层职责

| 层级 | 路径 | 作用 |
| ---- | ---- | ---- |
| CSV raw/临时层 | `data/metadata/`、`data/market_data/`、`data/raw/` | 当前 ETL 直接写入；便于断点续跑、排查、临时人工检查 |
| Parquet 正式数据层 | `data/parquet/` | 后续正式分析数据层；字段仍使用本地领域语义，不保存第三方字段 |
| DuckDB 查询层 | `data/warehouse/a_share.duckdb` | 后续 SQL 查询入口；优先读取 Parquet，不作为当前抓取写入目标 |

当前阶段继续先拉取 CSV。Parquet 构建脚本会从 CSV 正式表读取并生成列式文件。DuckDB 集成暂缓，只在设计中预留。

Parquet 第一版按当前 CSV 文件粒度生成：一个正式 CSV 文件对应一个 Parquet 文件。例如：

```text
data/market_data/daily/none/600519.csv
-> data/parquet/daily/none/600519.parquet

data/market_data/minute/1m/none/600519.csv
-> data/parquet/minute/1m/none/600519.parquet
```

暂不按 `trade_date` 分区，避免分钟数据产生海量小文件。后续如查询模式明确需要按日期裁剪，再增加 compaction/partition 脚本。

Parquet 构建命令：

```bash
# 构建 metadata、daily、adj_factor 的 Parquet 正式层。
python3 a_share_db/scripts/warehouse/build_parquet.py \
  --tables metadata daily adj_factor daily_basic \
  --resume \
  --progress-every 100

# 构建 1m 分钟 Parquet 正式层。
python3 a_share_db/scripts/warehouse/build_parquet.py \
  --tables minute \
  --frequencies 1m \
  --adjust-types none \
  --resume \
  --progress-every 50
```

Parquet 构建同样遵循项目通用规则：默认不备份，只有显式传入 `--backup` 才移动旧文件到 `data/backups/`；长任务必须显示进度；正式字段仍然不能保存第三方字段名。

正式数据表设计原则：

```text
data/metadata/*、data/market_data/* 是当前 CSV 正式/临时落地层。
data/parquet/* 是目标正式数据层。
正式字段必须使用本地领域语义，不保存第三方接口字段名、第三方代码格式或数据源标记。
第三方原始字段、原始代码、接口来源只允许出现在 raw_* 文件或 ETL 日志中。
第三方接口调用需要的 symbol、secid 等标识由 a_share_db/utils/provider_codes.py 按需生成。
```

### 3.1 股票基础信息表：`data/metadata/stock_basic.csv`

用途：存储 A 股股票基础信息，作为后续抓取行情、财务、公告的主表。

| Field                    | 中文名      | 说明                                               |
|--------------------------|----------|--------------------------------------------------|
| `code`                   | 股票代码     | 6 位股票代码，例如 `600519`                              |
| `name`                   | 股票简称     | 本地统一简称                                           |
| `full_name`              | 公司全称     | 本地统一公司全称                                         |
| `english_name`           | 英文全称     | 本地统一英文名称                                         |
| `pinyin`                 | 拼音缩写     | 本地统一拼音缩写                                         |
| `exchange`               | 交易所      | `SSE` / `SZSE` / `BSE`                           |
| `board`                  | 上市板块     | 例如主板、创业板、科创板、北交所、CDR                             |
| `industry`               | 所属行业     | 行业分类                                             |
| `region`                 | 所属地区     | 公司地区                                             |
| `currency`               | 交易货币     | 例如 `CNY`                                         |
| `list_date`              | 上市日期     | 格式：`YYYY-MM-DD`                                  |
| `delist_date`            | 退市日期     | 未退市则为空                                           |
| `status`                 | 上市状态     | `listed` / `delisted` / `suspended` / `approved` |
| `is_stock_connect`       | 是否互联互通标的 | 例如沪深港通标记                                         |
| `actual_controller`      | 实控人名称    | 公司实际控制人                                          |
| `controller_entity_type` | 实控人类型    | 实控人主体性质                                          |
| `update_time`            | 更新时间     | 格式：`YYYY-MM-DD HH:MM:SS`                         |

CSV 表头：

```csv
code,name,full_name,english_name,pinyin,exchange,board,industry,region,currency,list_date,delist_date,status,is_stock_connect,actual_controller,controller_entity_type,update_time
```

主键：

```text
code
```

配套原始表：

```text
data/metadata/raw_tushare_stock_basic.csv
```

该文件保存 Tushare `stock_basic` 接口原样字段，只用于追溯、排查和重建主表；生产代码应依赖 `data/metadata/stock_basic.csv`。

原始表头：

```csv
ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type
```

转换关系由 `scripts/metadata/fetch_stock_basic.py` 中的 `convert_tushare_stock_basic` 维护：

| 主表字段                 | Tushare 原始字段          |
| ---------------------- | --------------------- |
| `code`                 | `symbol` / `ts_code`  |
| `name`                 | `name`                |
| `full_name`            | `fullname`            |
| `english_name`         | `enname`              |
| `pinyin`               | `cnspell`             |
| `exchange`             | `exchange`            |
| `board`                | `market`              |
| `industry`             | `industry`            |
| `region`               | `area`                |
| `currency`             | `curr_type`           |
| `list_date`            | `list_date`           |
| `delist_date`          | `delist_date`         |
| `status`               | `list_status` 标准化后 |
| `is_stock_connect`     | `is_hs`               |
| `actual_controller`    | `act_name`            |
| `controller_entity_type` | `act_ent_type`      |

---

试跑建议：

```bash
# 只验证 Tushare token、接口连通性和字段转换，不写任何 CSV 或日志。
python3 a_share_db/scripts/metadata/fetch_stock_basic.py --statuses L --limit 20 --dry-run

# 写一份 20 行样本到临时路径，不覆盖正式主表。
python3 a_share_db/scripts/metadata/fetch_stock_basic.py \
  --statuses L \
  --limit 20 \
  --output /tmp/stock_basic_sample.csv \
  --no-log

# 如需同时保留 Tushare 原始返回，显式增加 --with-raw。
python3 a_share_db/scripts/metadata/fetch_stock_basic.py \
  --statuses L \
  --limit 20 \
  --output /tmp/stock_basic_sample.csv \
  --with-raw \
  --raw-output /tmp/raw_tushare_stock_basic_sample.csv \
  --no-log
```

`stock_basic` 只拉股票基础资料，不拉日线历史行情。`--limit` 只限制本地写出的样本行数；Tushare `stock_basic` 接口本身仍会返回对应上市状态的基础资料集合。

正式刷新时，如果目标 CSV 已存在，脚本默认不备份旧文件，直接用临时文件原子替换：

```text
1. 写完整的新临时文件：{target}.tmp
2. 将新临时文件替换为正式文件
```

如需备份旧文件，可显式加 `--backup`。备份目录可用 `--backup-root` 指定。

---

### 3.2 交易日历表：`data/metadata/trade_calendar.csv`

用途：判断某一天是否为 A 股交易日，避免按自然日错误抓取。

Tushare `trade_cal` 字段是数据源语义：`exchange/cal_date/is_open/pretrade_date`。
正式表使用本地语义，并保留 `exchange`，因为不同交易所交易日历可能不同。

北交所处理规则：

```text
Tushare trade_cal 当前未提供 BSE 参数。
北交所股票在回测或实盘中遇到 exchange=BSE 时，直接复用 SSE 交易日历。
raw_tushare_trade_calendar.csv 只保存 Tushare 实际返回的交易所；正式逻辑层可以按需派生或查询 BSE -> SSE 日历映射。
```

| Field                 | 中文名    | 说明                       |
|-----------------------|---------|--------------------------|
| `exchange`            | 交易所     | `SSE` / `SZSE` 等本地交易所代码 |
| `calendar_date`       | 日历日期    | 格式：`YYYY-MM-DD`          |
| `is_trading_day`      | 是否交易日   | `1` 交易，`0` 休市            |
| `previous_trade_date` | 前一交易日   | 当前日期之前最近一个交易日            |
| `update_time`         | 更新时间    | 格式：`YYYY-MM-DD HH:MM:SS` |

CSV 表头：

```csv
exchange,calendar_date,is_trading_day,previous_trade_date,update_time
```

主键：

```text
exchange + calendar_date
```

配套原始表：

```text
data/metadata/raw_tushare_trade_calendar.csv
```

原始表头：

```csv
exchange,cal_date,is_open,pretrade_date
```

转换关系由 `scripts/metadata/fetch_trade_calendar.py` 中的 `convert_tushare_trade_calendar` 维护：

| 正式表字段              | Tushare 原始字段          |
|----------------------|-----------------------|
| `exchange`           | `exchange`            |
| `calendar_date`      | `cal_date` 标准化后      |
| `is_trading_day`     | `is_open` 标准化后       |
| `previous_trade_date` | `pretrade_date` 标准化后 |

试跑建议：

```bash
# 只验证 Tushare token、接口连通性和字段转换，不写任何 CSV 或日志。
python3 a_share_db/scripts/metadata/fetch_trade_calendar.py \
  --start-date 20260101 \
  --end-date 20260131 \
  --dry-run

# 写一份 1 个月样本到临时路径，不覆盖正式交易日历。
python3 a_share_db/scripts/metadata/fetch_trade_calendar.py \
  --start-date 20260101 \
  --end-date 20260131 \
  --output /tmp/trade_calendar_sample.csv \
  --no-log

# 如需同时保留 Tushare 原始返回，显式增加 --with-raw。
python3 a_share_db/scripts/metadata/fetch_trade_calendar.py \
  --start-date 20260101 \
  --end-date 20260131 \
  --output /tmp/trade_calendar_sample.csv \
  --with-raw \
  --raw-output /tmp/raw_tushare_trade_calendar_sample.csv \
  --no-log
```

默认交易所为 A 股相关的 `SSE SZSE`，因此正式构建时可以只指定年份范围：

```bash
python3 a_share_db/scripts/metadata/fetch_trade_calendar.py \
  --start-date 19900101 \
  --end-date 20271231
```

如果要一次拉取 Tushare 文档列出的全部交易所日历：

```bash
python3 a_share_db/scripts/metadata/fetch_trade_calendar.py \
  --exchanges ALL \
  --start-date 19900101 \
  --end-date 20271231
```

---

### 3.3 日线行情表：`data/market_data/daily/{adjust_type}/{code}.csv`

用途：存储单只股票的日线行情。正式日线价格表分三种复权口径，各自独立成文件：

文件示例：

```text
data/market_data/daily/qfq/600519.csv
data/market_data/daily/none/600519.csv
data/market_data/daily/hfq/600519.csv
```

四张行情相关正式表：

```text
data/market_data/daily/none/{code}.csv      # 未复权日线，来自 Tushare daily 转换
data/market_data/adj_factor/{code}.csv      # 复权因子，来自 Tushare adj_factor 转换
data/market_data/daily/qfq/{code}.csv       # 前复权日线，由 none + adj_factor 本地生成
data/market_data/daily/hfq/{code}.csv       # 后复权日线，由 none + adj_factor 本地生成
```

依赖关系：

```text
daily none + adj_factor -> daily qfq
daily none + adj_factor -> daily hfq
```

不建议把 `none/qfq/hfq` 混在同一行里，也不建议把复权因子塞进日线价格表。复权因子是可复用的基础数据，单独维护便于重建任意截止日的前复权数据。

| Field              | 中文名       | 说明                         |
| ------------------ | --------- | -------------------------- |
| `code`             | 股票代码      | 6 位股票代码                    |
| `name`             | 股票名称      | 股票简称                       |
| `trade_date`       | 交易日期      | 格式：`YYYY-MM-DD`            |
| `open`             | 开盘价       | 当日开盘价                      |
| `high`             | 最高价       | 当日最高价                      |
| `low`              | 最低价       | 当日最低价                      |
| `close`            | 收盘价       | 当日收盘价                      |
| `pre_close`        | 前收盘价      | 上一个交易日收盘价                  |
| `change`           | 涨跌额       | `close - pre_close`        |
| `pct_chg`          | 涨跌幅       | 单位 `%`                     |
| `volume`           | 成交量       | 单位：股                       |
| `amount`           | 成交额       | 单位：元                       |
| `adjust_type`      | 复权类型      | `none` / `qfq` / `hfq`     |
| `update_time`      | 更新时间      | 格式：`YYYY-MM-DD HH:MM:SS`   |

CSV 表头：

```csv
code,name,trade_date,open,high,low,close,pre_close,change,pct_chg,volume,amount,adjust_type,update_time
```

唯一键：

```text
code + trade_date + adjust_type
```

第三方接口返回的原始日线字段如需保留，存放在 raw 文件中，例如：

```text
data/raw/daily/{provider}/{adjust_type}/{code}.csv
```

正式日线表由转换组件写入，转换时可通过 `a_share_db/utils/provider_codes.py` 从 `code + exchange` 生成接口调用需要的 provider code，但 provider code 不落入正式日线表。

Tushare `daily` 字段转换关系：

| 正式表字段      | Tushare daily 原始字段 | 转换规则                         |
|---------------|----------------------|--------------------------------|
| `code`        | `ts_code`            | 去掉交易所后缀                    |
| `name`        | 本地 `stock_basic`    | 用 `code` 关联                   |
| `trade_date`  | `trade_date`         | `YYYYMMDD` -> `YYYY-MM-DD`     |
| `open`        | `open`               | 原值                            |
| `high`        | `high`               | 原值                            |
| `low`         | `low`                | 原值                            |
| `close`       | `close`              | 原值                            |
| `pre_close`   | `pre_close`          | 原值；这是当日涨跌幅基准价             |
| `change`      | `change`             | 原值；也可由 `close - pre_close` 校验 |
| `pct_chg`     | `pct_chg`            | 原值，单位 `%`                   |
| `volume`      | `vol`                | 手 -> 股，乘以 `100`              |
| `amount`      | `amount`             | 千元 -> 元，乘以 `1000`            |
| `adjust_type` | -                    | `none`                         |

Tushare `daily` 不提供流通市值和总市值，因此这两个字段不放在日线价格表中。后续如需要，单独建立估值或市值表。

复权价格计算规则：

```text
none: 使用未复权 open/high/low/close/pre_close

hfq_price_t = none_price_t * adj_factor_t
hfq_pre_close_t = none_pre_close_t * adj_factor_t

qfq_price_t = none_price_t * adj_factor_t / latest_adj_factor
qfq_pre_close_t = none_pre_close_t * adj_factor_t / latest_adj_factor

change = close - pre_close
pct_chg = change / pre_close * 100
```

`latest_adj_factor` 默认取该股票本地数据当前最大交易日期的复权因子。每次新增交易日后，`qfq` 历史价格可能整体变化，因此 `qfq` 文件应按股票重建。

建议构建顺序：

```text
1. 拉取 data/market_data/daily/none/{code}.csv
2. 拉取 data/market_data/adj_factor/{code}.csv
3. 本地生成 data/market_data/daily/qfq/{code}.csv
4. 本地生成 data/market_data/daily/hfq/{code}.csv
```

试跑建议：

```bash
# 未复权日线，先测单只股票和短时间窗口。
python3 a_share_db/scripts/market/fetch_daily.py \
  --codes 600519 \
  --start-date 20260101 \
  --end-date 20260131 \
  --dry-run

# 复权因子，先测同一只股票和同一时间窗口。
python3 a_share_db/scripts/market/fetch_adj_factor.py \
  --codes 600519 \
  --start-date 20260101 \
  --end-date 20260131 \
  --dry-run

# 已经落地 none 和 adj_factor 后，本地生成 qfq/hfq。
python3 a_share_db/scripts/market/build_adjusted_daily.py \
  --codes 600519 \
  --dry-run
```

全市场历史数据建议使用断点续跑和限速：

```bash
# 拉未复权日线。--resume 会跳过已存在且非空的单股票文件。
python3 a_share_db/scripts/market/fetch_daily.py \
  --all-stocks \
  --start-date 19900101 \
  --end-date 20260510 \
  --resume \
  --request-interval 0.13 \
  --progress-every 50 \
  --max-retries 3 \
  --retry-interval 5

# 拉复权因子。
python3 a_share_db/scripts/market/fetch_adj_factor.py \
  --all-stocks \
  --start-date 19900101 \
  --end-date 20260510 \
  --resume \
  --request-interval 0.13 \
  --progress-every 50 \
  --max-retries 3 \
  --retry-interval 5

# 本地生成 qfq/hfq。--resume 会跳过已存在且非空的 qfq/hfq 文件。
python3 a_share_db/scripts/market/build_adjusted_daily.py \
  --all-stocks \
  --resume \
  --progress-every 50
```

批量脚本默认遇到单只股票失败会记录错误并继续处理后续股票；最后返回非 0 退出码并打印失败列表。修复网络或接口问题后，使用同一条命令加 `--resume` 重跑即可继续补齐。若需要调试时遇错立即停止，可加 `--stop-on-error`。

---

### 3.4 复权因子表：`data/market_data/adj_factor/{code}.csv`

用途：保存单只股票的复权因子，作为 `qfq/hfq` 日线表的唯一复权基础。

文件示例：

```text
data/market_data/adj_factor/600519.csv
```

| Field           | 中文名   | 说明                       |
|-----------------|--------|--------------------------|
| `code`          | 股票代码  | 6 位股票代码                  |
| `trade_date`    | 交易日期  | 格式：`YYYY-MM-DD`          |
| `adjust_factor` | 复权因子  | 本地统一字段名                  |
| `update_time`   | 更新时间  | 格式：`YYYY-MM-DD HH:MM:SS` |

CSV 表头：

```csv
code,trade_date,adjust_factor,update_time
```

唯一键：

```text
code + trade_date
```

Tushare `adj_factor` 字段转换关系：

| 正式表字段       | Tushare adj_factor 原始字段 |
|----------------|----------------------------|
| `code`         | `ts_code`                  |
| `trade_date`   | `trade_date`               |
| `adjust_factor` | `adj_factor`              |

原始复权因子如需保留，存放在：

```text
data/raw/adj_factor/tushare/{code}.csv
```

---

### 3.5 每日指标表：`data/market_data/daily_basic/{code}.csv`

用途：保存单只股票每日估值、换手率、股本和市值等基础指标，作为选股、因子研究、容量约束和市值过滤的核心表。

文件示例：

```text
data/market_data/daily_basic/600519.csv
```

| Field                      | 中文名       | 说明                         |
|----------------------------|------------|------------------------------|
| `code`                     | 股票代码      | 6 位股票代码                    |
| `trade_date`               | 交易日期      | 格式：`YYYY-MM-DD`            |
| `close`                    | 收盘价       | 当日收盘价                      |
| `turnover_rate`            | 换手率       | 单位 `%`                      |
| `turnover_rate_free_float` | 自由流通换手率  | 单位 `%`                      |
| `volume_ratio`             | 量比         | 当日量比                        |
| `pe`                       | 市盈率       | 静态 PE；亏损时可为空              |
| `pe_ttm`                   | 滚动市盈率     | TTM PE；亏损时可为空              |
| `pb`                       | 市净率       | PB                           |
| `ps`                       | 市销率       | PS                           |
| `ps_ttm`                   | 滚动市销率     | TTM PS                       |
| `dividend_yield`           | 股息率       | 单位 `%`                      |
| `dividend_yield_ttm`       | 滚动股息率     | 单位 `%`                      |
| `total_shares`             | 总股本       | 单位：股；Tushare 万股 -> 股       |
| `float_shares`             | 流通股本      | 单位：股；Tushare 万股 -> 股       |
| `free_float_shares`        | 自由流通股本   | 单位：股；Tushare 万股 -> 股       |
| `total_market_value`       | 总市值       | 单位：元；Tushare 万元 -> 元       |
| `float_market_value`       | 流通市值      | 单位：元；Tushare 万元 -> 元       |
| `update_time`              | 更新时间      | 格式：`YYYY-MM-DD HH:MM:SS`   |

CSV 表头：

```csv
code,trade_date,close,turnover_rate,turnover_rate_free_float,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dividend_yield,dividend_yield_ttm,total_shares,float_shares,free_float_shares,total_market_value,float_market_value,update_time
```

唯一键：

```text
code + trade_date
```

Tushare `daily_basic` 字段转换关系：

| 正式表字段                  | Tushare daily_basic 原始字段 | 转换规则              |
|---------------------------|------------------------------|----------------------|
| `code`                    | `ts_code`                    | 去掉交易所后缀         |
| `trade_date`              | `trade_date`                 | `YYYYMMDD` -> `YYYY-MM-DD` |
| `close`                   | `close`                      | 原值                 |
| `turnover_rate`           | `turnover_rate`              | 原值，单位 `%`        |
| `turnover_rate_free_float` | `turnover_rate_f`           | 原值，单位 `%`        |
| `volume_ratio`            | `volume_ratio`               | 原值                 |
| `pe`                      | `pe`                         | 原值                 |
| `pe_ttm`                  | `pe_ttm`                     | 原值                 |
| `pb`                      | `pb`                         | 原值                 |
| `ps`                      | `ps`                         | 原值                 |
| `ps_ttm`                  | `ps_ttm`                     | 原值                 |
| `dividend_yield`          | `dv_ratio`                   | 原值，单位 `%`        |
| `dividend_yield_ttm`      | `dv_ttm`                     | 原值，单位 `%`        |
| `total_shares`            | `total_share`                | 万股 -> 股，乘以 `10000` |
| `float_shares`            | `float_share`                | 万股 -> 股，乘以 `10000` |
| `free_float_shares`       | `free_share`                 | 万股 -> 股，乘以 `10000` |
| `total_market_value`      | `total_mv`                   | 万元 -> 元，乘以 `10000` |
| `float_market_value`      | `circ_mv`                    | 万元 -> 元，乘以 `10000` |

原始每日指标如需保留，存放在：

```text
data/raw/daily_basic/tushare/{code}.csv
```

试跑建议：

```bash
python3 a_share_db/scripts/market/fetch_daily_basic.py \
  --codes 600519 \
  --start-date 20260101 \
  --end-date 20260131 \
  --dry-run
```

全市场历史数据建议使用断点续跑和限速：

`daily_basic` 单次请求有行数上限，脚本会在同时传入 `--start-date` 和 `--end-date` 时自动按日期窗口分段请求，并按 `code + trade_date` 合并去重。

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

---

### 3.6 历史分钟行情表：`data/market_data/minute/{frequency}/{adjust_type}/{code}.csv`

用途：存储单只股票的历史分钟 K 线行情。Tushare `stk_mins` 是当前数据来源；另一张参考表提供了更清晰的“K线结束时间”语义，因此本地字段采用 `bar_end_time`。

文件示例：

```text
data/market_data/minute/1m/none/600519.csv
data/market_data/minute/5m/none/600519.csv
data/market_data/minute/1m/qfq/600519.csv
data/market_data/minute/1m/hfq/600519.csv
```

第一阶段先落地 `none` 未复权分钟数据。`qfq/hfq` 目录预留给后续使用日级复权因子本地生成分钟复权数据。

| Field          | 中文名      | 说明                                      |
| -------------- | --------- | ----------------------------------------- |
| `code`         | 股票代码     | 6 位股票代码，例如 `600519`                     |
| `name`         | 股票名称     | 来自本地 `stock_basic.csv`                    |
| `trade_date`   | 交易日期     | 从 `bar_end_time` 派生，格式：`YYYY-MM-DD`       |
| `bar_end_time` | K线结束时间   | 格式：`YYYY-MM-DD HH:MM:SS`                  |
| `frequency`    | K线频率     | `1m` / `5m` / `15m` / `30m` / `60m`        |
| `open`         | 开盘价      | 当前分钟 K 线开盘价                              |
| `high`         | 最高价      | 当前分钟 K 线最高价                              |
| `low`          | 最低价      | 当前分钟 K 线最低价                              |
| `close`        | 收盘价      | 当前分钟 K 线收盘价                              |
| `volume`       | 成交量      | 单位：股；Tushare `stk_mins.vol` 和参考表均为股       |
| `amount`       | 成交额      | 单位：元；Tushare `stk_mins.amount` 和参考表均为元    |
| `adjust_type`  | 复权类型     | `none` / `qfq` / `hfq`；第一阶段只写 `none`       |
| `update_time`  | 更新时间     | 格式：`YYYY-MM-DD HH:MM:SS`                  |

CSV 表头：

```csv
code,name,trade_date,bar_end_time,frequency,open,high,low,close,volume,amount,adjust_type,update_time
```

唯一键：

```text
code + frequency + adjust_type + bar_end_time
```

正式分钟表不保存 `ts_code`、`sh600000`、`symbol`、`secid` 或 provider 名称。第三方代码格式由 `a_share_db/utils/provider_codes.py` 按需生成。

Tushare `stk_mins` 字段转换关系：

| 正式表字段      | Tushare stk_mins 原始字段 | 转换规则                              |
| --------------- | ------------------------ | ------------------------------------- |
| `code`          | `ts_code`                | 去掉交易所后缀                         |
| `name`          | 本地 `stock_basic`        | 用 `code` 关联                         |
| `trade_date`    | `trade_time`             | 取日期部分，格式化为 `YYYY-MM-DD`       |
| `bar_end_time`  | `trade_time`             | 格式化为 `YYYY-MM-DD HH:MM:SS`         |
| `frequency`     | 请求参数 `freq`           | `1min` -> `1m`，`5min` -> `5m` 等       |
| `open`          | `open`                   | 原值                                  |
| `high`          | `high`                   | 原值                                  |
| `low`           | `low`                    | 原值                                  |
| `close`         | `close`                  | 原值                                  |
| `volume`        | `vol`                    | 原值；单位已经是股                       |
| `amount`        | `amount`                 | 原值；单位已经是元                       |
| `adjust_type`   | -                        | `none`                                |

参考表字段转换关系：

| 正式表字段      | 参考表字段      | 转换规则                              |
| --------------- | ------------- | ------------------------------------- |
| `code`          | `股票代码`      | `sh600000` -> `600000`，交易所前缀不落表 |
| `name`          | 本地 `stock_basic` | 用 `code` 关联                      |
| `trade_date`    | `k线结束时间`    | 取日期部分                              |
| `bar_end_time`  | `k线结束时间`    | 原时间格式标准化                         |
| `frequency`     | -             | 文件或导入参数指定，默认可按 `1m` 处理       |
| `open`          | `开盘价`        | 原值                                  |
| `high`          | `最高价`        | 原值                                  |
| `low`           | `最低价`        | 原值                                  |
| `close`         | `收盘价`        | 原值                                  |
| `volume`        | `成交量`        | 原值；单位为股                           |
| `amount`        | `成交额`        | 原值；单位为元                           |
| `adjust_type`   | -             | `none`                                |

分钟行情不放 `pre_close`、`change`、`pct_chg`。这些字段在分钟级别容易因为跨午休、跨日、停牌和集合竞价语义产生歧义，后续策略或指标层可以按需要从 `close` 序列计算。

分钟接口单次最多 8000 行。`fetch_minute.py` 默认读取本地 `trade_calendar.csv`，按频率自动选择每个 request 覆盖的最大安全交易日数：

| 频率 | 安全估算 bar/交易日 | 默认交易日/request | 最大估算行数 |
| ---- | ------------------ | ------------------ | ------------ |
| `1m` | 242                | 33                 | 7986         |
| `5m` | 49                 | 163                | 7987         |
| `15m` | 17                | 470                | 7990         |
| `30m` | 9                 | 888                | 7992         |
| `60m` | 5                 | 1599               | 7995         |

如果本地交易日历不存在，脚本会退回到 `--window-days` 自然日窗口。正常构建前应先生成 `trade_calendar.csv`。

全市场分钟历史拉取时，每只股票的实际开始时间为 `max(命令 start-date, stock_basic.list_date)`，避免对上市前区间发起大量空请求。

原始分钟数据如需保留，存放在：

```text
data/raw/minute/tushare/{frequency}/{code}.csv
```

---

### 3.7 ETL 日志表：`data/logs/etl_log.csv`

用途：记录每次抓取任务的执行情况。

| Field           | 中文名  | 说明                               |
| --------------- | ---- | -------------------------------- |
| `job_name`      | 任务名称 | 例如 `fetch_daily`                 |
| `source`        | 数据来源 | 例如 `tencent`                     |
| `start_time`    | 开始时间 | 任务开始时间                           |
| `end_time`      | 结束时间 | 任务结束时间                           |
| `status`        | 执行状态 | `success` / `failed` / `partial` |
| `row_count`     | 数据行数 | 本次写入或更新的数据行数                     |
| `error_message` | 错误信息 | 失败时记录原因                          |

CSV 表头：

```csv
job_name,source,start_time,end_time,status,row_count,error_message
```

---

### 3.8 更新状态表：`data/logs/update_status.csv`

用途：记录每只股票、每种复权类型已经更新到哪一天，用于增量更新。

| Field              | 中文名    | 说明                               |
| ------------------ | ------ | -------------------------------- |
| `code`             | 股票代码   | 6 位股票代码                          |
| `adjust_type`      | 复权类型   | `none` / `qfq` / `hfq`           |
| `last_trade_date`  | 最后交易日期 | 已更新到的最后交易日                       |
| `last_update_time` | 最后更新时间 | 本地文件最后更新时间                       |
| `status`           | 更新状态   | `success` / `failed` / `pending` |
| `error_message`    | 错误信息   | 失败时记录原因                          |

CSV 表头：

```csv
code,adjust_type,last_trade_date,last_update_time,status,error_message
```

唯一键：

```text
code + adjust_type
```

---

### 3.9 第二代表通用规则

四种落地布局：

| 布局 | 文件 | 断点续跑规则 | 适用 |
| ---- | ---- | ------------ | ---- |
| per-stock | `{table}/{code}.csv` | 跳过已存在且非空的股票文件 | 涨跌停价、资金流向、融资融券、北向持股、分红、股东户数 |
| per-date | `{table}/{year}.csv` | 跳过已完成的年份文件；区间最后一年总是重拉 | 停复牌、ST 名单、龙虎榜、大宗交易、涨跌停统计 |
| per-key | `{table}/{key}.csv` | 跳过已存在的 key 文件；财报周期在 `--refresh-recent-days`（默认 400 天）内总是重拉 | 指数日线/估值/权重、行业指数、财务报表（key = 报告期） |
| single | `{table}.csv` | 无（全表重建） | 元数据、宏观、汇总表 |

通用约定：

```text
所有表的 code 为 6 位股票代码；指数/行业指数使用 Wind 风格带后缀代码（000300.SH、801010.SI），因为纯 6 位代码在不同发布机构之间不唯一。
日期统一 YYYY-MM-DD；股数单位股；金额单位元；比率单位 %。
Tushare 单位换算：手 -> 股 ×100；万股 -> 股 ×10000；千元/万元/百万元/亿元 -> 元。
每行带 update_time。
Tushare 接口普遍支持 offset/limit 分页，fetch_paginated 按接口上限分页，不再依赖日期窗口。
```

### 3.10 交易约束表

| 表 | 文件 | 唯一键 | 来源 | 字段 |
| -- | ---- | ------ | ---- | ---- |
| 涨跌停价 | `market_data/limit_price/{code}.csv` | code + trade_date | `stk_limit`（2007 起） | code, trade_date, limit_up_price, limit_down_price |
| 停复牌 | `market_data/suspend/{year}.csv` | code + trade_date + suspend_type | `suspend_d` 按交易日（1999-05-28 起） | code, trade_date, suspend_timing, suspend_type(`suspend`/`resume`) |
| ST 名单 | `market_data/st_stock/{year}.csv` | code + trade_date | `stock_st` 按交易日（2005 起） | code, name, trade_date, st_type, st_type_name |
| 涨跌停统计 | `market_data/limit_list/{year}.csv` | code + trade_date | `limit_list_d`（2020 起） | 见 `constant/events.py`，limit_type 为 `limit_up`/`limit_down`/`touched` |

`suspend_d` 按股票查询会被截断，所以按交易日抓取；2005 年之前的 ST 状态可从 `stock_name_history` 中名称含 `ST` 推断。

### 3.11 资金与持仓表

| 表 | 文件 | 唯一键 | 来源 | 说明 |
| -- | ---- | ------ | ---- | ---- |
| 个股资金流向 | `market_data/moneyflow/{code}.csv` | code + trade_date | `moneyflow`（2010 起） | 小/中/大/特大单买卖量额与净额；量 股，额 元 |
| 融资融券明细 | `market_data/margin/{code}.csv` | code + trade_date | `margin_detail`（2010 起） | financing_* 融资，lending_* 融券；余额/金额 元，量 股 |
| 融资融券汇总 | `market_data/margin_summary.csv` | exchange + trade_date | `margin` | SSE/SZSE/BSE 合计 |
| 北向持股 | `market_data/stock_connect_hold/{code}.csv` | code + trade_date | `hk_hold`（2016 起） | hold_shares 股，hold_ratio %，connect_market SSE/SZSE |
| 南北向资金 | `market_data/stock_connect_flow.csv` | trade_date | `moneyflow_hsgt`（2014 起） | 百万元 -> 元 |
| 龙虎榜 | `market_data/dragon_tiger_list/{year}.csv` | code + trade_date + reason | `top_list`（2010 起） | 上榜原因、买卖金额 |
| 龙虎榜席位 | `market_data/dragon_tiger_inst/{year}.csv` | code + trade_date + seat_name + side | `top_inst` | 席位买卖 |
| 大宗交易 | `market_data/block_trade/{year}.csv` | code + trade_date + buyer + seller + price | `block_trade`（2010 起） | 万股 -> 股，万元 -> 元 |

### 3.12 元数据扩展表

| 表 | 文件 | 唯一键 | 来源 |
| -- | ---- | ------ | ---- |
| 股票曾用名 | `metadata/stock_name_history.csv` | code + start_date | `namechange` 全市场分页 |
| 上市公司资料 | `metadata/stock_company.csv` | code | `stock_company` 按交易所；registered_capital 万元 -> 元 |
| IPO | `metadata/ipo.csv` | code | `new_share`（2008 起）；万股 -> 股，亿元 -> 元 |
| 沪深港通成分 | `metadata/stock_connect_constituent.csv` | code + connect_market + in_date | `hs_const` SH/SZ × 当前/历史 |
| 指数基础信息 | `metadata/index_basic.csv` | index_code | `index_basic` SSE/SZSE/CSI/SW |
| 申万行业分类 | `metadata/sw_industry.csv` | industry_index_code | `index_classify` SW2021 L1/L2/L3 |
| 申万行业成分 | `metadata/sw_industry_member.csv` | code + l3_code + in_date | `index_member_all` 按 L1 分页；含 in_date/out_date 可做时点行业 |

### 3.13 指数与行业行情表

| 表 | 文件 | 唯一键 | 来源 |
| -- | ---- | ------ | ---- |
| 指数日线 | `market_data/index_daily/{index_code}.csv` | index_code + trade_date | `index_daily`；手 -> 股，千元 -> 元 |
| 指数估值 | `market_data/index_daily_basic/{index_code}.csv` | index_code + trade_date | `index_dailybasic`（2004 起）；万元/万股 -> 元/股 |
| 指数权重 | `market_data/index_weight/{index_code}.csv` | index_code + code + trade_date | `index_weight`（2005 起，按月）；按年窗口 + 分页 |
| 申万行业指数日线 | `market_data/sw_industry_daily/{industry_index_code}.csv` | industry_index_code + trade_date | `sw_daily`（2012 起）；万股/万元 -> 股/元 |

默认基准指数与权重指数列表在 `constant/index.py`（上证综指、上证50、沪深300、中证500/800/1000/2000/全指、科创50、深证成指、创业板指、国证2000、北证50 等）。

### 3.14 财务数据表

财务报表按报告期落地：`financial/{table}/{period}.csv`，period 为 `YYYYMMDD` 季末日期。所有表带 `announce_date`（首次公告日）以支持 point-in-time 使用，三大报表另带 `actual_announce_date`（实际公告日，含更正）。

| 表 | 文件 | 唯一键 | 来源 |
| -- | ---- | ------ | ---- |
| 利润表 | `financial/income/{period}.csv` | code + report_period + statement_type + actual_announce_date | `income_vip` |
| 资产负债表 | `financial/balance_sheet/{period}.csv` | 同上 | `balancesheet_vip` |
| 现金流量表 | `financial/cash_flow/{period}.csv` | 同上 | `cashflow_vip` |
| 财务指标 | `financial/indicator/{period}.csv` | code + report_period + announce_date | `fina_indicator_vip` |
| 业绩预告 | `financial/forecast/{period}.csv` | code + report_period + announce_date + forecast_type | `forecast_vip` |
| 业绩快报 | `financial/express/{period}.csv` | code + report_period + announce_date | `express_vip` |
| 财报披露日期 | `financial/disclosure_date/{period}.csv` | code + report_period | `disclosure_date` |
| 前十大股东 | `financial/top10_holders/{period}.csv` | code + report_period + announce_date + holder_name | `top10_holders` |
| 前十大流通股东 | `financial/top10_float_holders/{period}.csv` | 同上 | `top10_floatholders` |
| 分红送股 | `financial/dividend/{code}.csv` | code + report_period + announce_date + process | `dividend`；base_shares 万股 -> 股 |
| 股东户数 | `financial/holder_number/{code}.csv` | code + report_period + announce_date | `stk_holdernumber` |

约定：

```text
statement_type 默认只抓 consolidated（Tushare report_type=1，合并报表）；可用 --report-types 扩展。
company_type：general / bank / insurance / securities。
Tushare vip 接口会重复返回同一份报表，转换时按唯一键去重并优先保留 is_update=1 的行。
三大报表与财务指标共约 450 个字段，本地字段名的映射见 constant/financial.py，不在此逐一列出。
```

### 3.15 宏观表

| 表 | 文件 | 唯一键 | 来源 |
| -- | ---- | ------ | ---- |
| Shibor | `macro/shibor.csv` | rate_date | `shibor`（2006 起，按 5 年窗口分页） |
| GDP | `macro/gdp.csv` | quarter | `cn_gdp` |
| CPI | `macro/cpi.csv` | month | `cn_cpi` |
| PPI | `macro/ppi.csv` | month | `cn_ppi` |
| 货币供应量 | `macro/money_supply.csv` | month | `cn_m` |

### 3.16 第二代表的构建与增量

```text
全量构建：python3 a_share_db/scripts/workflows/build_extended_history.py
按组构建：--groups metadata index financial stock daily
单表重建：调用对应 scripts/*/fetch_*.py，加 --resume 可续跑
Parquet：python3 a_share_db/scripts/warehouse/build_parquet.py --tables extended --resume
```

增量更新策略（已实现，统一入口 `scripts/workflows/refresh_all.py`，非交易日自动跳过）：

```text
per-date 表：从本地最大年份文件重拉当年即可（同 --resume 行为）。
per-key 财务表：--resume 会自动重拉最近 400 天内结束的报告期。
per-stock 表：--update 按本地最大 trade_date+1 增量合并（limit_price/moneyflow/margin/stock_connect_hold）；dividend/holder_number 无日期过滤，全量刷新。
single 表：直接重跑全表。
指数类 per-key 表：--update 全量重拉（文件小）。
分钟表：fetch_minute --update 只读文件尾部取最后 bar_end_time，追加新 bar，不重写大文件。
退市股：所有按股票循环的脚本支持 --statuses，默认 listed；--statuses delisted 回填退市股。
```

---

## 4. 代码格式规范

固定常量管理：

```text
字段列表、枚举映射、默认交易所列表等固定常量统一放在 a_share_db/constant/。
一个文件只维护一类领域常量，例如 stock_basic.py 只维护股票基础信息相关常量。
scripts/ 下的 ETL 脚本只能引用这些常量，不在脚本内部重复定义字段列表。
```

当前常量文件：

| 文件                          | 用途                         |
|-----------------------------|----------------------------|
| `constant/stock_basic.py`   | 股票基础信息字段、Tushare 字段、上市状态映射 |
| `constant/daily.py`         | 日线行情字段、复权因子字段、复权类型       |
| `constant/minute.py`        | 分钟行情字段、分钟频率、provider 频率映射 |
| `constant/trade_calendar.py` | 交易日历字段、Tushare 字段、默认交易所列表 |
| `constant/paths.py`         | 数据目录和正式文件路径常量              |
| `constant/warehouse.py`     | Parquet/DuckDB 数据层相关常量；`EXTENDED_PARQUET_TABLES` 注册第二代表的列、文本列、日期列和路径 |
| `constant/commands.py`      | 常用 wrapper 命令默认参数            |
| `constant/limit_price.py`   | 涨跌停价字段                        |
| `constant/suspend.py`       | 停复牌字段与类型映射                 |
| `constant/st_stock.py`      | ST/风险警示名单字段                  |
| `constant/name_change.py`   | 股票曾用名字段                      |
| `constant/stock_company.py` | 上市公司资料字段映射                 |
| `constant/ipo.py`           | IPO 字段与单位                      |
| `constant/stock_connect.py` | 沪深港通成分、北向持股、南北向资金字段 |
| `constant/moneyflow.py`     | 个股资金流向字段映射与单位           |
| `constant/margin.py`        | 融资融券明细与汇总字段映射           |
| `constant/index.py`         | 指数基础/日线/估值/权重字段，默认基准指数列表 |
| `constant/industry.py`      | 申万行业分类、成分、行业指数日线字段   |
| `constant/events.py`        | 龙虎榜、大宗交易、涨跌停统计字段映射   |
| `constant/holders.py`       | 股东户数、前十大股东字段             |
| `constant/financial.py`     | 利润表/资产负债表/现金流量表/财务指标/预告/快报/分红/披露日期字段映射 |
| `constant/macro.py`         | Shibor、GDP、CPI、PPI、货币供应量字段映射 |

第二代脚本的复用规则：

```text
scripts/ 下的第二代抓取脚本只负责：定义 provider 请求、调用 convert_mapped_frame 转换、解析命令行。
分页（fetch_paginated）、重试、进度、断点续跑、原子写入、ETL 日志统一由 utils/etl_runners.py 提供。
字段映射 dict（provider 字段 -> 本地字段）是唯一事实来源；TUSHARE_*_FIELDS 和 *_COLUMNS 由它派生。
```

脚本组织规则：

```text
仓库根目录不放 Python 脚本。
所有可执行命令放在 a_share_db/scripts/ 下，并按 metadata、market、workflows、warehouse 等目录分组。
包内复用逻辑放在 a_share_db/utils/ 或未来更具体的包目录中。
```

代码注释规则：

```text
新增或修改 Python 代码时必须写必要的英文注释。
注释要解释代码逻辑、业务意义或非显而易见的取舍，不做逐行翻译。
__init__.py 这类默认空文件不需要注释。
```

不同数据源使用不同代码格式。主表只保存本地标准字段 `code` 和 `exchange`，第三方代码格式由 `a_share_db/utils/provider_codes.py` 按需转换。

| Field    | 示例         | 用途        |
| -------- | ---------- | --------- |
| `code`   | `600519`   | 本地统一主键    |
| `exchange` | `SSE`   | 本地交易所代码    |

转换输出示例：

| 转换函数                     | 示例         | 用途        |
| -------------------------- | ---------- | --------- |
| `build_sina_symbol`        | `sh600519` | 新浪接口      |
| `build_tencent_symbol`     | `sh600519` | 腾讯接口      |
| `build_eastmoney_secid`    | `1.600519` | 东方财富接口    |

映射规则：

| 股票代码开头      | `exchange` | `symbol` 前缀 | `secid` 前缀 |
| ----------- | ---------- | ----------- | ---------- |
| `60` / `68` | `SSE`      | `sh`        | `1.`       |
| `00` / `30` | `SZSE`     | `sz`        | `0.`       |
| `8` / `4`   | `BSE`      | `bj`        | 视数据源而定     |

---

## 5. 增量更新流程

```text
1. 更新 stock_basic.csv
2. 更新 trade_calendar.csv
3. 判断今天是否为交易日
4. 对每只股票读取 data/market_data/daily/none/{code}.csv 的最大 trade_date
5. 从 max(trade_date)+1 到 end_date 抓取 Tushare daily
6. 读取旧 none 文件，与新增数据按 code + trade_date 合并去重
7. 用临时文件原子替换原 none 文件；只有显式传入 `--backup` 时才备份旧文件
8. 同步更新 data/market_data/adj_factor/{code}.csv，复权因子起点按复权因子文件自己的最大 trade_date 计算
9. 默认增量合并 data/market_data/daily/hfq/{code}.csv 的缺失交易日
10. qfq 默认不在每日增量中重建；需要时手动或周期性通过 build_adjusted_daily.py 重建
11. 写入 etl_log.csv
```

增量更新以每个股票本地 CSV 的最大 `trade_date` 为准，不依赖全局“上次运行时间”。这样某只股票中途失败时，下一次重跑会只补这只股票缺失的区间。

`hfq` 可以按缺失交易日增量合并：

```text
hfq_price_t = none_price_t * adj_factor_t
```

历史 `hfq` 行不依赖最新交易日，因此每日更新可以只补新交易日。

`qfq` 默认不在每日增量中物理重建：

```text
qfq_price_t = none_price_t * adj_factor_t / latest_adj_factor
```

`latest_adj_factor` 改变时，历史 `qfq` 行可能整体变化，因此 `qfq` 应通过 `build_adjusted_daily.py` 手动或周期性重建，或在分析时由 `none + adj_factor` 动态生成。

示例：

```bash
python3 a_share_db/scripts/market/update_daily.py \
  --all-stocks \
  --end-date 20260510 \
  --request-interval 0.13 \
  --progress-every 50 \
  --max-retries 3 \
  --retry-interval 5
```

---

## 6. 常用一键命令

常用命令以薄 wrapper 的方式实现，只封装默认参数，业务逻辑必须复用已有 ETL 函数。

每天更新数据库：

```bash
python3 a_share_db/scripts/workflows/update_daily_data.py
```

默认行为：

```text
1. 更新 daily/none
2. 更新 adj_factor
3. 增量合并 daily/hfq
4. 不重建 daily/qfq
```

手动或周期性重建 qfq/hfq：

```bash
python3 a_share_db/scripts/workflows/rebuild_adjusted_daily_data.py
```

刷新股票主表和交易日历：

```bash
python3 a_share_db/scripts/metadata/refresh_metadata.py
```

这些 wrapper 可以保留少量参数用于 dry-run、覆盖结束日期、调整进度输出等，但直接运行时必须采用项目默认配置。

---

## 7. 命令行进度显示约定

长时间运行的命令必须复用 `a_share_db.utils.progress.ProgressReporter`，并提供 `--progress-every` 参数。

进度输出至少包含：

```text
current/total, percent, elapsed, eta, rows, skipped, failed
```

默认建议每 50 只股票输出一次：

```bash
--progress-every 50
```

需要更频繁时可以用 `--progress-every 10`；需要关闭时用 `--progress-every 0`。

---

## 8. 代码复用约定

任何可以跨脚本复用的逻辑都应该单独实现为包内模块，而不是复制到每个 `scripts/` 命令文件里。

适合抽离的逻辑包括：

```text
进度显示、日期格式化、文件原子写入、备份路径生成、CSV 合并去重、股票选择、provider code 转换、ETL 日志写入
```

脚本层职责应尽量保持为：

```text
解析 CLI 参数 -> 调用复用模块/ETL 函数 -> 打印执行结果
```

现有示例：

```text
a_share_db/utils/progress.py        # 长任务进度输出
a_share_db/utils/provider_codes.py  # 第三方代码格式转换
a_share_db/constant/commands.py     # 一键命令默认参数
a_share_db/constant/*.py            # 字段、路径、枚举等常量
```

---

## 9. 第一阶段 MVP

第一阶段只实现以下文件：

```text
data/metadata/stock_basic.csv
data/metadata/raw_tushare_stock_basic.csv
data/metadata/raw_tushare_trade_calendar.csv
data/metadata/trade_calendar.csv
data/market_data/daily/none/{code}.csv
data/market_data/adj_factor/{code}.csv
data/market_data/daily_basic/{code}.csv
data/market_data/daily/qfq/{code}.csv
data/market_data/daily/hfq/{code}.csv
data/market_data/minute/{frequency}/none/{code}.csv
data/logs/etl_log.csv
data/logs/update_status.csv
```

优先级：

```text
P0: stock_basic.csv
P0: raw_tushare_stock_basic.csv
P0: raw_tushare_trade_calendar.csv
P0: trade_calendar.csv
P0: none daily data
P0: adj_factor data
P0: daily_basic data
P0: qfq daily data
P0: hfq daily data
P1: none minute data
P0: update_status.csv
P2: financials / announcements / valuation
```

---

## 10. 后续扩展

后续可扩展模块：

```text
valuation/
financials/
corporate_actions/
announcements/
data/raw/
```

其中：

| 模块                  | 说明                |
| ------------------- | ----------------- |
| `valuation`         | PE、PB、市值、股息率等估值数据 |
| `financials`        | 利润表、资产负债表、现金流量表   |
| `corporate_actions` | 分红、送转、配股、复权因子     |
| `announcements`     | 公告、年报、PDF 文件      |
| `raw`               | 原始接口返回数据备份        |

```
```
