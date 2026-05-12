````markdown
# A 股 CSV 数据库 LLD

## 1. 目标

从 0 构建一个本地 A 股数据仓库，第一阶段使用 CSV 存储，先跑通：

```text
股票基础信息 → 交易日历 → 日线行情 → 增量更新 → 日志记录
````

后续如需要复杂查询，再迁移到 SQLite / DuckDB / PostgreSQL。

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
│   │   └── adj_factor/
│   │
│   ├── raw/
│   │   ├── daily/
│   │   │   └── {provider}/
│   │   │       └── {adjust_type}/
│   │   └── adj_factor/
│   │       └── {provider}/
│   │
│   ├── backups/
│   │   └── {timestamp}/
│   │
│   └── logs/
│       ├── etl_log.csv
│       └── update_status.csv
│
├── constant/
│   ├── stock_basic.py
│   ├── daily.py
│   ├── trade_calendar.py
│   └── commands.py
│
├── utils/
│   ├── progress.py
│   └── provider_codes.py
│
└── scripts/
    ├── metadata/
    │   ├── fetch_stock_basic.py
    │   ├── fetch_trade_calendar.py
    │   └── refresh_metadata.py
    ├── market/
    │   ├── fetch_adj_factor.py
    │   ├── fetch_daily.py
    │   ├── build_adjusted_daily.py
    │   └── update_daily.py
    ├── workflows/
    │   ├── update_daily_data.py
    │   └── rebuild_adjusted_daily_data.py
```

---

## 3. 数据文件设计

正式数据表设计原则：

```text
data/metadata/stock_basic.csv、data/metadata/trade_calendar.csv、data/market_data/daily/* 都是本地维护的正式表。
正式表字段必须使用本地领域语义，不保存第三方接口字段名、第三方代码格式或数据源标记。
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

### 3.5 ETL 日志表：`data/logs/etl_log.csv`

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

### 3.6 更新状态表：`data/logs/update_status.csv`

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
| `constant/trade_calendar.py` | 交易日历字段、Tushare 字段、默认交易所列表 |

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
data/market_data/daily/qfq/{code}.csv
data/market_data/daily/hfq/{code}.csv
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
P0: qfq daily data
P0: hfq daily data
P0: update_status.csv
P2: financials / announcements / valuation
```

---

## 7. 后续扩展

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
