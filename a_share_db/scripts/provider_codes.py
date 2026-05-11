"""Provider-specific security code adapters.

Curated local tables store only local domain fields. Downstream ETL jobs should
derive provider identifiers through this module instead of persisting
provider-specific fields in metadata or market data tables.
"""

from __future__ import annotations


def build_sina_symbol(code: str, exchange: str) -> str:
    """Return Sina/Tencent style symbol, for example sh600519."""
    prefix = _market_prefix(code, exchange)
    return f"{prefix}{code}" if prefix else code


def build_tencent_symbol(code: str, exchange: str) -> str:
    """Return Tencent style symbol, currently same format as Sina."""
    return build_sina_symbol(code, exchange)


def build_eastmoney_secid(code: str, exchange: str) -> str:
    """Return Eastmoney secid, for example 1.600519."""
    exchange = (exchange or "").upper()
    if exchange == "SSE":
        return f"1.{code}"
    if exchange in {"SZSE", "BSE"}:
        return f"0.{code}"
    if code.startswith(("60", "68")):
        return f"1.{code}"
    if code.startswith(("00", "30", "4", "8", "9")):
        return f"0.{code}"
    return code


def _market_prefix(code: str, exchange: str) -> str:
    exchange = (exchange or "").upper()
    prefix_by_exchange = {
        "SSE": "sh",
        "SZSE": "sz",
        "BSE": "bj",
    }
    prefix = prefix_by_exchange.get(exchange)
    if prefix is not None:
        return prefix
    if code.startswith(("60", "68")):
        return "sh"
    if code.startswith(("00", "30")):
        return "sz"
    if code.startswith(("4", "8", "9")):
        return "bj"
    return ""
