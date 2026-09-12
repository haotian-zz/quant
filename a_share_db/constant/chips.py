"""Constants for chip distribution summary (cyq_perf), covered from 2018."""

TUSHARE_CHIP_PERF_FIELD_MAP = {
    "ts_code": "code",
    "trade_date": "trade_date",
    "his_low": "historical_low",
    "his_high": "historical_high",
    "cost_5pct": "cost_5pct",
    "cost_15pct": "cost_15pct",
    "cost_50pct": "cost_50pct",
    "cost_85pct": "cost_85pct",
    "cost_95pct": "cost_95pct",
    "weight_avg": "weighted_average_cost",
    "winner_rate": "winner_rate",
}
CHIP_PERF_COLUMNS = list(TUSHARE_CHIP_PERF_FIELD_MAP.values()) + ["update_time"]
DEFAULT_CHIP_PERF_START_DATE = "20180102"
CHIP_PERF_PAGE_SIZE = 4000
