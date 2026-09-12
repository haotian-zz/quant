"""Constants for the provider technical-factor table (stk_factor_pro).

The provider names indicators as {indicator}_{bfq|hfq|qfq}[_{window}]. Local
names keep that systematic scheme but use the warehouse adjust-type word
"none" instead of the provider abbreviation "bfq", and the header fields
follow the daily / daily_basic naming.
"""

_HEADER_FIELD_MAP = {
    "ts_code": "code",
    "trade_date": "trade_date",
    "open": "open",
    "open_hfq": "open_hfq",
    "open_qfq": "open_qfq",
    "high": "high",
    "high_hfq": "high_hfq",
    "high_qfq": "high_qfq",
    "low": "low",
    "low_hfq": "low_hfq",
    "low_qfq": "low_qfq",
    "close": "close",
    "close_hfq": "close_hfq",
    "close_qfq": "close_qfq",
    "pre_close": "pre_close",
    "change": "change",
    "pct_chg": "pct_chg",
    "vol": "volume",
    "amount": "amount",
    "turnover_rate": "turnover_rate",
    "turnover_rate_f": "turnover_rate_free_float",
    "volume_ratio": "volume_ratio",
    "pe": "pe",
    "pe_ttm": "pe_ttm",
    "pb": "pb",
    "ps": "ps",
    "ps_ttm": "ps_ttm",
    "dv_ratio": "dividend_yield",
    "dv_ttm": "dividend_yield_ttm",
    "total_share": "total_shares",
    "float_share": "float_shares",
    "free_share": "free_float_shares",
    "total_mv": "total_market_value",
    "circ_mv": "float_market_value",
    "adj_factor": "adjust_factor",
}

_INDICATOR_BASES = [
    "asi", "asit", "atr", "bbi", "bias1", "bias2", "bias3", "boll_lower", "boll_mid", "boll_upper",
    "brar_ar", "brar_br", "cci", "cr", "dfma_dif", "dfma_difma", "dmi_adx", "dmi_adxr", "dmi_mdi", "dmi_pdi",
    "dpo", "madpo", "emv", "maemv", "kdj", "kdj_d", "kdj_k", "ktn_down", "ktn_mid", "ktn_upper",
    "macd", "macd_dea", "macd_dif", "mass", "ma_mass", "mfi", "mtm", "mtmma", "obv", "psy", "psyma",
    "roc", "maroc", "taq_down", "taq_mid", "taq_up", "trix", "trma", "vr", "wr", "wr1",
    "xsii_td1", "xsii_td2", "xsii_td3", "xsii_td4",
]
_WINDOWED_BASES = {"ema": [5, 10, 20, 30, 60, 90, 250], "ma": [5, 10, 20, 30, 60, 90, 250], "expma": [12, 50], "rsi": [6, 12, 24]}
_ADJUST_SUFFIXES = {"bfq": "none", "hfq": "hfq", "qfq": "qfq"}
_COUNTER_FIELDS = ["downdays", "updays", "lowdays", "topdays"]


def _build_field_map() -> dict[str, str]:
    field_map = dict(_HEADER_FIELD_MAP)
    for base in _INDICATOR_BASES:
        for provider_suffix, local_suffix in _ADJUST_SUFFIXES.items():
            field_map[f"{base}_{provider_suffix}"] = f"{base}_{local_suffix}"
    for base, windows in _WINDOWED_BASES.items():
        for provider_suffix, local_suffix in _ADJUST_SUFFIXES.items():
            for window in windows:
                if base in ("ema", "ma"):
                    field_map[f"{base}_{provider_suffix}_{window}"] = f"{base}_{local_suffix}_{window}"
                elif base == "rsi":
                    field_map[f"rsi_{provider_suffix}_{window}"] = f"rsi_{local_suffix}_{window}"
                else:
                    field_map[f"{base}_{window}_{provider_suffix}"] = f"{base}_{window}_{local_suffix}"
    for field in _COUNTER_FIELDS:
        field_map[field] = field
    return field_map


TUSHARE_TECHNICAL_FACTOR_FIELD_MAP = _build_field_map()
TECHNICAL_FACTOR_COLUMNS = list(TUSHARE_TECHNICAL_FACTOR_FIELD_MAP.values()) + ["update_time"]
# Header units follow daily/daily_basic: vol 手 -> 股, amount 千元 -> 元, shares 万股 -> 股, mv 万元 -> 元.
TECHNICAL_FACTOR_SCALES = {"vol": 100, "amount": 1000, "total_share": 10000, "float_share": 10000, "free_share": 10000, "total_mv": 10000, "circ_mv": 10000}
TECHNICAL_FACTOR_PAGE_SIZE = 5000
