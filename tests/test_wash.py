"""Smoke + invariant tests for the Gate xStocks wash analysis."""
import os
import sys
import json
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
from gatelib import load  # noqa: E402

F = json.load(open(os.path.join(ROOT, "findings.json")))
WASHED = F["_meta"]["washed"]
CONTROL = F["_meta"]["control"]


def test_side_flag_buys_push_price_up():
    """The taker-side flag is correct: side-1 (buy) trades push the price up."""
    df = load("NVDAX")
    dp = df["price"].diff()
    up = dp[df["buy"]].mean()
    down = dp[~df["buy"]].mean()
    assert up > 0 > down


def test_washed_clip_is_circular_and_breaks_benford():
    for s in WASHED:
        assert F[s]["top_clip_share"] > 0.16          # dominates the trade count
        assert 0.42 < F[s]["clip_buyshare"] < 0.48     # two-sided
        assert F[s]["clip_net_pct"] < 0.15             # nets to almost no position (circular)
        assert F[s]["daybuy_std"] < 0.15               # balance held across the month
        assert F[s]["benford_ks"] > 0.09               # first digit broken


def test_count_inflated_more_than_dollars():
    """The wash inflates the trade count far more than the dollar volume."""
    for s in WASHED:
        assert F[s]["clip_dollar_share"] < F[s]["top_clip_share"]
    assert F["_meta"]["clip_dollar_share"] < 0.10
    assert F["_meta"]["clip_trade_share_max"] > 0.45


def test_control_is_organic():
    c = F[CONTROL]
    assert c["top_clip_share"] < 0.08
    assert c["clip_net_pct"] > 0.85                    # takes a real side, not circular
    assert c["benford_ks"] < 0.06


def test_hoodx_headline():
    h = F["HOODX"]
    assert h["top_clip_qty"] == 0.12
    assert h["top_clip_share"] > 0.49
    assert h["days"] == 31


def test_loader_columns():
    df = load("MSTRX")
    assert {"ts", "price", "amt", "side", "buy", "notional"}.issubset(df.columns)
    assert df["ts"].is_monotonic_increasing


def test_dumps_are_complete():
    """The tape is the full record: trade ids are unique and gap-free (span == count)."""
    df = load("HOODX")
    assert df["id"].is_unique
    assert int(df["id"].max() - df["id"].min() + 1) == len(df)


# ---- screen / longitudinal / cross-venue invariants (over the regenerated JSON outputs) ----

def test_screen_flags_are_pervasive_and_calibrated():
    s = json.load(open(os.path.join(ROOT, "screen.json")))
    rel = [m for m in s["markets"] if m["reliable"]]
    assert len(rel) >= 12, "at least a dozen markets liquid enough to score"
    assert 8 <= s["n_flagged"] <= 11, "most liquid markets flagged, but not all"
    flagged_scores = [m["score"] for m in rel if m["flag"]]
    assert min(flagged_scores) >= s["flag_threshold"], "flagged markets clear the threshold"
    # the threshold is calibrated above every organic control (same-class and liquid)
    assert s["same_class_control"]["score"] < s["flag_threshold"], "same-class control below the flag"
    ctrl_scores = [c["score"] for c in s["liquid_controls"].values()]
    assert all(c < s["flag_threshold"] for c in ctrl_scores), "liquid controls below the flag"
    assert min(flagged_scores) - max(ctrl_scores) > 0.1, "clear gap above the controls, not flag-everything"
    # clip dominance is unreachable under an organic null (resampled from same-class + liquid controls)
    assert s["null_top_share_max"] < 0.10, "organic null top-share stays low"
    assert s["null_top_share_max"] < s["min_flagged_clip_share"], "every flagged clip exceeds the null"


def test_crossvenue_is_gate_specific():
    c = json.load(open(os.path.join(ROOT, "crossvenue.json")))
    for m in c["markets"]:
        assert m["gate_clip_share"] > 0.15, (m["symbol"], "dominant clip on Gate")
        assert m["bybit_clip_share"] < 0.07, (m["symbol"], "organic clip on Bybit")
        assert m["gate_clip_share"] > 3 * m["bybit_clip_share"], (m["symbol"], "Gate >> Bybit")


def test_longitudinal_onset_and_escalation():
    lo = json.load(open(os.path.join(ROOT, "longitudinal.json")))
    by = {r["month"]: r for r in lo["months"]}
    assert lo["first_elevated_month"] == "202510", "elevated clip from October 2025"
    assert lo["flag_crossed_month"] == "202603", "clearly washed from March 2026"
    assert all(by[m]["clip_share"] < 0.03 for m in ("202507", "202508", "202509")), "clean at launch"
    assert by["202605"]["clip_share"] > 0.45, "escalated by May"
    assert lo["cumulative_clip_usd"] > 800000, "cumulative manufactured volume"
