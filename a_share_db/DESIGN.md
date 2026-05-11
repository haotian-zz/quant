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
├── metadata/
│   ├── stock_basic.csv
│   ├── raw_tushare_stock_basic.csv
│   ├── raw_tushare_trade_calendar.csv
│   └── trade_calendar.csv
│
├── market_data/
│   └── daily/
│       ├── none/
│       ├── qfq/
│       └── hfq/
│
├── raw/
│   └── daily/
│       └── {provider}/
│           └── {adjust_type}/
│
├── backups/
│   └── {timestamp}/
│
├── logs/
│   ├── etl_log.csv
│   └── update_status.csv
│
├── constant/
│   ├── stock_basic.py
│   └── trade_calendar.py
│
└── scripts/
    ├── provider_codes.py
    ├── fetch_stock_basic.py
    ├── fetch_trade_calendar.py
    ├── fetch_daily.py
    └── update_all.py
```

---

## 3. 数据文件设计

正式数据表设计原则：

```text
metadata/stock_basic.csv、metadata/trade_calendar.csv、market_data/daily/* 都是本地维护的正式表。
正式表字段必须使用本地领域语义，不保存第三方接口字段名、第三方代码格式或数据源标记。
第三方原始字段、原始代码、接口来源只允许出现在 raw_* 文件或 ETL 日志中。
第三方接口调用需要的 symbol、secid 等标识由 scripts/provider_codes.py 按需生成。
```

### 3.1 股票基础信息表：`metadata/stock_basic.csv`

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
metadata/raw_tushare_stock_basic.csv
```

该文件保存 Tushare `stock_basic` 接口原样字段，只用于追溯、排查和重建主表；生产代码应依赖 `metadata/stock_basic.csv`。

原始表头：

```csv
ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type
```

转换关系由 `scripts/fetch_stock_basic.py` 中的 `convert_tushare_stock_basic` 维护：

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
python3 a_share_db/scripts/fetch_stock_basic.py --statuses L --limit 20 --dry-run

# 写一份 20 行样本到临时路径，不覆盖正式主表。
python3 a_share_db/scripts/fetch_stock_basic.py \
  --statuses L \
  --limit 20 \
  --output /tmp/stock_basic_sample.csv \
  --no-log

# 如需同时保留 Tushare 原始返回，显式增加 --with-raw。
python3 a_share_db/scripts/fetch_stock_basic.py \
  --statuses L \
  --limit 20 \
  --output /tmp/stock_basic_sample.csv \
  --with-raw \
  --raw-output /tmp/raw_tushare_stock_basic_sample.csv \
  --no-log
```

`stock_basic` 只拉股票基础资料，不拉日线历史行情。`--limit` 只限制本地写出的样本行数；Tushare `stock_basic` 接口本身仍会返回对应上市状态的基础资料集合。

正式刷新时，如果目标 CSV 已存在，脚本默认先备份旧文件，再替换为新文件：

```text
1. 写完整的新临时文件：{target}.tmp
2. 将旧正式文件移动到 backups/{timestamp}/...
3. 将新临时文件替换为正式文件
4. 如果替换失败且旧文件已备份，自动恢复旧正式文件
```

如需关闭备份，可加 `--no-backup`。备份目录可用 `--backup-root` 指定。

---

### 3.2 交易日历表：`metadata/trade_calendar.csv`

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
metadata/raw_tushare_trade_calendar.csv
```

原始表头：

```csv
exchange,cal_date,is_open,pretrade_date
```

转换关系由 `scripts/fetch_trade_calendar.py` 中的 `convert_tushare_trade_calendar` 维护：

| 正式表字段              | Tushare 原始字段          |
|----------------------|-----------------------|
| `exchange`           | `exchange`            |
| `calendar_date`      | `cal_date` 标准化后      |
| `is_trading_day`     | `is_open` 标准化后       |
| `previous_trade_date` | `pretrade_date` 标准化后 |

试跑建议：

```bash
# 只验证 Tushare token、接口连通性和字段转换，不写任何 CSV 或日志。
python3 a_share_db/scripts/fetch_trade_calendar.py \
  --start-date 20260101 \
  --end-date 20260131 \
  --dry-run

# 写一份 1 个月样本到临时路径，不覆盖正式交易日历。
python3 a_share_db/scripts/fetch_trade_calendar.py \
  --start-date 20260101 \
  --end-date 20260131 \
  --output /tmp/trade_calendar_sample.csv \
  --no-log

# 如需同时保留 Tushare 原始返回，显式增加 --with-raw。
python3 a_share_db/scripts/fetch_trade_calendar.py \
  --start-date 20260101 \
  --end-date 20260131 \
  --output /tmp/trade_calendar_sample.csv \
  --with-raw \
  --raw-output /tmp/raw_tushare_trade_calendar_sample.csv \
  --no-log
```

默认交易所为 A 股相关的 `SSE SZSE`，因此正式构建时可以只指定年份范围：

```bash
python3 a_share_db/scripts/fetch_trade_calendar.py \
  --start-date 19900101 \
  --end-date 20271231
```

如果要一次拉取 Tushare 文档列出的全部交易所日历：

```bash
python3 a_share_db/scripts/fetch_trade_calendar.py \
  --exchanges ALL \
  --start-date 19900101 \
  --end-date 20271231
```

---

### 3.3 日线行情表：`market_data/daily/{adjust_type}/{code}.csv`

用途：存储单只股票的日线行情。

文件示例：

```text
market_data/daily/qfq/600519.csv
market_data/daily/none/600519.csv
market_data/daily/hfq/600519.csv
```

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
| `amplitude`        | 振幅        | 单位 `%`                     |
| `turnover`         | 换手率       | 单位 `%`                     |
| `free_market_cap`  | 流通市值      | 单位：元                       |
| `total_market_cap` | 总市值       | 单位：元                       |
| `adjust_type`      | 复权类型      | `none` / `qfq` / `hfq`     |
| `update_time`      | 更新时间      | 格式：`YYYY-MM-DD HH:MM:SS`   |

CSV 表头：

```csv
code,name,trade_date,open,high,low,close,pre_close,change,pct_chg,volume,amount,amplitude,turnover,free_market_cap,total_market_cap,adjust_type,update_time
```

唯一键：

```text
code + trade_date + adjust_type
```

第三方接口返回的原始日线字段如需保留，存放在 raw 文件中，例如：

```text
raw/daily/{provider}/{adjust_type}/{code}.csv
```

正式日线表由转换组件写入，转换时可通过 `scripts/provider_codes.py` 从 `code + exchange` 生成接口调用需要的 provider code，但 provider code 不落入正式日线表。

---

### 3.4 ETL 日志表：`logs/etl_log.csv`

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

### 3.5 更新状态表：`logs/update_status.csv`

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
| `constant/trade_calendar.py` | 交易日历字段、Tushare 字段、默认交易所列表 |

不同数据源使用不同代码格式。主表只保存本地标准字段 `code` 和 `exchange`，第三方代码格式由 `scripts/provider_codes.py` 按需转换。

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
4. 读取 update_status.csv
5. 找到每只股票的 last_trade_date
6. 从下一个交易日开始抓取日线数据
7. 写入 market_data/daily/{adjust_type}/{code}.csv
8. 按 code + trade_date + adjust_type 去重
9. 按 trade_date 升序排序
10. 更新 update_status.csv
11. 写入 etl_log.csv
```

---

## 6. 第一阶段 MVP

第一阶段只实现以下文件：

```text
metadata/stock_basic.csv
metadata/raw_tushare_stock_basic.csv
metadata/raw_tushare_trade_calendar.csv
metadata/trade_calendar.csv
market_data/daily/qfq/{code}.csv
logs/etl_log.csv
logs/update_status.csv
```

优先级：

```text
P0: stock_basic.csv
P0: raw_tushare_stock_basic.csv
P0: raw_tushare_trade_calendar.csv
P0: trade_calendar.csv
P0: qfq daily data
P0: update_status.csv
P1: none / hfq daily data
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
raw/
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
