"""Shared metrics for the wash screen, longitudinal and cross-venue scripts.

One trade table in (columns ts, price, amt, side, buy, notional), one dict of
signals out. The composite score is the geometric mean of three normalised
signals (clip dominance, circular volume, Benford break), so a market must trip
all three to score high. Kept in one place so every script and the verifier
compute the score identically.
"""
import math
import pandas as pd

BENFORD = pd.Series({d: math.log10(1 + 1 / d) for d in range(1, 10)})
CLIP_CAP, BENF_CAP = 0.15, 0.15


def benford_ks(amt):
    fd = amt.astype(str).str.replace(".", "", regex=False).str.lstrip("0").str[0]
    fd = fd[fd.str.isdigit() & (fd != "0")].astype(int)
    obs = fd.value_counts(normalize=True).reindex(range(1, 10), fill_value=0.0)
    return float((obs.cumsum() - BENFORD.cumsum()).abs().max())


def score_from(clip_share, clip_net, ks):
    s_clip = min(1.0, clip_share / CLIP_CAP)
    s_circ = max(0.0, 1.0 - clip_net)
    s_benf = min(1.0, ks / BENF_CAP)
    return (s_clip * s_circ * s_benf) ** (1 / 3)


def metrics(df):
    n = len(df)
    vc = df["amt"].value_counts()
    clip_qty = float(vc.index[0]); clip_share = float(vc.iloc[0] / n)
    clip = df[df["amt"] == clip_qty]
    cn = float(clip["notional"].sum())
    buy_n = float(clip.loc[clip["buy"], "notional"].sum())
    clip_net = abs(2 * buy_n - cn) / cn if cn else 1.0
    ks = benford_ks(df["amt"])
    return dict(n_trades=int(n), clip_qty=clip_qty, clip_share=clip_share, clip_net=clip_net,
                benford_ks=ks, clip_notional=cn, score=score_from(clip_share, clip_net, ks))
