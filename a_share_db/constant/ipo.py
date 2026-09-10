"""Constants for the IPO (new share) table."""

TUSHARE_NEW_SHARE_FIELDS = [
    "ts_code",
    "sub_code",
    "name",
    "ipo_date",
    "issue_date",
    "amount",
    "market_amount",
    "price",
    "pe",
    "limit_amount",
    "funds",
    "ballot",
]

IPO_COLUMNS = [
    "code",
    "subscription_code",
    "name",
    "ipo_date",
    "list_date",
    "issue_shares",
    "online_issue_shares",
    "issue_price",
    "issue_pe",
    "subscription_limit_shares",
    "raised_funds",
    "ballot_rate",
    "update_time",
]

# Tushare share counts are in 万股 and raised funds in 亿元.
TUSHARE_IPO_SHARE_TO_LOCAL = 10000
TUSHARE_IPO_FUNDS_TO_LOCAL = 100_000_000

DEFAULT_IPO_START_DATE = "19900101"
# new_share caps each page at 2000 rows, so the range is paginated.
IPO_PAGE_SIZE = 2000
