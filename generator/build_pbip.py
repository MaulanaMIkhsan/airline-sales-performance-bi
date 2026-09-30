"""Builds the Power BI Project (PBIP): semantic model as a TMDL folder + report pages in PBIR format.
Open powerbi/AirlineSalesPerformance.pbip in Power BI Desktop, then Refresh.
Usage: python generator/build_pbip.py --data-folder "C:\\path\\to\\airline-sales-performance-bi\\data\\model"
"""
import argparse, hashlib, json, pathlib, re, shutil
import build_tmdl as bt
ROOT = pathlib.Path(__file__).resolve().parents[1]
NAME = "AirlineSalesPerformance"
PB = ROOT / "powerbi"
SM, RP = PB / f"{NAME}.SemanticModel", PB / f"{NAME}.Report"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
THEME = {"name": "Archipelago", "dataColors": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
         "foreground": "#0b0b0b", "foregroundNeutralSecondary": "#52514e", "background": "#ffffff", "backgroundLight": "#f5f5f3",
         "tableAccent": "#2a78d6", "good": "#1baf7a", "bad": "#e34948", "neutral": "#eda100",
         "textClasses": {"title": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": "#0b0b0b"},
                         "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 24, "color": "#0b0b0b"},
                         "label": {"fontFace": "Segoe UI", "fontSize": 10, "color": "#52514e"}},
         "visualStyles": {"*": {"*": {"border": [{"show": True, "color": {"solid": {"color": "#e6e5e0"}}, "radius": 8}],
                                      "background": [{"show": True, "color": {"solid": {"color": "#ffffff"}}}]}},
                          "page": {"*": {"background": [{"color": {"solid": {"color": "#f5f5f3"}}, "transparency": 0}]}}}}
def uid(*parts):
    return hashlib.md5("|".join(parts).encode()).hexdigest()[:20]
def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
def lit(v):
    return {"expr": {"Literal": {"Value": v}}}
# ---------------------------------------------------------------- semantic model (TMDL folder)
def write_semantic_model(data_folder):
    script = bt.tmdl().replace("C:\\airline-sales-performance-bi\\data\\model", data_folder)
    blocks, cur = [], None
    for line in script.splitlines()[1:]:                      # drop "createOrReplace"
        if re.match(r"^\t(table|relationship|expression) ", line):
            cur = [line[1:]]
            blocks.append(cur)
        elif cur is not None:
            cur.append(line[1:] if line.startswith("\t") else line)
    if SM.exists():
        shutil.rmtree(SM)
    d = SM / "definition"
    (d / "tables").mkdir(parents=True)
    rels, exprs, tables = [], [], []
    for b in blocks:
        text = "\n".join(b).rstrip() + "\n"
        kind, name = b[0].split(" ", 1)
        if kind == "table":
            tables.append(name)
            (d / "tables" / f"{name.strip(chr(39))}.tmdl").write_text(text, encoding="utf-8")
        elif kind == "relationship":
            rels.append(text)
        else:
            exprs.append(text)
    (d / "relationships.tmdl").write_text("\n".join(rels), encoding="utf-8")
    (d / "expressions.tmdl").write_text("\n".join(exprs), encoding="utf-8")
    (d / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1601\n", encoding="utf-8")
    model = ["model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3", "\tdiscourageImplicitMeasures",
             "\tsourceQueryCulture: en-US", "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
             "annotation __PBI_TimeIntelligenceEnabled = 0", "", "annotation PBI_QueryOrder = " + json.dumps(list(bt.CSV_TABLES)), ""]
    model += [f"ref table {t}" for t in tables]
    (d / "model.tmdl").write_text("\n".join(model) + "\n", encoding="utf-8")
    dump(SM / "definition.pbism", {"$schema": f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json", "version": "4.2", "settings": {}})
# ---------------------------------------------------------------- report visuals
def col(entity, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}
def mea(prop, entity="_Measures"):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}
def ref(f):
    k = "Column" if "Column" in f else "Measure"
    return f"{f[k]['Expression']['SourceRef']['Entity']}.{f[k]['Property']}"
def container(page, key, vtype, pos, roles=None, title=None, objects=None, sort=None):
    x, y, w, h = pos
    v = {"visualType": vtype, "drillFilterOtherVisuals": True}
    if roles:
        v["query"] = {"queryState": {r: {"projections": [{"field": f, "queryRef": ref(f), **({"active": True} if "Column" in f else {})} for f in fs]}
                                     for r, fs in roles.items()}}
        if sort:
            v["query"]["sortDefinition"] = {"sort": [{"field": f, "direction": d} for f, d in sort]}
    if vtype in ("lineChart", "clusteredBarChart", "clusteredColumnChart") and not objects:
        objects = {"valueAxis": [{"properties": {"showAxisTitle": lit("false")}}], "categoryAxis": [{"properties": {"showAxisTitle": lit("false")}}]}
    if objects:
        v["objects"] = objects
    c = {"$schema": f"{SCHEMA}/item/report/definition/visualContainer/2.0.0/schema.json", "name": uid(page, key),
         "position": {"x": x, "y": y, "z": 1000, "height": h, "width": w, "tabOrder": 1000}, "visual": v}
    if title:
        v["visualContainerObjects"] = {"title": [{"properties": {"show": lit("true"), "text": lit(f"'{title}'")}}]}
    return key, c
def textbox(page, key, pos, text, sub=None):
    runs = [{"value": text, "textStyle": {"fontWeight": "bold", "fontSize": "20pt", "color": "#0b0b0b"}}]
    paras = [{"textRuns": runs}]
    if sub:
        paras.append({"textRuns": [{"value": sub, "textStyle": {"fontSize": "10pt", "color": "#52514e"}}]})
    k, c = container(page, key, "textbox", pos, objects={"general": [{"properties": {"paragraphs": paras}}]})
    c["visual"]["visualContainerObjects"] = {"border": [{"properties": {"show": lit("false")}}], "background": [{"properties": {"show": lit("false")}}]}
    return k, c
def slicer(page, key, pos, field, title, mode="Dropdown", default=None, single=False):
    objs = {"data": [{"properties": {"mode": lit(f"'{mode}'")}}], "header": [{"properties": {"show": lit("false")}}]}
    if single:
        objs["selection"] = [{"properties": {"singleSelect": lit("true")}}]
    if isinstance(default, tuple):
        e = field["Column"]
        c = {"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": e["Property"]}}
        cmp = lambda k, d: {"Comparison": {"ComparisonKind": k, "Left": c, "Right": {"Literal": {"Value": f"datetime'{d}T00:00:00'"}}}}
        objs["general"] = [{"properties": {"filter": {"filter": {"Version": 2, "From": [{"Name": "s", "Entity": e["Expression"]["SourceRef"]["Entity"], "Type": 0}],
            "Where": [{"Condition": {"And": {"Left": cmp(2, default[0]), "Right": cmp(3, default[1])}}}]}}}}]
    elif default:
        e = field["Column"]
        objs["general"] = [{"properties": {"filter": {"filter": {"Version": 2, "From": [{"Name": "s", "Entity": e["Expression"]["SourceRef"]["Entity"], "Type": 0}],
            "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": e["Property"]}}],
                                            "Values": [[{"Literal": {"Value": f"{default}L" if isinstance(default, int) else f"'{default}'"}}]]}}}]}}}}]
    return container(page, key, "slicer", pos, {"Values": [field]}, title, objs)
def card(page, key, pos, measure):
    return container(page, key, "card", pos, {"Values": [mea(measure)]},
                     objects={"labels": [{"properties": {"fontSize": lit("20D")}}], "categoryLabels": [{"properties": {"show": lit("true"), "fontSize": lit("9D")}}]})
def cards(page, y, measures, h=86):
    n, gap, left, width = len(measures), 10, 20, 1240
    w = (width - gap * (n - 1)) / n
    return [card(page, f"card_{m}", (left + i * (w + gap), y, w, h), m) for i, m in enumerate(measures)]
DT_SLICER = col("ValTypeTable", "SalesType")
def pages():
    P = {}
    p = "Performance Overview"
    P[p] = [textbox(p, "title", (20, 8, 900, 60), "Sales & Flown Performance", "XA / Archipelago Air  |  synthetic data  |  TY capped at the data cut-off, LY at the same day last year"),
            slicer(p, "s_type", (20, 72, 200, 66), DT_SLICER, "Data type", default="Sales", single=True),
            slicer(p, "s_year", (230, 72, 160, 66), col("DateTable", "Year"), "Year", default=2026, single=True),
            slicer(p, "s_month", (400, 72, 200, 66), col("DateTable", "Month"), "Month"),
            slicer(p, "s_service", (610, 72, 160, 66), col("SalesFlown", "SERVICE TYPE"), "Service"),
            slicer(p, "s_channel", (780, 72, 200, 66), col("SalesFlown", "GROUPING CHANNEL"), "Channel"),
            container(p, "asof", "card", (1060, 72, 200, 66), {"Values": [mea("Data As Of")]}, "Data as of", {"labels": [{"properties": {"fontSize": lit("14D")}}], "categoryLabels": [{"properties": {"show": lit("false")}}]})]
    P[p] += cards(p, 146, ["Revenue TY", "Revenue YoY %", "Pax TY", "Pax YoY %", "Avg Fare TY", "Avg Fare YoY %"])
    P[p] += [container(p, "line", "lineChart", (20, 242, 820, 230), {"Category": [col("DateTable", "Month")], "Y": [mea("Revenue TY"), mea("Revenue LY")]},
                       "Revenue by month, TY vs LY", sort=[(col("DateTable", "Month"), "Ascending")]),
             container(p, "bar_channel", "clusteredBarChart", (850, 242, 410, 230), {"Category": [col("SalesFlown", "GROUPING CHANNEL")], "Y": [mea("Revenue TY")]},
                       "Revenue by channel", sort=[(mea("Revenue TY"), "Descending")]),
             container(p, "tbl_route", "pivotTable", (20, 482, 1240, 228), {"Rows": [col("DimRoute", "dest")],
                       "Values": [mea("Revenue TY"), mea("Revenue LY"), mea("Revenue YoY %"), mea("Pax TY"), mea("Avg Fare TY"), mea("Avg Fare YoY %")]},
                       "Route performance (destination from CGK)", sort=[(mea("Revenue TY"), "Descending")])]
    p = "MTD & YTD"
    P[p] = [textbox(p, "title", (20, 8, 900, 60), "MTD & YTD Tracking", "Pick MTD or YTD; both anchor on the latest date in the selection"),
            slicer(p, "s_period", (20, 72, 180, 66), col("PeriodSelector", "Period"), "Period", default="MTD", single=True),
            slicer(p, "s_type", (210, 72, 180, 66), DT_SLICER, "Data type", default="Sales", single=True),
            slicer(p, "s_year", (400, 72, 150, 66), col("DateTable", "Year"), "Year", default=2026, single=True),
            slicer(p, "s_month", (560, 72, 180, 66), col("DateTable", "Month"), "Month"),
            slicer(p, "s_service", (750, 72, 150, 66), col("SalesFlown", "SERVICE TYPE"), "Service")]
    P[p] += cards(p, 146, ["Revenue Selected Period", "Revenue Selected Period LY", "Revenue Selected Period YoY %", "Pax MTD YoY %", "Pax YTD YoY %", "Corporate Share %"])
    P[p] += [container(p, "col_rbd", "clusteredColumnChart", (20, 242, 820, 230), {"Category": [col("SubclassSortOrder", "BookingClass")], "Y": [mea("Revenue TY")]},
                       "Revenue by booking class (RBD)", sort=[(col("SubclassSortOrder", "BookingClass"), "Ascending")]),
             container(p, "tbl_family", "pivotTable", (850, 242, 410, 230), {"Rows": [col("SubclassSortOrder", "FareFamily")],
                       "Values": [mea("Revenue TY"), mea("Fare Family Share %"), mea("Avg Fare TY")]}, "Fare family mix", sort=[(mea("Revenue TY"), "Descending")]),
             container(p, "bar_cluster", "clusteredBarChart", (20, 482, 610, 228), {"Category": [col("DimCorporate", "CORPORATE_CLUSTER")], "Y": [mea("Corporate Revenue TY"), mea("Corporate Revenue LY")]},
                       "Corporate revenue by cluster", sort=[(mea("Corporate Revenue TY"), "Descending")]),
             container(p, "tbl_region", "pivotTable", (640, 482, 620, 228), {"Rows": [col("DimBranchRegion", "REGION")],
                       "Values": [mea("Revenue MTD"), mea("Revenue MTD YoY %"), mea("Revenue YTD"), mea("Revenue YTD YoY %")]}, "Branch regions", sort=[(mea("Revenue YTD"), "Descending")])]
    p = "Period vs Period"
    P[p] = [textbox(p, "title", (20, 8, 900, 60), "Period vs Period & Route Pull-Out", "Default: Apr-Sep 2026 vs Apr-Sep 2025, the six months after four routes were pulled out"),
            slicer(p, "s_p1", (20, 76, 410, 96), col("Calendar_Slicer1", "Date"), "Period 1", mode="Between", default=("2025-04-01", "2025-09-30")),
            slicer(p, "s_p2", (440, 76, 410, 96), col("Calendar_Slicer2", "Date"), "Period 2", mode="Between", default=("2026-04-01", "2026-09-30")),
            slicer(p, "s_type", (860, 76, 200, 96), DT_SLICER, "Data type", default="Flown", single=True)]
    P[p] += cards(p, 182, ["Revenue P1", "Revenue P2", "Revenue P2 vs P1 %", "Pax P1", "Pax P2", "Pax P2 vs P1 %"])
    P[p] += [container(p, "tbl_status", "pivotTable", (20, 282, 820, 428), {"Rows": [col("DimRoute", "status"), col("DimRoute", "dest")],
                       "Values": [mea("Revenue P1"), mea("Revenue P2"), mea("Revenue P2 vs P1 %"), mea("Pax P2 vs P1 %")]},
                       "Routes by status (Active / Pull Out)", sort=[(mea("Revenue P1"), "Descending")]),
             container(p, "bar_channel", "clusteredBarChart", (850, 282, 410, 428), {"Category": [col("SalesFlown", "GROUPING CHANNEL")], "Y": [mea("Revenue P1"), mea("Revenue P2")]},
                       "Channel: Period 1 vs Period 2", sort=[(mea("Revenue P2"), "Descending")])]
    p = "Booking Curve & BLF"
    P[p] = [textbox(p, "title", (20, 8, 900, 60), "Booking Curve & Forward Load Factor", "How early passengers buy, and how full the next 12 months already are"),
            slicer(p, "s_service", (20, 72, 200, 66), col("DimRoute", "service_type"), "Service"),
            slicer(p, "s_dest", (230, 72, 200, 66), col("DimRoute", "dest"), "Destination")]
    P[p] += cards(p, 146, ["Avg Lead Time (days)", "BLF %", "Seats Unsold"])
    P[p] += [container(p, "col_curve", "clusteredColumnChart", (20, 242, 620, 468), {"Category": [col("SalesToFlown", "Sales to Flown Group")], "Y": [mea("% of Total Pax (Lead Time)")]},
                       "Booking curve: % of flown pax by days before departure", sort=[(col("SalesToFlown", "Sales to Flown Group"), "Ascending")]),
             container(p, "col_blf_month", "clusteredColumnChart", (650, 242, 610, 230), {"Category": [col("BookingPosition", "Departure Month")], "Y": [mea("BLF %")]},
                       "Booked load factor by departure month", sort=[(col("BookingPosition", "Departure Month"), "Ascending")]),
             container(p, "bar_blf_dest", "clusteredBarChart", (650, 482, 610, 228), {"Category": [col("DimRoute", "dest")], "Y": [mea("BLF %")]},
                       "Booked load factor by destination", sort=[(mea("BLF %"), "Descending")])]
    return P
def write_report():
    if RP.exists():
        shutil.rmtree(RP)
    dump(RP / "definition.pbir", {"$schema": f"{SCHEMA}/item/report/definitionProperties/1.0.0/schema.json", "version": "4.0",
                                  "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    d = RP / "definition"
    dump(d / "version.json", {"$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    base = ROOT / "powerbi" / "theme" / "CY24SU10.json"
    shutil.copy(base, (RP / "StaticResources" / "SharedResources" / "BaseThemes").mkdir(parents=True, exist_ok=True) or RP / "StaticResources/SharedResources/BaseThemes/CY24SU10.json")
    dump(RP / "StaticResources" / "RegisteredResources" / "Archipelago.json", THEME)
    dump(d / "report.json", {"$schema": f"{SCHEMA}/item/report/definition/report/1.3.0/schema.json",
        "themeCollection": {"baseTheme": {"name": "CY24SU10", "reportVersionAtImport": "5.61", "type": "SharedResources"},
                            "customTheme": {"name": "Archipelago.json", "reportVersionAtImport": "5.61", "type": "RegisteredResources"}},
        "layoutOptimization": "None",
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]},
                             {"name": "RegisteredResources", "type": "RegisteredResources", "items": [{"name": "Archipelago.json", "path": "Archipelago.json", "type": "CustomTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "defaultFilterActionIsDataFilter": True, "defaultDrillFilterOtherVisuals": True,
                     "allowChangeFilterTypes": True, "useEnhancedTooltips": True}})
    order = []
    for i, (title, visuals) in enumerate(pages().items()):
        pid = uid("page", title)
        order.append(pid)
        dump(d / "pages" / pid / "page.json", {"$schema": f"{SCHEMA}/item/report/definition/page/1.4.0/schema.json", "name": pid,
             "displayName": title, "displayOption": "FitToPage", "height": 720, "width": 1280})
        for z, (key, c) in enumerate(visuals):
            c["position"]["z"] = c["position"]["tabOrder"] = z * 1000
            c["position"] = {k: round(v, 2) if isinstance(v, float) else v for k, v in c["position"].items()}
            dump(d / "pages" / pid / "visuals" / c["name"] / "visual.json", c)
    dump(d / "pages" / "pages.json", {"$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json", "pageOrder": order, "activePageName": order[0]})
    dump(PB / f"{NAME}.pbip", {"$schema": f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
                               "artifacts": [{"report": {"path": f"{NAME}.Report"}}], "settings": {"enableAutoRecovery": True}})
    (PB / ".gitignore").write_text("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-folder", default="C:\\airline-sales-performance-bi\\data\\model")
    a = ap.parse_args()
    write_semantic_model(a.data_folder)
    write_report()
    n = sum(1 for _ in RP.rglob("visual.json"))
    print(f"PBIP written: {len(bt.CSV_TABLES) + len(bt.CALC_TABLES)} tables, {len(bt.M)} measures, {len(pages())} pages, {n} visuals")
