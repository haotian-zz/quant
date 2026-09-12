"""Constants for public fund tables (ETF quotes, NAV, shares, holdings).

Fund codes keep the Wind-style suffix (510300.SH, 000001.OF).
"""

TUSHARE_FUND_BASIC_FIELD_MAP = {
    "ts_code": "fund_code",
    "name": "name",
    "management": "manager_company",
    "custodian": "custodian",
    "fund_type": "fund_type",
    "found_date": "found_date",
    "due_date": "due_date",
    "list_date": "list_date",
    "issue_date": "issue_date",
    "delist_date": "delist_date",
    "issue_amount": "issue_amount",
    "m_fee": "management_fee",
    "c_fee": "custodian_fee",
    "duration_year": "duration_years",
    "p_value": "par_value",
    "min_amount": "min_subscription_amount",
    "exp_return": "expected_return",
    "benchmark": "benchmark",
    "status": "status",
    "invest_type": "investment_type",
    "type": "type",
    "trustee": "trustee",
    "purc_startdate": "purchase_start_date",
    "redm_startdate": "redemption_start_date",
    "market": "market",
}
FUND_BASIC_COLUMNS = list(TUSHARE_FUND_BASIC_FIELD_MAP.values()) + ["update_time"]
# issue_amount is provider 亿份 -> 份.
FUND_BASIC_SCALES = {"issue_amount": 100_000_000}
FUND_MARKETS = ["E", "O"]
FUND_BASIC_PAGE_SIZE = 5000

# ETF-style daily quotes (fund_daily): vol 手 -> 份 (x100), amount 千元 -> 元.
TUSHARE_FUND_DAILY_FIELD_MAP = {
    "ts_code": "fund_code",
    "trade_date": "trade_date",
    "pre_close": "pre_close",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "change": "change",
    "pct_chg": "pct_chg",
    "vol": "volume",
    "amount": "amount",
}
FUND_DAILY_COLUMNS = list(TUSHARE_FUND_DAILY_FIELD_MAP.values()) + ["update_time"]
FUND_DAILY_SCALES = {"vol": 100, "amount": 1000}

TUSHARE_FUND_NAV_FIELD_MAP = {
    "ts_code": "fund_code",
    "ann_date": "announce_date",
    "nav_date": "nav_date",
    "unit_nav": "unit_nav",
    "accum_nav": "accumulated_nav",
    "accum_div": "accumulated_dividend",
    "net_asset": "net_assets",
    "adj_nav": "adjusted_nav",
    "update_flag": "is_update",
}
FUND_NAV_COLUMNS = list(TUSHARE_FUND_NAV_FIELD_MAP.values()) + ["update_time"]

# fd_share is provider 万份 -> 份.
TUSHARE_FUND_SHARE_FIELD_MAP = {
    "ts_code": "fund_code",
    "trade_date": "trade_date",
    "fd_share": "shares",
    "fund_type": "fund_type",
    "market": "market",
}
FUND_SHARE_COLUMNS = list(TUSHARE_FUND_SHARE_FIELD_MAP.values()) + ["update_time"]
FUND_SHARE_SCALES = {"fd_share": 10000}

TUSHARE_FUND_ADJ_FIELD_MAP = {
    "ts_code": "fund_code",
    "trade_date": "trade_date",
    "adj_factor": "adjust_factor",
}
FUND_ADJ_COLUMNS = list(TUSHARE_FUND_ADJ_FIELD_MAP.values()) + ["update_time"]

TUSHARE_FUND_DIVIDEND_FIELD_MAP = {
    "ts_code": "fund_code",
    "ann_date": "announce_date",
    "imp_anndate": "implementation_announce_date",
    "base_date": "base_date",
    "div_proc": "process",
    "record_date": "record_date",
    "ex_date": "ex_dividend_date",
    "pay_date": "pay_date",
    "earpay_date": "earnings_pay_date",
    "net_ex_date": "net_ex_date",
    "div_cash": "cash_dividend",
    "base_unit": "base_units",
    "ear_distr": "earnings_distributable",
    "ear_amount": "earnings_distributed",
    "account_date": "account_date",
    "base_year": "base_year",
}
FUND_DIVIDEND_COLUMNS = list(TUSHARE_FUND_DIVIDEND_FIELD_MAP.values()) + ["update_time"]

# Fund stock holdings by report period (fund_portfolio). mkv 元, amount 股, ratios %.
TUSHARE_FUND_PORTFOLIO_FIELD_MAP = {
    "ts_code": "fund_code",
    "ann_date": "announce_date",
    "end_date": "report_period",
    "symbol": "code",
    "mkv": "market_value",
    "amount": "shares",
    "stk_mkv_ratio": "weight_in_fund",
    "stk_float_ratio": "float_share_ratio",
}
FUND_PORTFOLIO_COLUMNS = list(TUSHARE_FUND_PORTFOLIO_FIELD_MAP.values()) + ["update_time"]
DEFAULT_FUND_PORTFOLIO_START_DATE = "20030101"
FUND_PORTFOLIO_PAGE_SIZE = 5000
FUND_SERIES_PAGE_SIZE = 2000
