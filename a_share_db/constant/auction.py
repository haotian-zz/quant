"""Constants for call-auction tables (opening and closing auctions)."""

# stk_auction_o / stk_auction_c: vol in 股, amount in 元, vwap in 元.
TUSHARE_AUCTION_FIELD_MAP = {
    "ts_code": "code",
    "trade_date": "trade_date",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "vol": "volume",
    "amount": "amount",
    "vwap": "vwap",
}
AUCTION_COLUMNS = list(TUSHARE_AUCTION_FIELD_MAP.values()) + ["update_time"]
DEFAULT_AUCTION_START_DATE = "20090105"
AUCTION_PAGE_SIZE = 4000
