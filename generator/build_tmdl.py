"""Generates the Power BI semantic model as a TMDL script (powerbi/semantic_model.tmdl)
plus a DAX query file (dax/measures.dax) and a measure catalog (docs/measure_catalog.md).
The measure catalog below is the single source of truth for every DAX measure in the project.
"""
import pathlib, re, textwrap
ROOT = pathlib.Path(__file__).resolve().parents[1]
T = "\t"
def q(name):  # TMDL / DAX object name quoting
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"
# ---------------------------------------------------------------- tables loaded from CSV (Power Query)
CSV_TABLES = {
    "SalesFlown": ("fact_sales_flown.csv", [
        ("DATA TYPE","string"),("SERVICE TYPE","string"),("SUBSERVICE","string"),("AGEN NO","string"),("AGENT GROUPING","string"),
        ("POI","string"),("BRANCH OFFICE","string"),("ROUTEVV","string"),("ROUTE","string"),("DATES","date"),("CORP CODE","string"),
        ("GROUPING CHANNEL","string"),("SUBCLASS","string"),("BO POO","string"),("CORP NAME","string"),("CORPORATE CLUSTER","string"),
        ("AGENT NAME","string"),("CORP SHARE","string"),("AREA","string"),("DATE TRAVEL","date"),("PAX","int64"),("NETT USD","double"),
        ("BASIC FARE USD","double"),("WEEK NUM","int64")]),
    "DimCorporate": ("dim_corporate.csv", [("CORP CODE","string"),("CORPORATE_NAME","string"),("CORPORATE_CLUSTER","string"),("INDUSTRY_TYPE","string")]),
    "DimBranchRegion": ("dim_branch_region.csv", [("BO","string"),("REGION","string")]),
    "DimRoute": ("dim_route.csv", [("route_vv","string"),("itinerary","string"),("dest","string"),("service_type","string"),
        ("subservice","string"),("aircraft","string"),("status","string")]),
    "BookingPosition": ("fact_booking_position.csv", [("RegionCode","string"),("FltNbr","int64"),("DOW","int64"),("Bulan","int64"),
        ("FlightType","string"),("SubServiceCode","string"),("Tahun","int64"),("TipeAircraft","string"),("STD","dateTime"),
        ("ServiceTypeCode","string"),("RouteVV","string"),("Route","string"),("Depart","string"),("Arrived","string"),
        ("DiffDate","int64"),("Book_Total","int64"),("Capacity_Total","int64")]),
    "SalesToFlown": ("fact_sales_to_flown.csv", [("route_vv","string"),("servicetypecode","string"),("sales_to_flown","int64"),
        ("trip_duration","int64"),("trip_type","string"),("year","int64"),("pax","int64")]),
    "GroupBooking": ("group_bookings.csv", [("MO","int64"),("WEEK","int64"),("TGL BOOKING","date"),("PNR","string"),("NAMA GROUP","string"),
        ("AGENT TRAVEL","string"),("AGENT/CORP/PRIVATE","string"),("DEPT.DATE","date"),("RETURN DATE","date"),("ROUTE","string"),
        ("DEST","string"),("DOM/INT","string"),("TTL PAX","int64"),("MARKET","string"),("APPROVED SKN FARE - IDR.","int64"),("YQ","int64"),
        ("TAX ++","int64"),("NETT SALES","int64"),("Nett Sales ( basic + yq )","int64"),("Total sales ( nett x ttl pax )","int64"),
        ("FARE BASIC","string"),("STATUS","string"),("DATE OF DEPOSIT","date"),("JMLH PAX DEPO","int64"),("JLMH DEPOSIT(idr)","int64"),
        ("REASON CANCEL","string"),("CORP CODE","string"),("TIME LIMIT","date"),("POI","string"),("DOI","date")]),
}
M_TYPE = {"string":"type text","int64":"Int64.Type","double":"type number","date":"type date","dateTime":"type datetime"}
TMDL_TYPE = {"string":"string","int64":"int64","double":"double","date":"dateTime","dateTime":"dateTime"}
# ---------------------------------------------------------------- calculated columns
CALC_COLUMNS = {
    "SalesFlown": [
        ("Route Status", "RELATED ( DimRoute[status] )", None),
        ("POO Classification", 'IF ( SalesFlown[BRANCH OFFICE] = SalesFlown[BO POO], "POO", "Non POO" )', None),
        ("Corporate Cluster Group", """SWITCH (
    TRUE (),
    ISBLANK ( SalesFlown[CORPORATE CLUSTER] ), "(Blank)",
    SalesFlown[CORPORATE CLUSTER] IN { "GOVERNMENT", "SOE" }, "GOVERNMENT & SOE",
    SalesFlown[CORPORATE CLUSTER] IN { "CHA/TMC", "PRIVATE" }, "PRIVATE",
    SalesFlown[CORPORATE CLUSTER]
)""", None)],
    "DateTable": [
        ("Day of week name", 'FORMAT ( DateTable[Date], "ddd" )', "Day of Week Number"),
        ("Day of Week Number", "WEEKDAY ( DateTable[Date], 2 )", None),
        ("WeekNum", "WEEKNUM ( DateTable[Date], 2 )", None),
        ("YearWeek", "DateTable[Year] * 100 + DateTable[WeekNum]", None),
        ("Month-Day", 'FORMAT ( DateTable[Date], "MM-DD" )', "MMDD Numeric"),
        ("MMDD Numeric", "MONTH ( DateTable[Date] ) * 100 + DAY ( DateTable[Date] )", None),
        ("Date No", "DAY ( DateTable[Date] )", None)],
    "DateFlown": [("WeekNum", "WEEKNUM ( DateFlown[Date], 2 )", None)],
    "SalesToFlown": [
        ("Trip Duration Group", """SWITCH (
    TRUE (),
    SalesToFlown[trip_type] = "OW", "One Way",
    SalesToFlown[trip_duration] <= 3, "1-3 Days",
    SalesToFlown[trip_duration] <= 7, "4-7 Days",
    SalesToFlown[trip_duration] <= 14, "8-14 Days",
    ">14 Days"
)""", "Trip Duration Sort"),
        ("Trip Duration Sort", """SWITCH (
    TRUE (),
    SalesToFlown[trip_type] = "OW", 0,
    SalesToFlown[trip_duration] <= 3, 1,
    SalesToFlown[trip_duration] <= 7, 2,
    SalesToFlown[trip_duration] <= 14, 3,
    4
)""", None),
        ("Sales to Flown Group", """VAR d = SalesToFlown[sales_to_flown]
RETURN
    SWITCH (
        TRUE (),
        d = 0, "H",
        d <= 7, "H-" & d,
        d <= 30, "H-(8-30)",
        d <= 60, "H-(31-60)",
        d <= 120, "H-(61-120)",
        "H-121+"
    )""", "Sales to Flown Sort"),
        ("Sales to Flown Sort", """VAR d = SalesToFlown[sales_to_flown]
RETURN
    SWITCH ( TRUE (), d <= 7, d + 1, d <= 30, 9, d <= 60, 10, d <= 120, 11, 12 )""", None)],
}
# ---------------------------------------------------------------- calculated tables
CALC_TABLES = {
    "DateTable": ("""ADDCOLUMNS (
    CALENDAR ( DATE ( 2025, 1, 1 ), DATE ( 2026, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Month", FORMAT ( [Date], "MMM" ),
    "MonthNumber", MONTH ( [Date] ),
    "Quarter", "Q" & FORMAT ( [Date], "Q" )
)""", ["Date","Year","Month","MonthNumber","Quarter"]),
    "DateFlown": ("""ADDCOLUMNS (
    CALENDAR ( DATE ( 2024, 1, 1 ), DATE ( 2027, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Month", FORMAT ( [Date], "MMM" ),
    "MonthNumber", MONTH ( [Date] ),
    "Quarter", "Q" & FORMAT ( [Date], "Q" )
)""", ["Date","Year","Month","MonthNumber","Quarter"]),
    "ValTypeTable": ("""DATATABLE ( "SalesType", STRING, { { "Sales" }, { "Flown" } } )""", ["SalesType"]),
    "PeriodSelector": ("""DATATABLE ( "Period", STRING, "PeriodSort", INTEGER, { { "MTD", 1 }, { "YTD", 2 } } )""", ["Period","PeriodSort"]),
    "SubclassSortOrder": ("""DATATABLE (
    "BookingClass", STRING, "SortOrder", INTEGER, "Cabin", STRING, "FareFamily", STRING,
    {
        { "F", 1, "First", "FPA JCDI" }, { "R", 2, "First", "ROX" }, { "P", 3, "First", "FPA JCDI" }, { "A", 4, "First", "FPA JCDI" },
        { "J", 5, "Business", "FPA JCDI" }, { "C", 6, "Business", "FPA JCDI" }, { "D", 7, "Business", "FPA JCDI" },
        { "O", 8, "Business", "ROX" }, { "I", 9, "Business", "FPA JCDI" }, { "Z", 10, "Business", "Other" },
        { "Y", 11, "Economy", "Y" }, { "W", 12, "Economy", "WBMKN" }, { "B", 13, "Economy", "WBMKN" }, { "M", 14, "Economy", "WBMKN" },
        { "K", 15, "Economy", "WBMKN" }, { "N", 16, "Economy", "WBMKN" }, { "G", 17, "Economy", "Other" }, { "Q", 18, "Economy", "QTV" },
        { "T", 19, "Economy", "QTV" }, { "V", 20, "Economy", "QTV" }, { "S", 21, "Economy", "SHL" }, { "H", 22, "Economy", "SHL" },
        { "L", 23, "Economy", "SHL" }, { "E", 24, "Economy", "Other" }, { "U", 25, "Economy", "Other" }, { "X", 26, "Economy", "ROX" }
    }
)""", ["BookingClass","SortOrder","Cabin","FareFamily"]),
    "Calendar_Slicer1": ("""DISTINCT ( SELECTCOLUMNS ( DateTable, "Date", DateTable[Date] ) )""", ["Date"]),
    "Calendar_Slicer2": ("""DISTINCT ( SELECTCOLUMNS ( DateTable, "Date", DateTable[Date] ) )""", ["Date"]),
    "Calendar_Slicer_PO1": ("""DISTINCT ( SELECTCOLUMNS ( DateTable, "Date", DateTable[Date] ) )""", ["Date"]),
    "Calendar_Slicer_PO2": ("""DISTINCT ( SELECTCOLUMNS ( DateTable, "Date", DateTable[Date] ) )""", ["Date"]),
    "_Measures": ("""ROW ( "Placeholder", BLANK () )""", ["Placeholder"]),
}
SORT_BY = {("DateTable","Month"):"MonthNumber", ("DateFlown","Month"):"MonthNumber", ("SubclassSortOrder","BookingClass"):"SortOrder",
           ("PeriodSelector","Period"):"PeriodSort"}
# ---------------------------------------------------------------- measures: (table, folder, name, format, expression, note)
F0, FPCT, FDATE = "#,0", "0.0%;-0.0%;0.0%", "dd mmm yyyy"
REV, PAX = "SUM ( SalesFlown[NETT USD] )", "SUM ( SalesFlown[PAX] )"
def period(table, n, slicer, kind):  # disconnected-slicer period comparison measures
    base = REV if kind == "Revenue" else PAX
    return (table, "5 Period vs Period", f"{kind} {n}", F0, f"""CALCULATE (
    {base},
    KEEPFILTERS ( TREATAS ( VALUES ( {slicer}[Date] ), DateTable[Date] ) )
)""", f"Uses disconnected slicer {slicer} so two date ranges can be compared on one page.")
M = [
    # ---- helpers
    ("_Measures","0 Helpers","_MaxDateInData",FDATE,"CALCULATE ( MAX ( SalesFlown[DATES] ), ALL ( SalesFlown ) )","Latest loaded date (the data cut-off). Every TY/LY measure is capped at this date so partial days/months compare like for like."),
    ("_Measures","0 Helpers","_MaxDateInContext",FDATE,"MAX ( SalesFlown[DATES] )","Latest date visible in the current filter context."),
    ("_Measures","0 Helpers","_TargetDate",FDATE,"[_MaxDateInContext]","Anchor date for MTD/YTD. Original was IF(ctx = data, data, ctx), which always returns ctx, so it is simplified."),
    ("_Measures","0 Helpers","_MaxWeek","0","MAX ( SalesFlown[WEEK NUM] )","Latest airline sales week in context."),
    ("_Measures","0 Helpers","_MaxTravelDateInData",FDATE,"CALCULATE ( MAX ( SalesFlown[DATE TRAVEL] ), ALL ( SalesFlown ) )","Latest travel date on any ticket, used by the travel-date page."),
    ("_Measures","0 Helpers","Data As Of",FDATE,"""VAR MaxDateInContext = [_MaxDateInContext]
VAR MaxDateInData = [_MaxDateInData]
VAR AllMonthsSelected =
    COUNTROWS ( VALUES ( DateTable[MonthNumber] ) ) = COUNTROWS ( ALL ( DateTable[MonthNumber] ) )
RETURN
    IF ( AllMonthsSelected, MaxDateInData, MaxDateInContext )""","Card subtitle: shows the cut-off date of the data behind the visual."),
    # ---- base
    ("_Measures","1 Base","Revenue","#,0",REV,"Nett revenue in USD (gross - discount + YQ)."),
    ("_Measures","1 Base","Pax","#,0",PAX,"Passengers. Sales = tickets per coupon row, Flown = tickets on first-coupon flag."),
    ("_Measures","1 Base","Avg Fare","#,0","DIVIDE ( [Revenue], [Pax] )","Revenue per pax."),
    # ---- daily TY vs LY (capped at cut-off)
    ("_Measures","2 TY vs LY","Revenue TY",F0,"""VAR CutoffDate = [_MaxDateInData]
RETURN
    CALCULATE ( [Revenue], KEEPFILTERS ( DateTable[Date] <= CutoffDate ) )""","This-year revenue up to the data cut-off. Works at day, week, month or year level."),
    ("_Measures","2 TY vs LY","Revenue LY",F0,"""VAR CutoffDateLY = EDATE ( [_MaxDateInData], -12 )
RETURN
    CALCULATE (
        [Revenue],
        SAMEPERIODLASTYEAR ( DateTable[Date] ),
        KEEPFILTERS ( DateTable[Date] <= CutoffDateLY )
    )""","Same period last year, capped at cut-off minus 12 months so a half-finished month is never compared with a full one."),
    ("_Measures","2 TY vs LY","Revenue YoY",F0,"[Revenue TY] - [Revenue LY]",""),
    ("_Measures","2 TY vs LY","Revenue YoY %",FPCT,"DIVIDE ( [Revenue TY] - [Revenue LY], [Revenue LY] )",""),
    ("_Measures","2 TY vs LY","Pax TY",F0,"""VAR CutoffDate = [_MaxDateInData]
RETURN
    CALCULATE ( [Pax], KEEPFILTERS ( DateTable[Date] <= CutoffDate ) )""",""),
    ("_Measures","2 TY vs LY","Pax LY",F0,"""VAR CutoffDateLY = EDATE ( [_MaxDateInData], -12 )
RETURN
    CALCULATE (
        [Pax],
        SAMEPERIODLASTYEAR ( DateTable[Date] ),
        KEEPFILTERS ( DateTable[Date] <= CutoffDateLY )
    )""",""),
    ("_Measures","2 TY vs LY","Pax YoY",F0,"[Pax TY] - [Pax LY]",""),
    ("_Measures","2 TY vs LY","Pax YoY %",FPCT,"DIVIDE ( [Pax TY] - [Pax LY], [Pax LY] )",""),
    ("_Measures","2 TY vs LY","Avg Fare TY",F0,"DIVIDE ( [Revenue TY], [Pax TY] )",""),
    ("_Measures","2 TY vs LY","Avg Fare LY",F0,"DIVIDE ( [Revenue LY], [Pax LY] )",""),
    ("_Measures","2 TY vs LY","Avg Fare YoY",F0,"[Avg Fare TY] - [Avg Fare LY]",""),
    ("_Measures","2 TY vs LY","Avg Fare YoY %",FPCT,"DIVIDE ( [Avg Fare TY] - [Avg Fare LY], [Avg Fare LY] )",""),
    ("_Measures","2 TY vs LY","Revenue Same Date LY",F0,"""VAR CurrentDate = MAX ( DateTable[Date] )
RETURN
    IF (
        CurrentDate <= [_MaxDateInData],
        CALCULATE ( [Revenue], ALL ( DateTable ), DateTable[Date] = EDATE ( CurrentDate, -12 ) )
    )""","Calendar-date match (1 Mar vs 1 Mar) for daily line charts; blank after the cut-off so the line stops."),
    # ---- MTD / YTD anchored on target date
    ("_Measures","3 MTD YTD","Revenue MTD",F0,"""VAR TargetDate = [_TargetDate]
RETURN
    CALCULATE ( TOTALMTD ( [Revenue], DateTable[Date] ), DateTable[Date] <= TargetDate )""",""),
    ("_Measures","3 MTD YTD","Revenue MTD LY",F0,"""VAR TargetDateLY = EDATE ( [_TargetDate], -12 )
RETURN
    CALCULATE (
        [Revenue],
        ALL ( DateTable ),
        DATESBETWEEN ( DateTable[Date], DATE ( YEAR ( TargetDateLY ), MONTH ( TargetDateLY ), 1 ), TargetDateLY )
    )""","Month to the same day last year. DATESBETWEEN replaces the two >= / <= filters of the original."),
    ("_Measures","3 MTD YTD","Revenue MTD YoY %",FPCT,"DIVIDE ( [Revenue MTD] - [Revenue MTD LY], [Revenue MTD LY] )",""),
    ("_Measures","3 MTD YTD","Revenue YTD",F0,"""VAR TargetDate = [_TargetDate]
RETURN
    CALCULATE ( TOTALYTD ( [Revenue], DateTable[Date] ), DateTable[Date] <= TargetDate )""",""),
    ("_Measures","3 MTD YTD","Revenue YTD LY",F0,"""VAR TargetDateLY = EDATE ( [_TargetDate], -12 )
RETURN
    CALCULATE (
        [Revenue],
        ALL ( DateTable ),
        DATESBETWEEN ( DateTable[Date], DATE ( YEAR ( TargetDateLY ), 1, 1 ), TargetDateLY )
    )""",""),
    ("_Measures","3 MTD YTD","Revenue YTD YoY %",FPCT,"DIVIDE ( [Revenue YTD] - [Revenue YTD LY], [Revenue YTD LY] )",""),
    ("_Measures","3 MTD YTD","Pax MTD",F0,"""VAR TargetDate = [_TargetDate]
RETURN
    CALCULATE ( TOTALMTD ( [Pax], DateTable[Date] ), DateTable[Date] <= TargetDate )""",""),
    ("_Measures","3 MTD YTD","Pax MTD LY",F0,"""VAR TargetDateLY = EDATE ( [_TargetDate], -12 )
RETURN
    CALCULATE (
        [Pax],
        ALL ( DateTable ),
        DATESBETWEEN ( DateTable[Date], DATE ( YEAR ( TargetDateLY ), MONTH ( TargetDateLY ), 1 ), TargetDateLY )
    )""",""),
    ("_Measures","3 MTD YTD","Pax MTD YoY %",FPCT,"DIVIDE ( [Pax MTD] - [Pax MTD LY], [Pax MTD LY] )",""),
    ("_Measures","3 MTD YTD","Pax YTD",F0,"""VAR TargetDate = [_TargetDate]
RETURN
    CALCULATE ( TOTALYTD ( [Pax], DateTable[Date] ), DateTable[Date] <= TargetDate )""",""),
    ("_Measures","3 MTD YTD","Pax YTD LY",F0,"""VAR TargetDateLY = EDATE ( [_TargetDate], -12 )
RETURN
    CALCULATE (
        [Pax],
        ALL ( DateTable ),
        DATESBETWEEN ( DateTable[Date], DATE ( YEAR ( TargetDateLY ), 1, 1 ), TargetDateLY )
    )""",""),
    ("_Measures","3 MTD YTD","Pax YTD YoY %",FPCT,"DIVIDE ( [Pax YTD] - [Pax YTD LY], [Pax YTD LY] )",""),
    ("_Measures","3 MTD YTD","Avg Fare MTD",F0,"DIVIDE ( [Revenue MTD], [Pax MTD] )",""),
    ("_Measures","3 MTD YTD","Avg Fare MTD LY",F0,"DIVIDE ( [Revenue MTD LY], [Pax MTD LY] )",""),
    ("_Measures","3 MTD YTD","Avg Fare MTD YoY %",FPCT,"DIVIDE ( [Avg Fare MTD] - [Avg Fare MTD LY], [Avg Fare MTD LY] )",""),
    ("_Measures","3 MTD YTD","Avg Fare YTD",F0,"DIVIDE ( [Revenue YTD], [Pax YTD] )",""),
    ("_Measures","3 MTD YTD","Avg Fare YTD LY",F0,"DIVIDE ( [Revenue YTD LY], [Pax YTD LY] )",""),
    ("_Measures","3 MTD YTD","Avg Fare YTD YoY %",FPCT,"DIVIDE ( [Avg Fare YTD] - [Avg Fare YTD LY], [Avg Fare YTD LY] )",""),
    # ---- MTD/YTD switch driven by PeriodSelector slicer
    ("_Measures","4 Period Switch","Revenue Selected Period",F0,"""SWITCH (
    SELECTEDVALUE ( PeriodSelector[Period], "MTD" ),
    "MTD", [Revenue MTD],
    "YTD", [Revenue YTD]
)""","One visual, user flips MTD / YTD with a slicer (field-parameter style without field parameters)."),
    ("_Measures","4 Period Switch","Revenue Selected Period LY",F0,"""SWITCH (
    SELECTEDVALUE ( PeriodSelector[Period], "MTD" ),
    "MTD", [Revenue MTD LY],
    "YTD", [Revenue YTD LY]
)""","Fix vs original: YTD LY now anchors on the target date like MTD LY (original used each row's own date)."),
    ("_Measures","4 Period Switch","Revenue Selected Period YoY",F0,"[Revenue Selected Period] - [Revenue Selected Period LY]",""),
    ("_Measures","4 Period Switch","Revenue Selected Period YoY %",FPCT,"DIVIDE ( [Revenue Selected Period] - [Revenue Selected Period LY], [Revenue Selected Period LY] )",""),
    # ---- period vs period (two disconnected calendars)
    period("_Measures", "P1", "Calendar_Slicer1", "Revenue"), period("_Measures", "P1", "Calendar_Slicer1", "Pax"),
    period("_Measures", "P2", "Calendar_Slicer2", "Revenue"), period("_Measures", "P2", "Calendar_Slicer2", "Pax"),
    ("_Measures","5 Period vs Period","Avg Fare P1",F0,"DIVIDE ( [Revenue P1], [Pax P1] )",""),
    ("_Measures","5 Period vs Period","Avg Fare P2",F0,"DIVIDE ( [Revenue P2], [Pax P2] )",""),
    ("_Measures","5 Period vs Period","Revenue P2 vs P1",F0,"[Revenue P2] - [Revenue P1]",""),
    ("_Measures","5 Period vs Period","Revenue P2 vs P1 %",FPCT,"DIVIDE ( [Revenue P2] - [Revenue P1], [Revenue P1] )",""),
    ("_Measures","5 Period vs Period","Pax P2 vs P1",F0,"[Pax P2] - [Pax P1]",""),
    ("_Measures","5 Period vs Period","Pax P2 vs P1 %",FPCT,"DIVIDE ( [Pax P2] - [Pax P1], [Pax P1] )",""),
    ("_Measures","5 Period vs Period","Avg Fare P2 vs P1 %",FPCT,"DIVIDE ( [Avg Fare P2] - [Avg Fare P1], [Avg Fare P1] )",""),
    # ---- pull-out route analysis: own pair of slicers so it does not clash with page 5
    period("_Measures", "PO P1", "Calendar_Slicer_PO1", "Revenue"), period("_Measures", "PO P1", "Calendar_Slicer_PO1", "Pax"),
    period("_Measures", "PO P2", "Calendar_Slicer_PO2", "Revenue"), period("_Measures", "PO P2", "Calendar_Slicer_PO2", "Pax"),
    ("_Measures","6 Pull Out","Revenue PO P2 vs P1 %",FPCT,"DIVIDE ( [Revenue PO P2] - [Revenue PO P1], [Revenue PO P1] )",""),
    ("_Measures","6 Pull Out","Pax PO P2 vs P1 %",FPCT,"DIVIDE ( [Pax PO P2] - [Pax PO P1], [Pax PO P1] )",""),
    ("_Measures","6 Pull Out","Pull Out Revenue Recaptured %",FPCT,"""VAR LostOnPulledRoutes =
    CALCULATE ( [Revenue PO P1] - [Revenue PO P2], DimRoute[status] = "Pull Out" )
VAR GainOnActiveRoutes =
    CALCULATE ( [Revenue PO P2] - [Revenue PO P1], DimRoute[status] = "Active" )
RETURN
    DIVIDE ( GainOnActiveRoutes, LostOnPulledRoutes )""","New: share of revenue lost on discontinued routes that shows up as growth on remaining routes."),
    # ---- mix
    ("_Measures","7 Mix","Domestic %","0%","""DIVIDE (
    CALCULATE ( [Revenue TY], SalesFlown[SERVICE TYPE] = "DOM" ),
    CALCULATE ( [Revenue TY], REMOVEFILTERS ( SalesFlown[SERVICE TYPE] ) )
)""","Fix vs original: denominator removes the service filter, so the % stays correct when a DOM/INT slicer is used."),
    ("_Measures","7 Mix","International %","0%","""DIVIDE (
    CALCULATE ( [Revenue TY], SalesFlown[SERVICE TYPE] = "INT" ),
    CALCULATE ( [Revenue TY], REMOVEFILTERS ( SalesFlown[SERVICE TYPE] ) )
)""",""),
    ("_Measures","7 Mix","Corporate Share %","0%","""DIVIDE (
    CALCULATE ( [Revenue TY], SalesFlown[CORP SHARE] = "Corp" ),
    CALCULATE ( [Revenue TY], REMOVEFILTERS ( SalesFlown[CORP SHARE] ) )
)""",""),
    ("_Measures","7 Mix","Fare Family Share %","0%","""DIVIDE ( [Revenue TY], CALCULATE ( [Revenue TY], REMOVEFILTERS ( SubclassSortOrder ) ) )""","Put SubclassSortOrder[FareFamily] or [BookingClass] on rows/columns. Replaces 26 copy-paste 'RBD x' measures plus 6 fare-family % measures."),
] + [("_Measures","7 Mix",f"{ff} %","0%",f'CALCULATE ( [Fare Family Share %], SubclassSortOrder[FareFamily] = "{ff}" )',"Card-friendly shortcut over Fare Family Share %.") for ff in ["FPA JCDI","ROX","Y","WBMKN","QTV","SHL"]] + [
    # ---- travel date (flown by departure date)
    ("_Measures","8 Travel Date","Pax by Travel Date TY",F0,"""VAR CutoffDate = [_MaxTravelDateInData]
RETURN
    CALCULATE ( [Pax], KEEPFILTERS ( DateFlown[Date] <= CutoffDate ) )""","Sales pax by departure date (forward-looking on-the-books view)."),
    ("_Measures","8 Travel Date","Pax by Travel Date LY",F0,"""VAR CutoffDateLY = EDATE ( [_MaxTravelDateInData], -12 )
RETURN
    CALCULATE (
        [Pax],
        SAMEPERIODLASTYEAR ( DateFlown[Date] ),
        KEEPFILTERS ( DateFlown[Date] <= CutoffDateLY )
    )""",""),
    ("_Measures","8 Travel Date","Pax by Travel Date YoY %","0%","DIVIDE ( [Pax by Travel Date TY] - [Pax by Travel Date LY], [Pax by Travel Date LY] )",""),
    # ---- lead time, BLF, groups
    ("_Measures","9 Lead Time & BLF","% of Total Pax (Lead Time)",FPCT,"""DIVIDE ( SUM ( SalesToFlown[pax] ), CALCULATE ( SUM ( SalesToFlown[pax] ), ALLSELECTED () ) )""","Booking curve share: how early passengers buy before departure."),
    ("_Measures","9 Lead Time & BLF","Avg Lead Time (days)","0.0","""DIVIDE (
    SUMX ( SalesToFlown, SalesToFlown[sales_to_flown] * SalesToFlown[pax] ),
    SUM ( SalesToFlown[pax] )
)""","New: pax-weighted average days between purchase and departure."),
    ("_Measures","9 Lead Time & BLF","BLF %",FPCT,"DIVIDE ( SUM ( BookingPosition[Book_Total] ), SUM ( BookingPosition[Capacity_Total] ) )","Booked load factor on future flights (seats sold / seats offered)."),
    ("_Measures","9 Lead Time & BLF","Seats Unsold","#,0","SUM ( BookingPosition[Capacity_Total] ) - SUM ( BookingPosition[Book_Total] )",""),
    ("_Measures","10 Group Booking","Group Pax Confirmed","#,0","""CALCULATE ( SUM ( GroupBooking[TTL PAX] ), GroupBooking[STATUS] IN { "TICKETED", "DEPOSIT" } )""",""),
    ("_Measures","10 Group Booking","Group Sales IDR","#,0","""CALCULATE ( SUM ( GroupBooking[Total sales ( nett x ttl pax )] ), GroupBooking[STATUS] IN { "TICKETED", "DEPOSIT" } )""",""),
    ("_Measures","10 Group Booking","Group Cancel Rate %",FPCT,"""DIVIDE ( CALCULATE ( COUNTROWS ( GroupBooking ), GroupBooking[STATUS] = "CANCELLED" ), COUNTROWS ( GroupBooking ) )""",""),
]
RELATIONSHIPS = [
    ("SalesFlown","DATES","DateTable","Date"), ("SalesFlown","DATE TRAVEL","DateFlown","Date"),
    ("SalesFlown","DATA TYPE","ValTypeTable","SalesType"), ("SalesFlown","SUBCLASS","SubclassSortOrder","BookingClass"),
    ("SalesFlown","CORP CODE","DimCorporate","CORP CODE"), ("SalesFlown","BRANCH OFFICE","DimBranchRegion","BO"),
    ("SalesFlown","ROUTEVV","DimRoute","route_vv"), ("BookingPosition","RouteVV","DimRoute","route_vv"),
    ("SalesToFlown","route_vv","DimRoute","route_vv"),
]
# ---------------------------------------------------------------- writers
def ind(text, n):
    return "\n".join((T * n + line) if line.strip() else "" for line in text.splitlines())
def m_query(table):
    fname, cols = CSV_TABLES[table]
    types = ", ".join(f'{{"{c}", {M_TYPE[t]}}}' for c, t in cols)
    return f"""let
    Source = Csv.Document(File.Contents(DataFolder & "\\{fname}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{{types}}}, "en-US")
in
    Typed"""
def measure_block(tbl):
    out = []
    for t, folder, name, fmt, expr, _ in M:
        if t != tbl:
            continue
        out.append(f"{T*2}measure {q(name)} =\n{ind(expr, 4)}")
        out.append(f"{T*3}formatString: {fmt}")
        out.append(f"{T*3}displayFolder: {folder}")
        out.append("")
    return out
def calc_col_block(tbl):
    out = []
    for name, expr, sort in CALC_COLUMNS.get(tbl, []):
        out.append(f"{T*2}column {q(name)} =\n{ind(expr, 4)}")
        out.append(f"{T*3}summarizeBy: none")
        if sort:
            out.append(f"{T*3}sortByColumn: {q(sort)}")
        out.append("")
    return out
def tmdl():
    L = ["createOrReplace", "",
         f'{T}expression DataFolder = "C:\\airline-sales-performance-bi\\data\\model" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]', ""]
    for tbl, (fname, cols) in CSV_TABLES.items():
        L.append(f"{T}table {q(tbl)}")
        L.append("")
        L += measure_block(tbl)
        for c, t in cols:
            L.append(f"{T*2}column {q(c)}")
            L.append(f"{T*3}dataType: {TMDL_TYPE[t]}")
            if t in ("int64", "double"):
                L.append(f"{T*3}formatString: #,0" if c not in ("FltNbr","DOW","Bulan","Tahun","MO","WEEK","WEEK NUM","year") else f"{T*3}formatString: 0")
                L.append(f"{T*3}summarizeBy: {'sum' if c in ('PAX','NETT USD','BASIC FARE USD','Book_Total','Capacity_Total','pax','TTL PAX','JMLH PAX DEPO') else 'none'}")
            else:
                if t == "date":
                    L.append(f"{T*3}formatString: dd mmm yyyy")
                L.append(f"{T*3}summarizeBy: none")
            L.append(f"{T*3}sourceColumn: {c}")
            L.append("")
        L += calc_col_block(tbl)
        L.append(f"{T*2}partition {q(tbl)} = m")
        L.append(f"{T*3}mode: import")
        L.append(f"{T*3}source =")
        L.append(ind(m_query(tbl), 5))
        L.append("")
    for tbl, (expr, cols) in CALC_TABLES.items():
        L.append(f"{T}table {q(tbl)}")
        if tbl in ("DateTable", "DateFlown"):
            L.append(f"{T*2}dataCategory: Time")
        L.append("")
        L += measure_block(tbl)
        for c in cols:
            L.append(f"{T*2}column {q(c)}")
            if tbl in ("DateTable", "DateFlown") and c == "Date":
                L.append(f"{T*3}isKey")
                L.append(f"{T*3}formatString: dd mmm yyyy")
            if tbl == "_Measures":
                L.append(f"{T*3}isHidden")
            L.append(f"{T*3}summarizeBy: none")
            L.append(f"{T*3}isNameInferred")
            L.append(f"{T*3}sourceColumn: [{c}]")
            if (tbl, c) in SORT_BY:
                L.append(f"{T*3}sortByColumn: {q(SORT_BY[(tbl, c)])}")
            L.append("")
        L += calc_col_block(tbl)
        L.append(f"{T*2}partition {q(tbl)} = calculated")
        L.append(f"{T*3}mode: import")
        L.append(f"{T*3}source =")
        L.append(ind(expr, 5))
        L.append("")
    for ft, fc, tt, tc in RELATIONSHIPS:
        rid = re.sub(r"\W", "_", f"{ft}_{fc}_to_{tt}")
        L.append(f"{T}relationship {rid}")
        L.append(f"{T*2}fromColumn: {q(ft)}.{q(fc)}")
        L.append(f"{T*2}toColumn: {q(tt)}.{q(tc)}")
        L.append("")
    return "\n".join(L).rstrip() + "\n"
def dax_query():
    L = ["// All measures as a DAX query. Paste into Power BI Desktop > DAX query view and run.", "DEFINE"]
    for t, folder, name, fmt, expr, _ in M:
        L.append(f"{T}MEASURE {q(t)}[{name}] =\n{ind(expr, 2)}")
    L.append("EVALUATE\n\tSUMMARIZECOLUMNS (\n\t\tDateTable[Year],\n\t\tValTypeTable[SalesType],\n\t\t\"Revenue TY\", [Revenue TY],\n\t\t\"Revenue LY\", [Revenue LY],\n\t\t\"Revenue YoY %\", [Revenue YoY %],\n\t\t\"Pax TY\", [Pax TY],\n\t\t\"Avg Fare TY\", [Avg Fare TY]\n\t)")
    return "\n".join(L) + "\n"
def catalog():
    L = ["# Measure catalog", "", f"{len(M)} measures, all stored in the `_Measures` table and grouped by display folder.", ""]
    cur = None
    for t, folder, name, fmt, expr, note in M:
        if folder != cur:
            L += ["", f"## {folder}", "", "| Measure | Format | Notes |", "|---|---|---|"]
            cur = folder
        L.append(f"| `{name}` | `{fmt}` | {note} |")
    return "\n".join(L) + "\n"
if __name__ == "__main__":
    (ROOT / "powerbi").mkdir(exist_ok=True)
    (ROOT / "dax").mkdir(exist_ok=True)
    (ROOT / "powerbi" / "semantic_model.tmdl").write_text(tmdl())
    (ROOT / "dax" / "measures.dax").write_text(dax_query())
    (ROOT / "docs" / "measure_catalog.md").write_text(catalog())
    print(f"tables={len(CSV_TABLES) + len(CALC_TABLES)} measures={len(M)} relationships={len(RELATIONSHIPS)}")
