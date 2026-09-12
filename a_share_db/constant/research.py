"""Constants for sell-side research and institutional activity tables."""

# Broker research reports with earnings forecasts (report_rc). Forecast money
# amounts are provider 万元 and converted to 元; ratios stay in % and 倍.
TUSHARE_BROKER_REPORT_FIELD_MAP = {
    "ts_code": "code",
    "name": "name",
    "report_date": "report_date",
    "report_title": "report_title",
    "report_type": "report_type",
    "classify": "classification",
    "org_name": "institution",
    "author_name": "author",
    "quarter": "forecast_period",
    "op_rt": "operating_revenue_forecast",
    "op_pr": "operating_profit_forecast",
    "tp": "total_profit_forecast",
    "np": "net_profit_forecast",
    "eps": "eps_forecast",
    "pe": "pe_forecast",
    "rd": "dividend_yield_forecast",
    "roe": "roe_forecast",
    "ev_ebitda": "ev_ebitda_forecast",
    "rating": "rating",
    "max_price": "target_price_high",
    "min_price": "target_price_low",
}
BROKER_REPORT_COLUMNS = list(TUSHARE_BROKER_REPORT_FIELD_MAP.values()) + ["update_time"]
BROKER_REPORT_SCALES = {"op_rt": 10000, "op_pr": 10000, "tp": 10000, "np": 10000}
DEFAULT_BROKER_REPORT_START_DATE = "20060101"

# Institutional surveys (stk_surv), covered from 2023.
TUSHARE_INSTITUTION_SURVEY_FIELD_MAP = {
    "ts_code": "code",
    "name": "name",
    "surv_date": "survey_date",
    "fund_visitors": "visiting_institutions",
    "rece_place": "reception_place",
    "rece_mode": "reception_mode",
    "rece_org": "reception_organizer",
    "org_type": "institution_type",
    "comp_rece": "company_receivers",
}
INSTITUTION_SURVEY_COLUMNS = list(TUSHARE_INSTITUTION_SURVEY_FIELD_MAP.values()) + ["update_time"]
DEFAULT_INSTITUTION_SURVEY_START_DATE = "20230101"
INSTITUTION_SURVEY_PAGE_SIZE = 400

# Monthly broker "golden stock" recommendations (broker_recommend), from 2022.
TUSHARE_BROKER_RECOMMEND_FIELD_MAP = {
    "month": "month",
    "broker": "broker",
    "ts_code": "code",
    "name": "name",
}
BROKER_RECOMMEND_COLUMNS = list(TUSHARE_BROKER_RECOMMEND_FIELD_MAP.values()) + ["update_time"]
DEFAULT_BROKER_RECOMMEND_START_MONTH = "202201"
