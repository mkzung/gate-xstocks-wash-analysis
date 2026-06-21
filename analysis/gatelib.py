"""Loader for Gate.io spot "deals" (trade) dumps from download.gatedata.org.

Free, key-less monthly trade dumps live at
``https://download.gatedata.org/spot/deals/{YYYYMM}/{PAIR}-{YYYYMM}.csv.gz``.

The CSV has no header; columns are:
    unix_timestamp(seconds.microseconds), trade_id, price, amount(base), side

The ``side`` flag is the taker side, encoded 1 or 2. It is verified empirically
in ``build_analysis``: taker buys (side 1) push the price up, sells (side 2) push
it down, so ``buy = side == 1``.
"""
import os
import gzip
import urllib.request
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
BASE = "https://download.gatedata.org/spot/deals"


def _path(sym, month):
    return os.path.join(CACHE, f"{sym}_USDT-{month}.csv.gz")


def fetch(sym, month):
    """Download a monthly deals dump into the cache if not already present."""
    os.makedirs(CACHE, exist_ok=True)
    path = _path(sym, month)
    if not os.path.exists(path):
        url = f"{BASE}/{month}/{sym}_USDT-{month}.csv.gz"
        urllib.request.urlretrieve(url, path)
    return path


def load(sym, month="202605"):
    """Load one month of Gate spot trades for ``<sym>/USDT`` as a DataFrame."""
    path = _path(sym, month)
    if not os.path.exists(path):
        path = fetch(sym, month)
    with gzip.open(path, "rt") as fh:
        df = pd.read_csv(fh, header=None, names=["ts", "id", "price", "amt", "side"])
    df = df.sort_values("ts").reset_index(drop=True)
    df["t"] = pd.to_datetime(df["ts"], unit="s", utc=True)
    df["buy"] = df["side"] == 1            # 1 = taker buy (verified by the uptick test)
    df["notional"] = df["price"] * df["amt"]
    return df
