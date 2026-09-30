# Measure catalog

82 measures, all stored in the `_Measures` table and grouped by display folder.


## 0 Helpers

| Measure | Format | Notes |
|---|---|---|
| `_MaxDateInData` | `dd mmm yyyy` | Latest loaded date (the data cut-off). Every TY/LY measure is capped at this date so partial days/months compare like for like. |
| `_MaxDateInContext` | `dd mmm yyyy` | Latest date visible in the current filter context. |
| `_TargetDate` | `dd mmm yyyy` | Anchor date for MTD/YTD. Original was IF(ctx = data, data, ctx), which always returns ctx, so it is simplified. |
| `_MaxWeek` | `0` | Latest airline sales week in context. |
| `_MaxTravelDateInData` | `dd mmm yyyy` | Latest travel date on any ticket, used by the travel-date page. |
| `Data As Of` | `dd mmm yyyy` | Card subtitle: shows the cut-off date of the data behind the visual. |

## 1 Base

| Measure | Format | Notes |
|---|---|---|
| `Revenue` | `#,0` | Nett revenue in USD (gross - discount + YQ). |
| `Pax` | `#,0` | Passengers. Sales = tickets per coupon row, Flown = tickets on first-coupon flag. |
| `Avg Fare` | `#,0` | Revenue per pax. |

## 2 TY vs LY

| Measure | Format | Notes |
|---|---|---|
| `Revenue TY` | `#,0` | This-year revenue up to the data cut-off. Works at day, week, month or year level. |
| `Revenue LY` | `#,0` | Same period last year, capped at cut-off minus 12 months so a half-finished month is never compared with a full one. |
| `Revenue YoY` | `#,0` |  |
| `Revenue YoY %` | `0.0%;-0.0%;0.0%` |  |
| `Pax TY` | `#,0` |  |
| `Pax LY` | `#,0` |  |
| `Pax YoY` | `#,0` |  |
| `Pax YoY %` | `0.0%;-0.0%;0.0%` |  |
| `Avg Fare TY` | `#,0` |  |
| `Avg Fare LY` | `#,0` |  |
| `Avg Fare YoY` | `#,0` |  |
| `Avg Fare YoY %` | `0.0%;-0.0%;0.0%` |  |
| `Revenue Same Date LY` | `#,0` | Calendar-date match (1 Mar vs 1 Mar) for daily line charts; blank after the cut-off so the line stops. |

## 3 MTD YTD

| Measure | Format | Notes |
|---|---|---|
| `Revenue MTD` | `#,0` |  |
| `Revenue MTD LY` | `#,0` | Month to the same day last year. DATESBETWEEN replaces the two >= / <= filters of the original. |
| `Revenue MTD YoY %` | `0.0%;-0.0%;0.0%` |  |
| `Revenue YTD` | `#,0` |  |
| `Revenue YTD LY` | `#,0` |  |
| `Revenue YTD YoY %` | `0.0%;-0.0%;0.0%` |  |
| `Pax MTD` | `#,0` |  |
| `Pax MTD LY` | `#,0` |  |
| `Pax MTD YoY %` | `0.0%;-0.0%;0.0%` |  |
| `Pax YTD` | `#,0` |  |
| `Pax YTD LY` | `#,0` |  |
| `Pax YTD YoY %` | `0.0%;-0.0%;0.0%` |  |
| `Avg Fare MTD` | `#,0` |  |
| `Avg Fare MTD LY` | `#,0` |  |
| `Avg Fare MTD YoY %` | `0.0%;-0.0%;0.0%` |  |
| `Avg Fare YTD` | `#,0` |  |
| `Avg Fare YTD LY` | `#,0` |  |
| `Avg Fare YTD YoY %` | `0.0%;-0.0%;0.0%` |  |

## 4 Period Switch

| Measure | Format | Notes |
|---|---|---|
| `Revenue Selected Period` | `#,0` | One visual, user flips MTD / YTD with a slicer (field-parameter style without field parameters). |
| `Revenue Selected Period LY` | `#,0` | Fix vs original: YTD LY now anchors on the target date like MTD LY (original used each row's own date). |
| `Revenue Selected Period YoY` | `#,0` |  |
| `Revenue Selected Period YoY %` | `0.0%;-0.0%;0.0%` |  |

## 5 Period vs Period

| Measure | Format | Notes |
|---|---|---|
| `Revenue P1` | `#,0` | Uses disconnected slicer Calendar_Slicer1 so two date ranges can be compared on one page. |
| `Pax P1` | `#,0` | Uses disconnected slicer Calendar_Slicer1 so two date ranges can be compared on one page. |
| `Revenue P2` | `#,0` | Uses disconnected slicer Calendar_Slicer2 so two date ranges can be compared on one page. |
| `Pax P2` | `#,0` | Uses disconnected slicer Calendar_Slicer2 so two date ranges can be compared on one page. |
| `Avg Fare P1` | `#,0` |  |
| `Avg Fare P2` | `#,0` |  |
| `Revenue P2 vs P1` | `#,0` |  |
| `Revenue P2 vs P1 %` | `0.0%;-0.0%;0.0%` |  |
| `Pax P2 vs P1` | `#,0` |  |
| `Pax P2 vs P1 %` | `0.0%;-0.0%;0.0%` |  |
| `Avg Fare P2 vs P1 %` | `0.0%;-0.0%;0.0%` |  |
| `Revenue PO P1` | `#,0` | Uses disconnected slicer Calendar_Slicer_PO1 so two date ranges can be compared on one page. |
| `Pax PO P1` | `#,0` | Uses disconnected slicer Calendar_Slicer_PO1 so two date ranges can be compared on one page. |
| `Revenue PO P2` | `#,0` | Uses disconnected slicer Calendar_Slicer_PO2 so two date ranges can be compared on one page. |
| `Pax PO P2` | `#,0` | Uses disconnected slicer Calendar_Slicer_PO2 so two date ranges can be compared on one page. |

## 6 Pull Out

| Measure | Format | Notes |
|---|---|---|
| `Revenue PO P2 vs P1 %` | `0.0%;-0.0%;0.0%` |  |
| `Pax PO P2 vs P1 %` | `0.0%;-0.0%;0.0%` |  |
| `Pull Out Revenue Recaptured %` | `0.0%;-0.0%;0.0%` | New: share of revenue lost on discontinued routes that shows up as growth on remaining routes. |

## 7 Mix

| Measure | Format | Notes |
|---|---|---|
| `Domestic %` | `0%` | Fix vs original: denominator removes the service filter, so the % stays correct when a DOM/INT slicer is used. |
| `International %` | `0%` |  |
| `Corporate Share %` | `0%` |  |
| `Fare Family Share %` | `0%` | Put SubclassSortOrder[FareFamily] or [BookingClass] on rows/columns. Replaces 26 copy-paste 'RBD x' measures plus 6 fare-family % measures. |
| `FPA JCDI %` | `0%` | Card-friendly shortcut over Fare Family Share %. |
| `ROX %` | `0%` | Card-friendly shortcut over Fare Family Share %. |
| `Y %` | `0%` | Card-friendly shortcut over Fare Family Share %. |
| `WBMKN %` | `0%` | Card-friendly shortcut over Fare Family Share %. |
| `QTV %` | `0%` | Card-friendly shortcut over Fare Family Share %. |
| `SHL %` | `0%` | Card-friendly shortcut over Fare Family Share %. |

## 8 Travel Date

| Measure | Format | Notes |
|---|---|---|
| `Pax by Travel Date TY` | `#,0` | Sales pax by departure date (forward-looking on-the-books view). |
| `Pax by Travel Date LY` | `#,0` |  |
| `Pax by Travel Date YoY %` | `0%` |  |

## 9 Lead Time & BLF

| Measure | Format | Notes |
|---|---|---|
| `% of Total Pax (Lead Time)` | `0.0%;-0.0%;0.0%` | Booking curve share: how early passengers buy before departure. |
| `Avg Lead Time (days)` | `0.0` | New: pax-weighted average days between purchase and departure. |
| `BLF %` | `0.0%;-0.0%;0.0%` | Booked load factor on future flights (seats sold / seats offered). |
| `Seats Unsold` | `#,0` |  |

## 10 Group Booking

| Measure | Format | Notes |
|---|---|---|
| `Group Pax Confirmed` | `#,0` |  |
| `Group Sales IDR` | `#,0` |  |
| `Group Cancel Rate %` | `0.0%;-0.0%;0.0%` |  |
