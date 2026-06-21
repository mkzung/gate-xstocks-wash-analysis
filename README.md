# Wash trading on tokenized stocks (xStocks) on Gate

[![test](https://github.com/mkzung/gate-xstocks-wash-analysis/actions/workflows/test.yml/badge.svg)](https://github.com/mkzung/gate-xstocks-wash-analysis/actions/workflows/test.yml)
![python](https://img.shields.io/badge/python-3.11-blue)
![license](https://img.shields.io/badge/license-MIT-green)

Companion code for a DN Institute [Market Health](https://github.com/1712n/dn-institute/tree/main/content/research/market-health) wiki submission. A composite detector scores **all 31 tokenized-stock (xStock) markets on Gate** on three converging signatures (a dominant fixed clip, that clip's two-sidedness, and a broken first-digit distribution). With the flag threshold **calibrated above three organic controls** - the same-class MicroStrategy (0.17) and the liquid SOL (0.69) and LINK (0.43) - **9 of the 13 markets liquid enough to score are flagged** (score 0.83 to 0.99). The **same tokens trade cleanly on Bybit**, so the wash is venue-specific; on HOODX it escalated from an elevated clip in October 2025 to clearly washed by March 2026. Reconstructed from free Gate and Bybit public trade dumps; the flagged clips are unreachable under an organic null at p < 1/3000.

**Live dashboard:** https://mkzung.github.io/gate-xstocks-wash-analysis/

## The screen (Gate, May 2026, markets with >= 5,000 trades)

| # | market | trades | clip share | circularity | Benford KS | score | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | AMZNX (Amazon) | 40,218 | 22.0% | 0.98 | 0.29 | 0.99 | WASH |
| 2 | AZNX (AstraZeneca) | 5,746 | 19.9% | 0.94 | 0.20 | 0.98 | WASH |
| 3 | TSLAX (Tesla) | 242,598 | 24.0% | 0.93 | 0.22 | 0.97 | WASH |
| 4 | HOODX (Robinhood) | 65,164 | 49.4% | 0.92 | 0.35 | 0.97 | WASH |
| 5 | AAPLX (Apple) | 37,753 | 17.1% | 0.93 | 0.14 | 0.95 | WASH |
| 6 | GOOGLX (Alphabet) | 33,819 | 16.8% | 0.91 | 0.14 | 0.94 | WASH |
| 7 | QQQX (Nasdaq-100) | 63,722 | 15.9% | 0.95 | 0.11 | 0.88 | WASH |
| 8 | SPYX (S&P 500) | 28,116 | 25.4% | 0.88 | 0.10 | 0.85 | WASH |
| 9 | NVDAX (NVIDIA) | 196,025 | 23.0% | 0.90 | 0.10 | 0.83 | WASH |
| 10 | CRCLX (Circle) | 631,314 | 14.0% | 0.86 | 0.07 | 0.74 | ambiguous |
| 11 | COINX (Coinbase) | 21,038 | 10.2% | 0.98 | 0.06 | 0.66 | ambiguous |
| 12 | METAX (Meta) | 6,181 | 9.9% | 0.95 | 0.05 | 0.61 | ambiguous |
| 13 | **MSTRX** (MicroStrategy) | 27,467 | **5.0%** | **0.06** | **0.03** | **0.17** | control |
| - | *SOL/USDT (liquid control)* | 2,180,550 | 7.5% | 0.99 | 0.10 | 0.69 | control |
| - | *LINK/USDT (liquid control)* | 688,530 | 1.9% | 0.87 | 0.11 | 0.43 | control |

`score` = geometric mean of three normalised signals (clip dominance, circularity `1 - |buys-sells|/clipvol`, Benford break), so a market must trip all three to score high. The flag at **0.80** sits above every organic control. The three "ambiguous" markets are elevated but inside the band of the liquid control SOL, so they are not flagged. 18 further markets had under 5,000 trades and were too thin to score.

## Same tokens, two venues (May 2026)

| market | clip on Gate | clip on Bybit | Gate score | Bybit score |
| --- | --- | --- | --- | --- |
| HOODX | 49.4% | 1.9% | 0.97 | 0.49 |
| TSLAX | 24.0% | 5.6% | 0.97 | 0.56 |
| NVDAX | 23.0% | 4.7% | 0.83 | 0.53 |
| AAPLX | 17.1% | 5.4% | 0.95 | 0.65 |
| GOOGLX | 16.8% | 5.3% | 0.94 | 0.63 |

Same token, same issuer, same underlying, same month: a dominant wash clip on Gate (above the flag), organic on Bybit (below it). The wash is the venue's, not the token's.

## Reproduce

```bash
pip install -r requirements.txt
cd analysis
python build_analysis.py   # per-market mechanism (six largest flagged + the control) -> findings.json + figures
python screen.py           # score all 31 markets + organic controls -> screen.json + screen.png
python longitudinal.py     # HOODX month by month since listing -> longitudinal.json + figure
python crossvenue.py       # Gate vs Bybit on five shared tickers -> crossvenue.json + figure
python verify.py           # independently recompute + assert the mechanism numbers
cd .. && pytest -q         # mechanism + screen + cross-venue + onset invariants
```

CI runs the full chain and pulls the public dumps live, so the badge depends on those endpoints being reachable.

## Data

Free, key-less public spot trade dumps: Gate `https://download.gatedata.org/spot/deals/<YYYYMM>/<PAIR>-<YYYYMM>.csv.gz` and Bybit `https://public.bybit.com/spot/<SYM>USDT/<SYM>USDT-<YYYY-MM>.csv.gz` (one row per trade). Taker side verified empirically (taker buys push the price up). Processed per-figure datasets are committed under [`data/`](data/) (`screen.csv`, `per_stock_metrics.csv`, `hoodx_daily_clip_share.csv`, `longitudinal.csv`, `crossvenue.csv`).
