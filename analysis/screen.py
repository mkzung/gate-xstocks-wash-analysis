"""Wash-trading detector: score every tokenized-stock market on Gate and rank them.

Runs a single composite non-organic-activity score over all xStock/USDT spot
markets Gate exposes, from the free public trade dumps. The score is the
geometric mean of three normalised, interpretable signals, so a market has to
trip ALL THREE to rank high:

  clip   - how much of the tape sits on one fixed trade size   (dominance)
  circ   - how two-sided that clip is: 1 - |buys-sells|/clipvol (circular volume)
  benf   - Kolmogorov-Smirnov distance of trade-size first digits from Benford

The flag threshold is calibrated above three organic controls run through the
same pipeline: the same-class MicroStrategy xStock and the liquid SOL/USDT and
LINK/USDT markets. Writes screen.json (every market, score, rank, flag) and a
ranked figure. Deterministic; no fetch beyond the cached dumps.
"""
import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from gatelib import load
from metrics_lib import benford_ks, score_from

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
POST = os.path.join(ROOT, "post")
MONTH = "202605"

# every xStock/USDT market Gate exposes a May-2026 dump for
UNIVERSE = ["AAPLX", "ABBVX", "ABTX", "ACNX", "AMZNX", "AVGOX", "AZNX", "COINX", "CRCLX",
            "CRWDX", "CSCOX", "DHRX", "GLDX", "GOOGLX", "HDX", "HONX", "HOODX", "KOX",
            "LLYX", "MCDX", "METAX", "MSTRX", "NFLXX", "NVDAX", "PEPX", "PGX", "QQQX",
            "SPYX", "TSLAX", "UNHX", "WMTX"]
LIQUID = ["SOL", "LINK"]   # liquid organic controls (not xStocks): calibrate the threshold above these
NAMES = {"AAPLX": "Apple", "ABBVX": "AbbVie", "ABTX": "Abbott", "ACNX": "Accenture",
         "AMZNX": "Amazon", "AVGOX": "Broadcom", "AZNX": "AstraZeneca", "COINX": "Coinbase",
         "CRCLX": "Circle", "CRWDX": "CrowdStrike", "CSCOX": "Cisco", "DHRX": "Danaher",
         "GLDX": "Gold ETF", "GOOGLX": "Alphabet", "HDX": "Home Depot", "HONX": "Honeywell",
         "HOODX": "Robinhood", "KOX": "Coca-Cola", "LLYX": "Eli Lilly", "MCDX": "McDonald's",
         "METAX": "Meta", "MSTRX": "MicroStrategy", "NFLXX": "Netflix", "NVDAX": "NVIDIA",
         "PEPX": "PepsiCo", "PGX": "P&G", "QQQX": "Nasdaq-100", "SPYX": "S&P 500",
         "TSLAX": "Tesla", "UNHX": "UnitedHealth", "WMTX": "Walmart", "SOL": "Solana", "LINK": "Chainlink"}

FLAG = 0.80        # calibrated above the liquid controls (SOL 0.69) and the same-class control (MSTRX 0.17)
MIN_TRADES = 5000  # below this a month is too thin to score the distribution reliably


def measure(sym):
    df = load(sym, MONTH)
    n = len(df)
    vc = df["amt"].value_counts()
    clip_qty = float(vc.index[0]); clip_share = float(vc.iloc[0] / n)
    clip = df[df["amt"] == clip_qty]
    cn = float(clip["notional"].sum())
    buy_n = float(clip.loc[clip["buy"], "notional"].sum())
    clip_net = abs(2 * buy_n - cn) / cn
    ks = benford_ks(df["amt"])
    tot = float(df["notional"].sum())
    days = df["t"].dt.date.nunique()
    return dict(symbol=sym, name=NAMES[sym], n_trades=int(n), distinct_sizes=int(df["amt"].nunique()),
                clip_qty=clip_qty, clip_share=round(clip_share, 4), clip_net_pct=round(clip_net, 3),
                benford_ks=round(ks, 3), daily_turnover_usd=round(tot / days, 0),
                turnover_usd=round(tot, 0), clip_notional=round(cn, 0),
                score=round(score_from(clip_share, clip_net, ks), 3))


allrows = sorted((measure(s) for s in UNIVERSE), key=lambda r: -r["score"])
for r in allrows:
    r["reliable"] = bool(r["n_trades"] >= MIN_TRADES)
    r["flag"] = bool(r["reliable"] and r["score"] >= FLAG)
rel = [r for r in allrows if r["reliable"]]
for i, r in enumerate(rel, 1):
    r["rank"] = i
flagged = [r["symbol"] for r in rel if r["flag"]]
ambiguous = [r["symbol"] for r in rel if not r["flag"] and r["symbol"] != "MSTRX" and r["score"] > 0.5]
thin = [r["symbol"] for r in allrows if not r["reliable"]]
controls = {s: measure(s) for s in LIQUID}
mstrx = next(r for r in rel if r["symbol"] == "MSTRX")

# organic null: resample BOTH a same-class (MSTRX) and a liquid (SOL) clean tape at the
# washed markets' sample sizes; the most common size by chance never approaches the flagged clips.
rng = np.random.default_rng(0)
null_max = 0.0
for src in (load("MSTRX", MONTH)["amt"].values, load("SOL", MONTH)["amt"].values):
    for nsamp in (65164, 28116):
        for _ in range(750):
            _, counts = np.unique(rng.choice(src, size=nsamp, replace=True), return_counts=True)
            null_max = max(null_max, counts.max() / nsamp)
min_flagged_clip = min(r["clip_share"] for r in rel if r["flag"])
flag_rows = [r for r in rel if r["flag"]]
agg_reported = sum(r["turnover_usd"] for r in flag_rows)
agg_clip = sum(r["clip_notional"] for r in flag_rows)

out = dict(month=MONTH, venue="Gate.io", universe_n=len(UNIVERSE), min_trades=MIN_TRADES, flag_threshold=FLAG,
           reliable_n=len(rel), n_flagged=len(flagged), flagged=flagged, ambiguous=ambiguous, too_thin=thin,
           same_class_control=dict(symbol="MSTRX", score=mstrx["score"]),
           liquid_controls={s: dict(name=NAMES[s], n_trades=controls[s]["n_trades"],
                                     clip_share=controls[s]["clip_share"], score=controls[s]["score"]) for s in LIQUID},
           null_top_share_max=round(float(null_max), 4), null_reps=3000,
           min_flagged_clip_share=round(float(min_flagged_clip), 4),
           flagged_reported_usd=round(agg_reported, 0), flagged_clip_usd=round(agg_clip, 0),
           flagged_clip_dollar_share=round(agg_clip / agg_reported, 4), markets=allrows)
json.dump(out, open(os.path.join(ROOT, "screen.json"), "w"), indent=2)
pd.DataFrame(allrows)[["symbol", "name", "n_trades", "reliable", "clip_share", "clip_net_pct",
                       "benford_ks", "score", "flag"]].to_csv(os.path.join(ROOT, "data", "screen.csv"), index=False)

print(f"Screened {len(UNIVERSE)} xStock markets, {MONTH}. {len(rel)} liquid enough to score; "
      f"flag >= {FLAG} (above liquid control SOL {controls['SOL']['score']}). {len(flagged)} flagged:\n")
print(f"  {'#':>2} {'mkt':7} {'trades':>8} {'clip%':>6} {'circ':>5} {'KS':>5} {'score':>6}  flag")
for r in rel:
    print(f"  {r['rank']:>2} {r['symbol']:7} {r['n_trades']:>8,} {r['clip_share']*100:5.1f}% "
          f"{1-r['clip_net_pct']:5.2f} {r['benford_ks']:5.2f} {r['score']:6.3f}  {'WASH' if r['flag'] else ''}")
for s in LIQUID:
    c = controls[s]
    print(f"  -- {s:7} {c['n_trades']:>8,} {c['clip_share']*100:5.1f}% {1-c['clip_net_pct']:5.2f} "
          f"{c['benford_ks']:5.2f} {c['score']:6.3f}  liquid control")
print(f"\nflagged ({len(flagged)}): {', '.join(flagged)}")
print(f"ambiguous (elevated, within the liquid-control band): {', '.join(ambiguous)}")
print(f"too thin to score ({len(thin)}): {len(thin)} markets")
print(f"organic null (MSTRX + SOL): top-share <= {null_max*100:.1f}% in 3,000 draws vs smallest flagged "
      f"{min_flagged_clip*100:.1f}% (p < 1/3000)")

# ranked figure: reliable xStocks + the two liquid controls, calibrated against the flag line
xs = rel + [controls[s] for s in LIQUID]
labels = [r["symbol"] for r in rel] + LIQUID


def colour(r):
    if r["symbol"] in LIQUID:
        return "#1c7ed6"          # liquid control
    if r["symbol"] == "MSTRX":
        return "#2f9e44"          # same-class control
    return "#d9480f" if r["flag"] else "#adb5bd"   # flagged / ambiguous


fig, ax = plt.subplots(figsize=(10, 5.0))
ax.bar(range(len(xs)), [r["score"] for r in xs], color=[colour(r) for r in xs], width=0.8)
ax.axhline(FLAG, ls="--", color="#495057", lw=1, label=f"flag threshold {FLAG} (above the controls)")
for i, r in enumerate(xs):
    ax.text(i, r["score"] + 0.015, f"{r['score']:.2f}", ha="center", fontsize=7.5)
ax.set_ylabel("non-organic-activity score (0-1)"); ax.set_ylim(0, 1.08)
ax.set_title(f"Gate liquid tokenized stocks, May 2026: {len(flagged)} flagged (orange) vs organic "
             f"controls (MSTRX, SOL, LINK)", fontsize=10.5)
ax.set_xticks(range(len(xs))); ax.set_xticklabels(labels, rotation=90, fontsize=8)
ax.legend(loc="upper right"); fig.tight_layout()
fig.savefig(os.path.join(POST, "screen.png"), dpi=120); plt.close()
print("wrote screen.json + data/screen.csv + post/screen.png")
