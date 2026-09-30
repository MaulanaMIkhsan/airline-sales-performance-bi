# Data dictionary

All files in `data/model/` are produced by `generator/build_model.py`. Everything is synthetic.

## fact_sales_flown.csv (Power BI: `SalesFlown`)

Grain: data type x date x agent x route x booking class x corporate x channel.

| Column | Type | Description |
|---|---|---|
| DATA TYPE | text | `Sales` (issued tickets, dated by issue date) or `Flown` (coupons flown, dated by travel date) |
| SERVICE TYPE | text | `DOM` / `INT` |
| SUBSERVICE | text | Sales region of the route (JKT, DPS, MES, SUB, UPG, ASA, CTH, JPK, SWP, MEA, EUR) |
| AGEN NO, AGENT NAME, AGENT GROUPING | text | Issuing agent (synthetic IATA-style numbers `99xxxxxx`) |
| POI | text | Point of issue city |
| BRANCH OFFICE | text | Sales branch that owns the agent |
| BO POO | text | Branch of the journey's point of origin |
| ROUTEVV | text | Itinerary key, `CGKDPSCGK` (round trip) or `CGKDPS` (one way) |
| ROUTE | text | Coupon segment, e.g. `CGKDPS` |
| DATES | date | Issue date for Sales, travel date for Flown |
| DATE TRAVEL | date | Travel date on Sales rows (blank for Flown) |
| CORP CODE, CORP NAME, CORPORATE CLUSTER | text | Corporate deal (blank = non-corporate) |
| GROUPING CHANNEL | text | DIRECT OFFICE, GSA, TRAVEL AGENT, WEB/MOB, OTA |
| SUBCLASS | text | Booking class (RBD), 26 values F..X |
| CORP SHARE | text | `Corp` / `Non Corp` |
| AREA | text | DOM / INT / MEA |
| PAX | int | Passengers (see refactor notes for sales vs flown definition) |
| NETT USD | decimal | Gross fare - discount + YQ surcharge |
| BASIC FARE USD | decimal | Gross fare |
| WEEK NUM | int | Airline sales week (week 1 = days before first Monday) |

## fact_sales_to_flown.csv (`SalesToFlown`)

Flown passengers by booking lead time: `route_vv`, `servicetypecode`, `sales_to_flown` (days from issue to travel), `trip_duration` (days, round trips), `trip_type` (OW/RT), `year`, `pax`.

## fact_booking_position.csv (`BookingPosition`)

Forward inventory snapshot per flight leg for the next 12 months: flight number, departure time `STD`, route, aircraft type, days to departure `DiffDate`, `Book_Total`, `Capacity_Total`.

## group_bookings.csv (`GroupBooking`)

Group desk tracking sheet (IDR): booking date, PNR, group, agent, route, pax, approved fare, YQ, tax, status (TICKETED / DEPOSIT / OPTION / CANCELLED), deposits, cancel reason.

## Dimensions

| File | Key | Columns |
|---|---|---|
| dim_route.csv | route_vv | itinerary (RT/OW), dest, service_type, subservice, aircraft, status (Active / Pull Out) |
| dim_corporate.csv | CORP CODE | CORPORATE_NAME, CORPORATE_CLUSTER, INDUSTRY_TYPE |
| dim_branch_region.csv | BO | REGION |

## Synthetic scenario built into the data

- Demand seasonality: Eid al-Fitr travel peaks (2025, 2026, 2027), year-end and school holidays, Friday/Sunday travel peaks.
- 2026 grows ~6% on average with route-level variation.
- Routes TNJ, MLG, BKS, CAN are pulled out from 1 Apr 2026.
- Late bookers and corporates skew to higher booking classes; corporates get deal discounts.
- ~3.5% refunds and ~2% no-shows, plus FIM/EMD and interline rows that the SQL filters out.
