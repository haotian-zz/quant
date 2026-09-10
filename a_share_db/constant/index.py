"""Constants for market index metadata, quotes, valuation and weights.

Local index identifiers follow the Wind-style convention `{code}.{suffix}`
(for example 000300.SH, 399006.SZ, 932000.CSI, 801010.SI). This is the common
industry convention rather than a provider-specific format, and it is needed
because the six-digit part alone is not unique across publishers.
"""

TUSHARE_INDEX_BASIC_FIELDS = [
    "ts_code",
    "name",
    "fullname",
    "market",
    "publisher",
    "index_type",
    "category",
    "base_date",
    "base_point",
    "list_date",
    "weight_rule",
    "desc",
    "exp_date",
]

INDEX_BASIC_COLUMNS = [
    "index_code",
    "name",
    "full_name",
    "market",
    "publisher",
    "index_type",
    "category",
    "base_date",
    "base_point",
    "list_date",
    "weight_rule",
    "description",
    "expire_date",
    "update_time",
]

# index_basic is queried per market; MSCI and others return nothing for this token.
INDEX_BASIC_MARKETS = ["SSE", "SZSE", "CSI", "SW", "CICC", "OTH"]
INDEX_BASIC_PAGE_SIZE = 8000

TUSHARE_INDEX_DAILY_FIELDS = [
    "ts_code",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "change",
    "pct_chg",
    "vol",
    "amount",
]

INDEX_DAILY_COLUMNS = [
    "index_code",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "change",
    "pct_chg",
    "volume",
    "amount",
    "update_time",
]

# index_daily uses the same units as stock daily: vol in 手 and amount in 千元.
TUSHARE_INDEX_VOLUME_TO_LOCAL = 100
TUSHARE_INDEX_AMOUNT_TO_LOCAL = 1000
INDEX_DAILY_PAGE_SIZE = 6000

TUSHARE_INDEX_DAILY_BASIC_FIELDS = [
    "ts_code",
    "trade_date",
    "total_mv",
    "float_mv",
    "total_share",
    "float_share",
    "free_share",
    "turnover_rate",
    "turnover_rate_f",
    "pe",
    "pe_ttm",
    "pb",
]

INDEX_DAILY_BASIC_COLUMNS = [
    "index_code",
    "trade_date",
    "total_market_value",
    "float_market_value",
    "total_shares",
    "float_shares",
    "free_float_shares",
    "turnover_rate",
    "turnover_rate_free_float",
    "pe",
    "pe_ttm",
    "pb",
    "update_time",
]

# index_dailybasic reports 万元 and 万股, matching daily_basic conversions.
TUSHARE_INDEX_MARKET_VALUE_TO_LOCAL = 10000
TUSHARE_INDEX_SHARE_TO_LOCAL = 10000
INDEX_DAILY_BASIC_PAGE_SIZE = 2500

TUSHARE_INDEX_WEIGHT_FIELDS = [
    "index_code",
    "con_code",
    "trade_date",
    "weight",
]

INDEX_WEIGHT_COLUMNS = [
    "index_code",
    "code",
    "trade_date",
    "weight",
    "update_time",
]

INDEX_WEIGHT_PAGE_SIZE = 5000
# Weight snapshots are monthly; one-year windows keep pages small and resumable.
INDEX_WEIGHT_WINDOW_CALENDAR_DAYS = 366

# Benchmarks and universes most A-share strategies need. Quotes are fetched for
# all of them; weights only where the index defines a tradable universe.
DEFAULT_INDEX_DAILY_CODES = [
    "000001.SH",  # 上证综指
    "000016.SH",  # 上证50
    "000300.SH",  # 沪深300
    "000905.SH",  # 中证500
    "000852.SH",  # 中证1000
    "932000.CSI",  # 中证2000
    "000906.SH",  # 中证800
    "000985.CSI",  # 中证全指
    "000688.SH",  # 科创50
    "000903.SH",  # 中证100
    "399001.SZ",  # 深证成指
    "399005.SZ",  # 中小100
    "399006.SZ",  # 创业板指
    "399303.SZ",  # 国证2000
    "399330.SZ",  # 深证100
    "899050.BJ",  # 北证50
]

DEFAULT_INDEX_WEIGHT_CODES = [
    "000016.SH",
    "000300.SH",
    "000905.SH",
    "000852.SH",
    "932000.CSI",
    "000906.SH",
    "000985.CSI",
    "000688.SH",
    "399006.SZ",
    "399303.SZ",
]

DEFAULT_INDEX_START_DATE = "19901219"
DEFAULT_INDEX_DAILY_BASIC_START_DATE = "20040101"
DEFAULT_INDEX_WEIGHT_START_DATE = "20050101"
