"""Constants for macro and interest-rate reference tables."""

# Shibor (%): provider tenor names are kept readable in local columns.
TUSHARE_SHIBOR_FIELDS = ["date", "on", "1w", "2w", "1m", "3m", "6m", "9m", "1y"]
TUSHARE_SHIBOR_FIELD_MAP = {
    "on": "overnight",
    "1w": "week_1",
    "2w": "week_2",
    "1m": "month_1",
    "3m": "month_3",
    "6m": "month_6",
    "9m": "month_9",
    "1y": "year_1",
}
SHIBOR_COLUMNS = ["rate_date"] + list(TUSHARE_SHIBOR_FIELD_MAP.values()) + ["update_time"]
SHIBOR_PAGE_SIZE = 2000
DEFAULT_SHIBOR_START_DATE = "20061008"

# Quarterly GDP (亿元 and %)
TUSHARE_GDP_FIELDS = ["quarter", "gdp", "gdp_yoy", "pi", "pi_yoy", "si", "si_yoy", "ti", "ti_yoy"]
TUSHARE_GDP_FIELD_MAP = {
    "gdp": "gdp",
    "gdp_yoy": "gdp_yoy",
    "pi": "primary_industry",
    "pi_yoy": "primary_industry_yoy",
    "si": "secondary_industry",
    "si_yoy": "secondary_industry_yoy",
    "ti": "tertiary_industry",
    "ti_yoy": "tertiary_industry_yoy",
}
GDP_COLUMNS = ["quarter"] + list(TUSHARE_GDP_FIELD_MAP.values()) + ["update_time"]

# Monthly CPI (index values and %)
TUSHARE_CPI_FIELDS = [
    "month",
    "nt_val", "nt_yoy", "nt_mom", "nt_accu",
    "town_val", "town_yoy", "town_mom", "town_accu",
    "cnt_val", "cnt_yoy", "cnt_mom", "cnt_accu",
]
TUSHARE_CPI_FIELD_MAP = {
    "nt_val": "national_value",
    "nt_yoy": "national_yoy",
    "nt_mom": "national_mom",
    "nt_accu": "national_accumulated",
    "town_val": "urban_value",
    "town_yoy": "urban_yoy",
    "town_mom": "urban_mom",
    "town_accu": "urban_accumulated",
    "cnt_val": "rural_value",
    "cnt_yoy": "rural_yoy",
    "cnt_mom": "rural_mom",
    "cnt_accu": "rural_accumulated",
}
CPI_COLUMNS = ["month"] + list(TUSHARE_CPI_FIELD_MAP.values()) + ["update_time"]

# Monthly PPI (%). Provider abbreviations: mp=means of production, cg=consumer goods,
# qm=mining, rm=raw materials, p=processing, f=food, c=clothing, adu=daily use, dcg=durables.
_PPI_GROUPS = {
    "ppi": "ppi",
    "ppi_mp": "production_materials",
    "ppi_mp_qm": "production_mining",
    "ppi_mp_rm": "production_raw_materials",
    "ppi_mp_p": "production_processing",
    "ppi_cg": "consumer_goods",
    "ppi_cg_f": "consumer_food",
    "ppi_cg_c": "consumer_clothing",
    "ppi_cg_adu": "consumer_daily_use",
    "ppi_cg_dcg": "consumer_durables",
}
TUSHARE_PPI_FIELD_MAP = {}
for _suffix, _local_suffix in (("yoy", "yoy"), ("mom", "mom"), ("accu", "accumulated")):
    for _provider, _local in _PPI_GROUPS.items():
        TUSHARE_PPI_FIELD_MAP[f"{_provider}_{_suffix}"] = f"{_local}_{_local_suffix}"
TUSHARE_PPI_FIELDS = ["month"] + list(TUSHARE_PPI_FIELD_MAP.keys())
PPI_COLUMNS = ["month"] + list(TUSHARE_PPI_FIELD_MAP.values()) + ["update_time"]

# Monthly money supply (亿元 and %)
TUSHARE_MONEY_SUPPLY_FIELDS = ["month", "m0", "m0_yoy", "m0_mom", "m1", "m1_yoy", "m1_mom", "m2", "m2_yoy", "m2_mom"]
TUSHARE_MONEY_SUPPLY_FIELD_MAP = {field: field for field in TUSHARE_MONEY_SUPPLY_FIELDS if field != "month"}
MONEY_SUPPLY_COLUMNS = ["month"] + list(TUSHARE_MONEY_SUPPLY_FIELD_MAP.values()) + ["update_time"]


# LPR (shibor_lpr), %, from 2013-10.
TUSHARE_LPR_FIELD_MAP = {"date": "rate_date", "1y": "year_1", "5y": "year_5"}
LPR_COLUMNS = list(TUSHARE_LPR_FIELD_MAP.values()) + ["update_time"]
DEFAULT_LPR_START_DATE = "20131025"

# PMI (cn_pmi). Provider columns are statistical codes; only the headline
# series are kept (large/medium/small-enterprise breakdowns are dropped).
TUSHARE_PMI_FIELD_MAP = {
    "MONTH": "month",
    "PMI010000": "manufacturing_pmi",
    "PMI010100": "manufacturing_production",
    "PMI010200": "manufacturing_new_orders",
    "PMI010300": "manufacturing_new_export_orders",
    "PMI010400": "manufacturing_backlog_orders",
    "PMI010500": "manufacturing_finished_inventory",
    "PMI010600": "manufacturing_purchase_volume",
    "PMI010700": "manufacturing_imports",
    "PMI010800": "manufacturing_output_prices",
    "PMI010900": "manufacturing_input_prices",
    "PMI011000": "manufacturing_raw_material_inventory",
    "PMI011100": "manufacturing_employment",
    "PMI011200": "manufacturing_supplier_delivery",
    "PMI011300": "manufacturing_expectations",
    "PMI020100": "non_manufacturing_business_activity",
    "PMI020200": "non_manufacturing_new_orders",
    "PMI020300": "non_manufacturing_new_export_orders",
    "PMI020400": "non_manufacturing_backlog_orders",
    "PMI020500": "non_manufacturing_inventory",
    "PMI020600": "non_manufacturing_input_prices",
    "PMI020700": "non_manufacturing_sales_prices",
    "PMI020800": "non_manufacturing_employment",
    "PMI020900": "non_manufacturing_supplier_delivery",
    "PMI021000": "non_manufacturing_expectations",
    "PMI030000": "composite_pmi_output",
}
PMI_COLUMNS = list(TUSHARE_PMI_FIELD_MAP.values()) + ["update_time"]

# Social financing (sf_month), 亿元 -> 元.
TUSHARE_SOCIAL_FINANCING_FIELD_MAP = {
    "month": "month",
    "inc_month": "increment_month",
    "inc_cumval": "increment_cumulative",
    "stk_endval": "stock_end_value",
}
SOCIAL_FINANCING_COLUMNS = list(TUSHARE_SOCIAL_FINANCING_FIELD_MAP.values()) + ["update_time"]
SOCIAL_FINANCING_SCALES = {"inc_month": 1e8, "inc_cumval": 1e8, "stk_endval": 1e8}

# US treasury yield curve (us_tycr), %.
TUSHARE_US_TREASURY_FIELD_MAP = {
    "date": "rate_date",
    "m1": "month_1", "m2": "month_2", "m3": "month_3", "m4": "month_4", "m6": "month_6",
    "y1": "year_1", "y2": "year_2", "y3": "year_3", "y5": "year_5", "y7": "year_7",
    "y10": "year_10", "y20": "year_20", "y30": "year_30",
}
US_TREASURY_COLUMNS = list(TUSHARE_US_TREASURY_FIELD_MAP.values()) + ["update_time"]
DEFAULT_US_TREASURY_START_DATE = "19900101"
US_TREASURY_PAGE_SIZE = 2000

# Economic calendar (eco_cal), one request per calendar day.
TUSHARE_ECONOMIC_CALENDAR_FIELD_MAP = {
    "date": "event_date",
    "time": "event_time",
    "currency": "currency",
    "country": "country",
    "event": "event",
    "value": "value",
    "pre_value": "previous_value",
    "fore_value": "forecast_value",
}
ECONOMIC_CALENDAR_COLUMNS = list(TUSHARE_ECONOMIC_CALENDAR_FIELD_MAP.values()) + ["update_time"]
DEFAULT_ECONOMIC_CALENDAR_START_DATE = "20150101"
ECONOMIC_CALENDAR_PAGE_SIZE = 100
