"""Build a self-contained dark dashboard (index.html + dashboard.html).

Leads with the venue-wide screen, then the cross-venue control and the onset
series, with the mechanism figures behind them. Reads the committed JSON
outputs and embeds the figures as base64, so the page is a single file.
"""
import os
import json
import base64

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
S = json.load(open(os.path.join(ROOT, "screen.json")))
C = json.load(open(os.path.join(ROOT, "crossvenue.json")))
L = json.load(open(os.path.join(ROOT, "longitudinal.json")))
REL = [m for m in S["markets"] if m["reliable"]]
MST = next(m for m in S["markets"] if m["symbol"] == "MSTRX")


def b64(name):
    with open(os.path.join(ROOT, "post", name), "rb") as fh:
        return base64.b64encode(fh.read()).decode()


fig = {n: b64(n) for n in ["screen.png", "crossvenue.png", "longitudinal.png",
                           "circular-volume.png", "benford.png"]}

rows = "".join(
    '<tr%s><td class="num">%d</td><td class="txt">%s</td><td class="txt">%s</td><td class="num">%s</td>'
    '<td class="num">%.1f%%</td><td class="num">%.2f</td><td class="num">%.2f</td><td class="num">%.2f</td>'
    '<td>%s</td></tr>'
    % (' class="control"' if m["symbol"] == "MSTRX" else "", m["rank"], m["symbol"], m["name"],
       f'{m["n_trades"]:,}', m["clip_share"] * 100, 1 - m["clip_net_pct"], m["benford_ks"], m["score"],
       "WASH" if m["flag"] else ("control" if m["symbol"] == "MSTRX" else "ambiguous"))
    for m in REL)

cv = "".join(
    '<tr><td class="txt">%s</td><td class="num">%.1f%%</td><td class="num">%.1f%%</td></tr>'
    % (m["symbol"], m["gate_clip_share"] * 100, m["bybit_clip_share"] * 100) for m in C["markets"])

CSS = """
:root{--bg:#0e1116;--panel:#161b22;--border:#2d333b;--text:#e6edf3;--muted:#8b949e;--accent:#58a6ff;--accent-2:#f0883e;--bad:#f85149;--good:#3fb950;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;--mono:ui-monospace,Menlo,Consolas,monospace;}
*,*::before,*::after{box-sizing:border-box;} body{background:var(--bg);color:var(--text);font-family:var(--sans);margin:0;line-height:1.55;}
a{color:var(--accent);text-decoration:none;} a:hover{text-decoration:underline;}
header{border-bottom:1px solid var(--border);padding:30px 44px;background:linear-gradient(180deg,#161b22,#0e1116);}
header h1{margin:0 0 8px;font-size:23px;} header .meta{color:var(--muted);font-size:14px;}
main{padding:26px 44px;max-width:1180px;margin:0 auto;} .lead{font-size:16px;margin:0 0 22px;} .lead strong{color:var(--accent-2);}
.grid{display:grid;gap:15px;grid-template-columns:repeat(3,1fr);} @media(max-width:880px){.grid{grid-template-columns:1fr;}main,header{padding:18px 16px;}}
.stat{background:var(--panel);border:1px solid var(--border);padding:17px 19px;border-radius:10px;}
.stat .label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.4px;} .stat .value{font-size:25px;font-weight:700;margin-top:4px;font-family:var(--mono);}
.stat .sub{color:var(--muted);font-size:12px;margin-top:4px;} .stat.bad .value{color:var(--bad);} .stat.good .value{color:var(--good);} .stat.accent .value{color:var(--accent-2);}
section{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:20px 24px;margin:17px 0;}
section h2{margin:0 0 6px;font-size:18px;} section .sub{color:var(--muted);font-size:14px;margin-bottom:13px;}
.figure{background:#fff;border:1px solid var(--border);border-radius:8px;padding:8px;text-align:center;} .figure img{max-width:100%;height:auto;}
table{width:100%;border-collapse:collapse;margin:4px 0;font-size:13px;} th,td{border-bottom:1px solid var(--border);text-align:left;padding:6px 11px;}
th{color:var(--muted);font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:.4px;} td.num{font-family:var(--mono);text-align:right;} td.txt{font-family:var(--mono);}
tr.control td{background:rgba(63,185,80,.10);font-weight:600;} .tnote{color:var(--muted);font-size:12.5px;margin-top:10px;}
.keyfindings{background:linear-gradient(135deg,#1c232c,#161b22);border-left:3px solid var(--accent-2);} .keyfindings h2{color:var(--accent-2);}
footer{color:var(--muted);font-size:13px;padding:20px 44px;border-top:1px solid var(--border);margin-top:26px;}
.two{display:grid;grid-template-columns:1.1fr .9fr;gap:18px;} @media(max-width:880px){.two{grid-template-columns:1fr;}}
"""

H = next(m for m in C["markets"] if m["symbol"] == "HOODX")
HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Wash trading on Gate's tokenized stocks | Market Health</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><style>{CSS}</style></head><body>
<header><h1>Wash trading is the rule, not the exception, on Gate's tokenized stocks</h1>
<div class="meta">DN Institute Market Health Wiki | <a href="https://github.com/mkzung/gate-xstocks-wash-analysis">github.com/mkzung/gate-xstocks-wash-analysis</a> | Max Gorbuk<br>
Free, key-less Gate + Bybit public spot dumps | May 2026 | {S['universe_n']} markets screened</div></header>
<main>
<p class="lead">A detector scored every tokenized-stock market on Gate. Of the <strong>{S['reliable_n']}</strong> liquid enough to score, <strong>{S['n_flagged']}</strong> are flagged, with the threshold calibrated above three organic controls (same-class MicroStrategy and liquid SOL and LINK). The same tokens trade organically on Bybit, so the wash is the venue's, not the token's.</p>
<div class="grid">
  <div class="stat bad"><div class="label">Flagged on Gate</div><div class="value">{S['n_flagged']} / {S['reliable_n']}</div><div class="sub">score 0.83-0.99, above the MSTRX ({MST['score']:.2f}) and SOL (0.69) controls</div></div>
  <div class="stat accent"><div class="label">Same token, two venues</div><div class="value">{H['gate_clip_share']*100:.0f}% &rarr; {H['bybit_clip_share']*100:.0f}%</div><div class="sub">HOODX dominant clip: Gate vs Bybit</div></div>
  <div class="stat good"><div class="label">Wash onset (HOODX)</div><div class="value">Oct 2025</div><div class="sub">elevated clip; clearly washed by March 2026</div></div>
</div>
<section class="keyfindings"><h2>What the data says</h2><ol>
<li><b>The wash is pervasive.</b> Scoring all {S['universe_n']} markets on three signals (clip dominance, circularity, Benford break), {S['n_flagged']} of the {S['reliable_n']} liquid markets are flagged 0.83-0.99, above three organic controls (MSTRX {MST['score']:.2f}, liquid SOL 0.69, LINK 0.43); three more are ambiguous. 18 markets were too thin to score.</li>
<li><b>Circular volume.</b> The flagged markets run one fixed size that is 16-49% of trades while its buys and sells cancel (7-12% directional vs 94% for the control). It inflates the trade count, not the dollars (6.4%).</li>
<li><b>It is the venue, not the token.</b> The same five xStocks are washed on Gate (clip 17-49%) but organic on Bybit (2-6%). Same token, issuer and underlying; only the venue differs.</li>
<li><b>It has a start date.</b> HOODX was clean for three months; an elevated clip appeared Oct 2025 and crossed into clearly-washed territory from March 2026 as real volume faded. ${L['cumulative_clip_usd']/1e6:.2f}M manufactured on HOODX alone.</li>
<li><b>Unreachable by chance.</b> Resampling the organic controls (same-class and liquid), the top size never exceeds 8% in 3,000 draws; the flagged 16-49% sits far outside the null (p &lt; 1/3000). Cheap to run, which is why it is widespread.</li>
</ol></section>
<section><h2>The screen: every liquid tokenized-stock market on Gate</h2><div class="sub">Non-organic-activity score (geometric mean of clip dominance, circularity and Benford break). {S['n_flagged']} of {S['reliable_n']} flagged, above the same-class (MSTRX) and liquid (SOL, LINK) controls.</div><div class="figure"><img src="data:image/png;base64,{fig['screen.png']}" alt="venue screen"></div>
<table><thead><tr><th>#</th><th>market</th><th>name</th><th>trades</th><th>clip</th><th>circ</th><th>KS</th><th>score</th><th>flag</th></tr></thead><tbody>{rows}</tbody></table>
<div class="tnote">circ = circularity (1 - net directional of the clip): near 1 = buys and sells cancel (wash); the MSTRX control (shaded) takes a side. 18 markets with &lt; 5,000 trades were too thin to score.</div></section>
<section><h2>It is the venue, not the token</h2><div class="sub">Dominant clip share of the same five xStocks on Gate vs Bybit, May 2026.</div>
<div class="two"><div class="figure"><img src="data:image/png;base64,{fig['crossvenue.png']}" alt="cross venue"></div>
<table><thead><tr><th>market</th><th>clip on Gate</th><th>clip on Bybit</th></tr></thead><tbody>{cv}</tbody></table></div></section>
<section><h2>When it started</h2><div class="sub">HOODX dominant-clip share (bars) and score (line) by month since listing. Clean at launch, elevated from Oct 2025, clearly washed from March 2026.</div><div class="figure"><img src="data:image/png;base64,{fig['longitudinal.png']}" alt="onset"></div></section>
<section><h2>The mechanism: circular volume and a broken first digit</h2><div class="sub">On the six largest flagged markets: the dominant clip nets to almost no position (left) and breaks Benford's law (right); the MicroStrategy control does neither.</div>
<div class="two"><div class="figure"><img src="data:image/png;base64,{fig['circular-volume.png']}" alt="circular volume"></div><div class="figure"><img src="data:image/png;base64,{fig['benford.png']}" alt="benford"></div></div></section>
<footer>Data: Gate (download.gatedata.org) and Bybit (public.bybit.com) public spot dumps, May 2026, free and key-less. Reproducible: screen.py, longitudinal.py, crossvenue.py, verify.py. A flag on reported activity, not an attribution of who placed the orders or why (manipulation or reward-farming of Gate's xStocks incentive programmes).</footer>
</main></body></html>"""

for name in ("index.html", "dashboard.html"):
    open(os.path.join(ROOT, name), "w").write(HTML)
print("wrote index.html + dashboard.html (%d bytes)" % len(HTML))
