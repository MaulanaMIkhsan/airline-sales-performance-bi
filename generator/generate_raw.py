"""Synthetic airline sales & flown coupon generator.
Produces coupon-level raw tables that mimic a typical airline revenue-accounting extract
(sales by date of issue, flown by date of travel) plus reference tables.
Everything here is fictional: carrier "XA / Archipelago Air", agents, corporates, fares and volumes.
Only public IATA airport codes are real.
Usage: python generator/generate_raw.py --asof 2026-09-29 --scale 1.0 --seed 42
"""
import argparse, pathlib
import numpy as np, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
# ---------------- reference data ----------------
# dest, service, subservice (sales region), base one-way fare USD, aircraft, weight
ROUTES = [
    ("DPS","DOM","DPS",95,"B738",14),("SUB","DOM","SUB",70,"B738",10),("KNO","DOM","MES",110,"A330",9),
    ("UPG","DOM","UPG",120,"B738",8),("BPN","DOM","UPG",115,"B738",5),("YIA","DOM","JKT",60,"B738",6),
    ("SRG","DOM","JKT",55,"ATR72",3),("PDG","DOM","MES",95,"B738",4),("PLM","DOM","MES",65,"B738",4),
    ("PKU","DOM","MES",85,"B738",3),("BTH","DOM","MES",80,"B738",3),("PNK","DOM","JKT",85,"B738",3),
    ("BDJ","DOM","JKT",90,"B738",3),("MDC","DOM","UPG",175,"B738",2),("DJJ","DOM","UPG",230,"B738",3),
    ("LOP","DOM","DPS",100,"B738",2),("SOC","DOM","JKT",60,"ATR72",2),("TNJ","DOM","MES",90,"ATR72",1),
    ("MLG","DOM","SUB",65,"ATR72",1),("BKS","DOM","MES",75,"ATR72",1),
    ("SIN","INT","ASA",210,"B738",6),("KUL","INT","ASA",190,"B738",3),("BKK","INT","ASA",260,"A330",2),
    ("HKG","INT","CTH",380,"A330",2),("PVG","INT","CTH",430,"A330",1),("CAN","INT","CTH",390,"A330",1),
    ("NRT","INT","JPK",620,"A330",3),("ICN","INT","JPK",540,"A330",2),("SYD","INT","SWP",560,"A330",2),
    ("MEL","INT","SWP",580,"A330",1),("JED","INT","MEA",780,"B777",5),("DOH","INT","MEA",690,"A330",1),
    ("AMS","INT","EUR",980,"B777",1),
]
PULL_OUT = {"TNJ","MLG","BKS","CAN"}          # routes discontinued during 2026 (synthetic scenario)
PULL_OUT_DATE = pd.Timestamp("2026-04-01")
CAPACITY = {"B738":162,"A330":360,"B777":393,"ATR72":70}
RBD = list("FRPAJCDOIZYWBMKNGQTVSHLEUX")
RBD_MULT = np.array([5.0,4.6,4.2,3.8,3.2,2.9,2.6,2.35,2.15,2.0,1.6,1.45,1.35,1.25,1.15,1.05,.98,.9,.83,.76,.7,.64,.58,.52,.46,.4])
RBD_W = np.array([.2,.2,.2,.3,1.2,1.1,1.0,.9,.8,.6,4,4,5,6,7,8,8,9,9,8,7,6,5,3,2,1.5])
CHANNELS = [("CTO","DIRECT OFFICE",.10),("ATO","DIRECT OFFICE",.05),("GSA","GSA",.06),("TA","TRAVEL AGENT",.30),
            ("CONS","TRAVEL AGENT",.07),("WEB","WEB/MOB",.14),("MOB","WEB/MOB",.10),("OTA","OTA",.18)]
BRANCHES = [("JKT","Region 1 - Jabodetabek"),("BDO","Region 1 - Jabodetabek"),("SUB","Region 2 - Java East"),
            ("DPS","Region 3 - Bali Nusra"),("KNO","Region 4 - Sumatra"),("UPG","Region 5 - Sulawesi Papua"),
            ("BPN","Region 6 - Kalimantan"),("SIN","Region 7 - International")]
CITY_BO = {"CGK":"JKT","DPS":"DPS","SUB":"SUB","KNO":"KNO","UPG":"UPG","BPN":"BPN","SIN":"SIN"}
INDUSTRIES = ["Energy","Mining","Banking","Telco","FMCG","Government","Healthcare","Construction","Logistics","Education"]
CLUSTERS = ["GOVERNMENT","SOE","PRIVATE","CHA/TMC"]
AGENT_WORDS = ["Samudra","Cahaya","Bintang","Nusa","Pelangi","Kenari","Harmoni","Mentari","Angkasa","Lestari",
               "Kencana","Sentosa","Permata","Rajawali","Merak","Sinar","Delta","Orion","Atlas","Zenith"]
def build_refs(rng):
    routes = pd.DataFrame(ROUTES, columns=["dest","service_type","subservice","base_fare","aircraft","weight"])
    routes["route_vv"] = "CGK" + routes.dest + "CGK"
    routes["status"] = np.where(routes.dest.isin(PULL_OUT), "Pull Out", "Active")
    routes["growth_2026"] = np.round(rng.normal(1.06, .08, len(routes)), 3)
    ch = pd.DataFrame(CHANNELS, columns=["channel","channel_group","weight"])
    bo = pd.DataFrame(BRANCHES, columns=["bo","region"])
    n_agents = 180
    ag = pd.DataFrame({"agent_no": [f"99{rng.integers(100000,999999)}" for _ in range(n_agents)]}).drop_duplicates()
    ag["agent_name"] = [f"{rng.choice(AGENT_WORDS)} Travel {i:03d}" for i in range(len(ag))]
    ag["branch_office"] = rng.choice(bo.bo, len(ag), p=[.45,.08,.12,.1,.08,.07,.05,.05])
    ag["agent_grouping"] = rng.choice(["RETAIL","CONSOLIDATOR","OTA","TMC","HAJJ/UMRAH"], len(ag), p=[.5,.15,.1,.15,.1])
    ag["poi"] = ag.branch_office.replace({"JKT":"JKT","BDO":"BDO"})
    ag["weight"] = rng.pareto(1.3, len(ag)) + .1       # few large agents, long tail
    n_corp = 70
    corp = pd.DataFrame({"corporate_code": [f"CRP{i:04d}" for i in range(1, n_corp+1)]})
    corp["industry_type"] = rng.choice(INDUSTRIES, n_corp)
    corp["corporate_cluster"] = np.where(corp.industry_type.eq("Government"), "GOVERNMENT", rng.choice(CLUSTERS[1:], n_corp, p=[.3,.55,.15]))
    corp["corporate_name"] = [f"Contoso {ind} {i:02d}" for i, ind in enumerate(corp.industry_type, 1)]
    corp["weight"] = rng.pareto(1.5, n_corp) + .1
    return routes, ch, bo, ag, corp
# ---------------- demand shape ----------------
EID = {2024: "2024-04-10", 2025: "2025-03-31", 2026: "2026-03-20", 2027: "2027-03-10"}   # approx Eid al-Fitr dates
def travel_season(d):
    d = pd.DatetimeIndex(d)
    f = np.ones(len(d))
    for y, e in EID.items():
        gap = (d - pd.Timestamp(e)).days.values
        f += 0.9 * np.exp(-((gap + 4) ** 2) / 40)      # pre-Eid mudik peak
        f += 0.6 * np.exp(-((gap - 7) ** 2) / 30)      # post-Eid return peak
    md = d.month * 100 + d.day
    f += np.where((md >= 1218) | (md <= 104), .45, 0)        # year-end holidays
    f += np.where((md >= 620) & (md <= 715), .35, 0)         # school holidays
    f *= np.select([d.dayofweek == 4, d.dayofweek == 6, d.dayofweek == 1], [1.18, 1.15, .88], 1.0)
    return f
def gen_bookings(rng, start, asof, scale, refs):
    routes, ch, bo, ag, corp = refs
    horizon = asof + pd.Timedelta(days=330)
    issue_days = pd.date_range(start, asof)
    # issue-day volume: base * growth * weekday effect (fewer issues on weekends)
    lam = 62 * scale * np.where(issue_days.dayofweek >= 5, .75, 1.08) * np.where(issue_days.year >= 2026, 1.05, 1.0)
    n = rng.poisson(lam)
    doi = np.repeat(issue_days.values, n)
    N = len(doi)
    # lead time mixture, then accept/reject by travel seasonality so peaks get booked earlier
    comp = rng.choice(4, N, p=[.27,.40,.23,.10])
    lead = np.select([comp == 0, comp == 1, comp == 2], [rng.integers(0,8,N), rng.integers(8,31,N), rng.integers(31,91,N)], rng.integers(91,220,N))
    dot = pd.DatetimeIndex(doi) + pd.to_timedelta(lead, "D")
    keep = rng.random(N) < travel_season(dot) / 2.4
    doi, lead, dot = doi[keep], lead[keep], dot[keep]
    N = len(doi)
    r = rng.choice(len(routes), N, p=routes.weight / routes.weight.sum())
    rt = routes.iloc[r].reset_index(drop=True)
    # 2026 growth per route and pull-out cut-off
    g = np.where(dot.year >= 2026, rt.growth_2026.values, 1.0)
    alive = ~((rt.status.values == "Pull Out") & (dot >= PULL_OUT_DATE))
    keep = (rng.random(N) < g / 1.3) & alive
    idx = np.flatnonzero(keep)
    b = pd.DataFrame({"doi": pd.DatetimeIndex(doi[idx]), "dot": dot[idx], "lead": lead[idx]})
    b = pd.concat([b, rt.iloc[idx].reset_index(drop=True)], axis=1)
    N = len(b)
    b["booking_id"] = np.arange(1, N + 1)
    b["party"] = rng.choice([1,1,1,2,2,3,4,6], N)
    ci = rng.choice(len(ch), N, p=ch.weight / ch.weight.sum())
    b["channel"] = ch.channel.values[ci]
    agent_ch = b.channel.isin(["TA","CONS","GSA","OTA"])
    ai = rng.choice(len(ag), N, p=ag.weight / ag.weight.sum())
    for c in ["agent_no","agent_name","branch_office","agent_grouping","poi"]:
        b[c] = np.where(agent_ch, ag[c].values[ai], None)
    direct_bo = rng.choice(bo.bo, N, p=[.5,.05,.12,.1,.08,.07,.05,.03])
    b["branch_office"] = b.branch_office.fillna(pd.Series(direct_bo))
    b["poi"] = b.poi.fillna(b.branch_office)
    b["agent_no"] = b.agent_no.fillna(pd.Series(np.where(b.channel.isin(["WEB","MOB"]), "99000001", "99000002")))
    b["agent_name"] = b.agent_name.fillna(pd.Series(np.where(b.channel.isin(["WEB","MOB"]), "XA DIRECT ONLINE", "XA SALES OFFICE")))
    b["agent_grouping"] = b.agent_grouping.fillna("DIRECT")
    # corporate deals: shorter lead, higher classes
    is_corp = (rng.random(N) < np.where(b.lead < 15, .38, .18)) & ~b.channel.isin(["OTA"])
    cj = rng.choice(len(corp), N, p=corp.weight / corp.weight.sum())
    b["corporate"] = np.where(is_corp, rng.choice(["corp","corv","corx"], N, p=[.7,.2,.1]), "")
    b["corporate_code"] = np.where(is_corp, corp.corporate_code.values[cj], None)
    # RBD: late bookings / corporates skew up the fare ladder
    tilt = np.clip(1 - b.lead.values / 60, 0, 1) * .8 + np.asarray(is_corp) * .6
    k = np.arange(26)
    logits = np.log(RBD_W)[None, :] + tilt[:, None] * (-(k[None, :] - 10) / 6)
    p = np.exp(logits); p /= p.sum(1, keepdims=True)
    rbd_i = (p.cumsum(1) > rng.random(N)[:, None]).argmax(1)
    b["subclass"] = np.array(RBD)[rbd_i]
    season_prem = 1 + .25 * (travel_season(b["dot"]) - 1)
    b["fare_ow"] = np.round(b.base_fare * RBD_MULT[rbd_i] * season_prem * rng.lognormal(0, .12, N), 2)
    # trip shape
    b["trip_type"] = np.where(rng.random(N) < .55, "RT", "OW")
    dur = np.select([rng.random(N) < .35], [rng.integers(1, 4, N)], rng.choice([4,5,6,7,8,10,12,14,18,25,40], N))
    b["trip_duration"] = np.where(b.trip_type == "RT", dur, 0)
    b["bo_poo"] = "JKT"
    return b[b["dot"] <= horizon].reset_index(drop=True)
def explode_coupons(rng, b, asof):
    t = b.loc[b.index.repeat(b.party)].reset_index(drop=True)
    t["ticket_no"] = (9900000000000 + np.arange(1, len(t) + 1)).astype(str)
    t["doctype"] = rng.choice(["PAX","FIM","EMD"], len(t), p=[.97,.015,.015])
    t["oprt_aln"] = rng.choice(["XA","//","/-"], len(t), p=[.985,.01,.005])
    c1 = t.assign(coupon_no=1, route=t.route_vv.str[:3] + t.dest, cpn_dot=t["dot"])
    rt = t[t.trip_type == "RT"]
    c2 = rt.assign(coupon_no=2, route=rt.dest + "CGK", cpn_dot=rt["dot"] + pd.to_timedelta(rt.trip_duration, "D"))
    c = pd.concat([c1, c2], ignore_index=True)
    c["route_vv"] = np.where(c.trip_type == "RT", c.route_vv, "CGK" + c.dest)
    n = len(c)
    c["note"] = (c.coupon_no == 1).astype(int)          # first-coupon flag used for flown pax counting
    refunded = rng.random(n) < .035
    noshow = rng.random(n) < .02
    c["cpnsts"] = np.select([refunded, c.cpn_dot > asof, noshow], ["Refunded", "Unutilised", "Unutilised"], "Flown")
    c["gross_usd"] = np.round(c.fare_ow * rng.lognormal(0, .03, n), 2)
    c["disc_usd"] = np.round(np.where(c.corporate != "", c.gross_usd * rng.uniform(.05, .15, n), c.gross_usd * rng.uniform(0, .03, n)), 2)
    c["yq_usd"] = np.round(np.where(c.service_type == "INT", rng.uniform(30, 90, n), rng.uniform(5, 15, n)), 2)
    c["doi"] = c.doi.dt.normalize()
    c["dot"] = c.cpn_dot.dt.normalize()
    cols = ["ticket_no","coupon_no","note","doi","dot","doctype","cpnsts","oprt_aln","service_type","subservice","agent_no",
            "agent_name","agent_grouping","poi","branch_office","route_vv","route","corporate_code","corporate","channel",
            "subclass","bo_poo","gross_usd","disc_usd","yq_usd","trip_type","trip_duration","aircraft"]
    return c[cols].rename(columns={"service_type":"servicetypecode","subservice":"subservicecode","channel":"channel_iata"})
def booking_position(rng, routes, asof):
    days = pd.date_range(asof + pd.Timedelta(days=1), asof + pd.Timedelta(days=365))
    rows = []
    fn = 400
    for rt in routes.itertuples():
        if rt.status == "Pull Out":
            continue
        freq = max(1, round(rt.weight / 3))
        for leg, (o, d) in enumerate([("CGK", rt.dest), (rt.dest, "CGK")]):
            for f in range(freq):
                fn += 2
                std = days + pd.Timedelta(hours=6 + 3 * f + 2 * leg)
                cap = np.full(len(days), CAPACITY[rt.aircraft])
                out = (days - asof).days.values
                lf = (.86 - .62 * (1 - np.exp(-out / 45))) * travel_season(days) ** .6 * rng.normal(1, .07, len(days))
                book = np.clip(np.round(cap * lf), 0, cap).astype(int)
                rows.append(pd.DataFrame({"RegionCode": rt.subservice, "FltNbr": fn + leg, "STD": std, "DOW": std.dayofweek + 1,
                    "Bulan": std.month, "Tahun": std.year, "FlightType": "J", "SubServiceCode": rt.subservice,
                    "ServiceTypeCode": rt.service_type, "TipeAircraft": rt.aircraft, "RouteVV": rt.route_vv,
                    "Route": f"{o}{d}", "Depart": o, "Arrived": d, "DiffDate": out, "Book_Total": book, "Capacity_Total": cap}))
    return pd.concat(rows, ignore_index=True)
def group_bookings(rng, routes, ag, corp, asof):
    n = 420
    tgl = pd.to_datetime(rng.integers(pd.Timestamp("2026-01-02").value // 10**9, asof.value // 10**9, n), unit="s").normalize()
    act = routes[routes.status == "Active"]
    r = act.sample(n, replace=True, weights=act.weight, random_state=1).reset_index(drop=True)
    dept = tgl + pd.to_timedelta(rng.integers(20, 200, n), "D")
    pax = rng.choice([10,12,15,20,25,30,40,45,60,90], n)
    fare = np.round(r.base_fare.values * rng.uniform(.8, 1.3, n) * 16300 / 1000) * 1000   # IDR
    yq = np.where(r.service_type == "INT", 850000, 150000)
    tax = np.where(r.service_type == "INT", 1100000, 180000)
    status = rng.choice(["TICKETED","DEPOSIT","OPTION","CANCELLED"], n, p=[.45,.25,.15,.15])
    mkt = rng.choice(["AGENT","CORP","PRIVATE"], n, p=[.6,.25,.15])
    ai = rng.integers(0, len(ag), n)
    cj = rng.integers(0, len(corp), n)
    dep_pax = np.where(np.isin(status, ["TICKETED","DEPOSIT"]), pax, 0)
    gb = pd.DataFrame({"MO": tgl.month, "WEEK": tgl.isocalendar().week.values, "TGL BOOKING": tgl,
        "PNR": ["".join(rng.choice(list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789"), 6)) for _ in range(n)],
        "NAMA GROUP": [f"Group {i:04d}" for i in range(1, n + 1)], "AGENT TRAVEL": ag.agent_name.values[ai],
        "AGENT/CORP/PRIVATE": mkt, "DEPT.DATE": dept, "RETURN DATE": dept + pd.to_timedelta(rng.integers(3, 12, n), "D"),
        "ROUTE": r.route_vv.values, "DEST": r.dest.values, "DOM/INT": np.where(r.service_type == "DOM", "D", "I"),
        "TTL PAX": pax, "MARKET": r.subservice.values, "APPROVED SKN FARE - IDR.": fare.astype(int), "YQ": yq, "TAX ++": tax})
    gb["NETT SALES"] = gb["APPROVED SKN FARE - IDR."] + gb.YQ + gb["TAX ++"]
    gb["Nett Sales ( basic + yq )"] = gb["APPROVED SKN FARE - IDR."] + gb.YQ
    gb["Total sales ( nett x ttl pax )"] = gb["Nett Sales ( basic + yq )"] * gb["TTL PAX"]
    gb["FARE BASIC"] = rng.choice(["GVXA1","GVXA2","GRPEC","GRPUM"], n)
    gb["STATUS"] = status
    gb["DATE OF DEPOSIT"] = np.where(dep_pax > 0, tgl + pd.to_timedelta(rng.integers(1, 10, n), "D"), pd.NaT)
    gb["JMLH PAX DEPO"] = dep_pax
    gb["JLMH DEPOSIT(idr)"] = (dep_pax * gb["APPROVED SKN FARE - IDR."] * .2).round(-3).astype(int)
    gb["REASON CANCEL"] = np.where(status == "CANCELLED", rng.choice(["Price","Schedule change","Group size dropped","Moved to competitor"], n), None)
    gb["CORP CODE"] = np.where(mkt == "CORP", corp.corporate_code.values[cj], None)
    gb["TIME LIMIT"] = tgl + pd.to_timedelta(14, "D")
    gb["POI"] = "JKT"
    gb["DOI"] = np.where(status == "TICKETED", dept - pd.to_timedelta(rng.integers(7, 20, n), "D"), pd.NaT)
    for c in ["TGL BOOKING","DEPT.DATE","RETURN DATE","DATE OF DEPOSIT","TIME LIMIT","DOI"]:
        gb[c] = pd.to_datetime(gb[c]).dt.strftime("%Y-%m-%d")
    return gb
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default="2026-09-29")
    ap.add_argument("--scale", type=float, default=2.5)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    asof = pd.Timestamp(a.asof)
    RAW.mkdir(parents=True, exist_ok=True)
    refs = build_refs(rng)
    routes, ch, bo, ag, corp = refs
    b = gen_bookings(rng, pd.Timestamp("2024-06-01"), asof, a.scale, refs)
    c = explode_coupons(rng, b, asof)
    # split like the source system: yearly sales tables (by DOI) and flown tables (by DOT, flown only)
    for y in (2025, 2026):
        c[c.doi.dt.year == y].to_parquet(RAW / f"sales_{y}.parquet", index=False)
        c[(c["dot"].dt.year == y) & (c.cpnsts == "Flown")].to_parquet(RAW / f"flown_{y}.parquet", index=False)
    ch[["channel","channel_group"]].rename(columns={"channel":"Channel","channel_group":"Grouping_channel"}).to_csv(RAW / "ref_channel_group.csv", index=False)
    corp[["corporate_code","corporate_name","corporate_cluster","industry_type"]].to_csv(RAW / "ref_corporate.csv", index=False)
    bo.rename(columns={"bo":"BO","region":"REGION"}).to_csv(RAW / "ref_branch_region.csv", index=False)
    routes[["route_vv","dest","service_type","subservice","aircraft","status"]].to_csv(RAW / "ref_route.csv", index=False)
    booking_position(rng, routes, asof).to_parquet(RAW / "booking_position.parquet", index=False)
    group_bookings(rng, routes, ag, corp, asof).to_csv(RAW / "group_bookings.csv", index=False)
    print(f"bookings={len(b):,} coupons={len(c):,} flown2025={((c['dot'].dt.year==2025)&(c.cpnsts=='Flown')).sum():,}")
if __name__ == "__main__":
    main()
