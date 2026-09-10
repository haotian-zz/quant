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
