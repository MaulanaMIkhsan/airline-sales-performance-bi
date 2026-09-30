"""Renders README preview charts from data/model (static PNGs for GitHub).
The numbers are computed the same way the DAX measures compute them."""
import pathlib, duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = pathlib.Path(__file__).resolve().parents[1]
D, IMG = ROOT / "data" / "model", ROOT / "docs" / "img"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, BG = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": .8, "axes.axisbelow": True, "figure.facecolor": BG, "axes.facecolor": BG})
con = duckdb.connect()
con.execute(f"CREATE VIEW f AS SELECT * FROM read_csv_auto('{D}/fact_sales_flown.csv')")
con.execute(f"CREATE VIEW s2f AS SELECT * FROM read_csv_auto('{D}/fact_sales_to_flown.csv')")
con.execute(f"CREATE VIEW bp AS SELECT * FROM read_csv_auto('{D}/fact_booking_position.csv')")
asof = con.execute('SELECT MAX("DATES") FROM f').fetchone()[0]
def title(ax, t, sub):
    ax.set_title(t, loc="left", fontsize=13, color=INK, fontweight="bold", pad=22)
    ax.text(0, 1.02, sub, transform=ax.transAxes, color=INK2, fontsize=9.5)
def save(fig, name):
    fig.tight_layout()
    fig.savefig(IMG / name, dpi=160)
    plt.close(fig)
# 1. monthly flown revenue TY vs LY (capped at cut-off like [Revenue TY]/[Revenue LY])
m = con.execute(f"""SELECT month("DATES") m, year("DATES") y, SUM("NETT USD")/1e6 usd FROM f
    WHERE "DATA TYPE"='Sales' AND "DATES" <= DATE '{asof:%Y-%m-%d}' GROUP BY ALL ORDER BY 2,1""").df()
fig, ax = plt.subplots(figsize=(9, 4.2))
for y, c in [(2025, S2), (2026, S1)]:
    d = m[m.y == y]
    ax.plot(d.m, d.usd, color=c, lw=2, marker="o", ms=4)
    ax.annotate(str(y), (d.m.iloc[-1], d.usd.iloc[-1]), xytext=(6, 0), textcoords="offset points", color=INK, va="center", fontsize=9.5)
ax.set_xticks(range(1, 13), ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])
ax.set_ylabel("Sales revenue (USD m)")
ax.set_ylim(0, None)
title(ax, "Sales revenue by month, 2026 vs 2025", f"Synthetic data, cut-off {asof:%d %b %Y}. Eid al-Fitr travel (late Mar 2025, mid Mar 2026) drives the March spike.")
save(fig, "01_revenue_ty_ly.png")
# 2. booking curve
b = con.execute("""SELECT CASE WHEN sales_to_flown=0 THEN 'H' WHEN sales_to_flown<=7 THEN 'H-1..7' WHEN sales_to_flown<=30 THEN 'H-8..30'
    WHEN sales_to_flown<=60 THEN 'H-31..60' WHEN sales_to_flown<=120 THEN 'H-61..120' ELSE 'H-121+' END g,
    MIN(sales_to_flown) o, SUM(pax) p FROM s2f GROUP BY 1 ORDER BY o""").df()
b["pct"] = b.p / b.p.sum() * 100
fig, ax = plt.subplots(figsize=(9, 4))
bars = ax.bar(b.g, b.pct, color=S1, width=.6)
for r, v in zip(bars, b.pct):
    ax.text(r.get_x() + r.get_width() / 2, v + .6, f"{v:.0f}%", ha="center", color=INK, fontsize=9.5)
ax.set_ylabel("% of flown pax")
ax.grid(axis="x", visible=False)
title(ax, "Booking curve: when passengers buy", "Days between ticket issue and departure (H = departure day). Feeds the lead-time page and the sales-to-flown groups.")
save(fig, "02_booking_curve.png")
# 3. fare family revenue mix by area
fam = {"FPA JCDI":"FPAJCDI","ROX":"ROX","Y":"Y","WBMKN":"WBMKN","QTV":"QTV","SHL":"SHL"}
mp = {c: k for k, v in fam.items() for c in v}
r = con.execute('SELECT "AREA" a, SUBCLASS s, SUM("NETT USD") usd FROM f WHERE "DATA TYPE"=\'Sales\' AND year("DATES")=2026 GROUP BY ALL').df()
r["fam"] = r.s.map(mp).fillna("Other")
pv = r.pivot_table(index="fam", columns="a", values="usd", aggfunc="sum").fillna(0)
pv = (pv / pv.sum() * 100).reindex(["FPA JCDI","ROX","Y","WBMKN","QTV","SHL","Other"])
fig, ax = plt.subplots(figsize=(9, 4.4))
w = .26
x = range(len(pv))
for i, (a, c) in enumerate([("DOM", S1), ("INT", S2), ("MEA", S3)]):
    ax.bar([k + (i - 1) * w for k in x], pv[a], width=w - .03, color=c, label=a)
ax.set_xticks(list(x), pv.index)
ax.set_ylabel("% of area revenue")
ax.grid(axis="x", visible=False)
ax.legend(frameon=False, ncol=3, loc="upper right")
title(ax, "Revenue mix by fare family, 2026 YTD", "One [Fare Family Share %] measure replaces 26 per-RBD measures + 6 hard-coded mix measures.")
save(fig, "03_fare_family_mix.png")
# 4. BLF next 12 months
l = con.execute(f"""SELECT date_trunc('month', STD) mth, SUM(Book_Total)*100.0/SUM(Capacity_Total) blf FROM bp WHERE STD >= date_trunc('month', DATE '{asof:%Y-%m-%d}') + INTERVAL 1 MONTH GROUP BY 1 ORDER BY 1""").df()
fig, ax = plt.subplots(figsize=(9, 4))
bars = ax.bar(l.mth.dt.strftime("%b\n%Y"), l.blf, color=S1, width=.6)
for rr, v in zip(bars, l.blf):
    ax.text(rr.get_x() + rr.get_width() / 2, v + 1, f"{v:.0f}%", ha="center", color=INK, fontsize=9)
ax.set_ylabel("Booked load factor")
ax.set_ylim(0, 100)
ax.grid(axis="x", visible=False)
title(ax, "Forward booked load factor, next 12 months", "Seats sold / seats offered on scheduled flights. Near months fill first; Mar 2027 (Eid) books ahead.")
save(fig, "04_forward_blf.png")
print("previews written to", IMG)
