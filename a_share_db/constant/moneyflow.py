"""Constants for per-stock order-size money flow data."""

# Each provider pair is (volume in 手, amount in 万元) for one order-size bucket.
TUSHARE_MONEYFLOW_FIELDS = [
    "ts_code",
    "trade_date",
    "buy_sm_vol",
    "buy_sm_amount",
    "sell_sm_vol",
    "sell_sm_amount",
    "buy_md_vol",
    "buy_md_amount",
    "sell_md_vol",
    "sell_md_amount",
    "buy_lg_vol",
    "buy_lg_amount",
    "sell_lg_vol",
    "sell_lg_amount",
    "buy_elg_vol",
    "buy_elg_amount",
    "sell_elg_vol",
    "sell_elg_amount",
    "net_mf_vol",
    "net_mf_amount",
]

# Local names spell out the bucket; volumes are in 股 and amounts in 元.
TUSHARE_MONEYFLOW_FIELD_MAP = {
    "buy_sm_vol": "buy_small_volume",
    "buy_sm_amount": "buy_small_amount",
    "sell_sm_vol": "sell_small_volume",
    "sell_sm_amount": "sell_small_amount",
    "buy_md_vol": "buy_medium_volume",
    "buy_md_amount": "buy_medium_amount",
    "sell_md_vol": "sell_medium_volume",
    "sell_md_amount": "sell_medium_amount",
    "buy_lg_vol": "buy_large_volume",
    "buy_lg_amount": "buy_large_amount",
    "sell_lg_vol": "sell_large_volume",
    "sell_lg_amount": "sell_large_amount",
    "buy_elg_vol": "buy_extra_large_volume",
    "buy_elg_amount": "buy_extra_large_amount",
    "sell_elg_vol": "sell_extra_large_volume",
    "sell_elg_amount": "sell_extra_large_amount",
    "net_mf_vol": "net_volume",
    "net_mf_amount": "net_amount",
}

MONEYFLOW_COLUMNS = ["code", "trade_date"] + list(TUSHARE_MONEYFLOW_FIELD_MAP.values()) + ["update_time"]

TUSHARE_MONEYFLOW_VOLUME_TO_LOCAL = 100
TUSHARE_MONEYFLOW_AMOUNT_TO_LOCAL = 10000

DEFAULT_MONEYFLOW_START_DATE = "20100101"
MONEYFLOW_PAGE_SIZE = 4000
