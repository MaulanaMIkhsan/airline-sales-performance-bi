# Refactor notes

Changes made while rebuilding the production model for this public version. Each one keeps the original business result unless marked **Fix**.

## Model

| Area | Before | After | Why |
|---|---|---|---|
| Route status | 80-value `SWITCH` grouping column on the fact table listing every route | `DimRoute[status]` + `RELATED()` | New route = one row in a table, not a model edit |
| BLF link | Many-to-many relationship fact `ROUTEVV` to BLF `RouteVV` | Both facts point to `DimRoute` | Clean star, no ambiguous filter paths |
| Corporate link | Many-to-many to an Excel corporate list | Many-to-one to `DimCorporate` (keys de-duplicated upstream) | Predictable filtering, smaller model |
| Measure homes | Measures spread over 8 slicer / helper tables | One `_Measures` table with numbered display folders | Easier to find, review, and hand over |
| Fare family | `SUBCLASS IN {...}` lists repeated inside 6 measures | `SubclassSortOrder[FareFamily]` and `[Cabin]` columns | Mapping lives in one place and can be used on axes |
| Week number | Hard-coded first Monday per year in SQL | Computed first Monday, independent of `@@DATEFIRST` | Works for any year |

## DAX

| Measure(s) | Before | After |
|---|---|---|
| `RBD F` ... `RBD X` | 26 copies of the same `CALCULATE` with a different subclass | Removed. `[Revenue TY]` or `[Fare Family Share %]` with `SubclassSortOrder[BookingClass]` on columns |
| `FPA JCDI %`, `Y %`, `WBMKN %`, `QTV %`, `SHL %`, `ROX %` | Each repeated the cut-off logic and a hard-coded subclass list | One-liners over `[Fare Family Share %]` |
| `_TargetDate` | `IF ( ctx = data, data, ctx )` | `[_MaxDateInContext]`. Both branches return the same value |
| `Date chusd Last Year (Daily)` | `ISFILTERED` branch plus two `CALCULATE` paths | `Revenue LY`: one `CALCULATE` with `SAMEPERIODLASTYEAR` + `KEEPFILTERS` cut-off. Same result at every grain |
| `DOW Name chusd` | Exact duplicate of `Date chusd This Year` | Removed |
| `Test Total` | Leftover debug measure | Removed |
| `RevSales YTD LY` | **Fix.** Anchored on each row's own date, while `RevSales MTD LY` anchored on the data cut-off, so the MTD/YTD switch compared different LY windows | Both anchor on `_TargetDate` via `DATESBETWEEN` |
| `Domestic %`, `International %` | **Fix.** Denominator kept the service-type filter, so a DOM/INT slicer made both show 100% / blank | Denominator uses `REMOVEFILTERS ( SalesFlown[SERVICE TYPE] )` |
| MTD/YTD LY | `ALL ( DateTable )` + two date comparisons | `ALL ( DateTable )` + `DATESBETWEEN` (same result, easier to read) |

## Added

- `Pull Out Revenue Recaptured %`: revenue gained on active routes divided by revenue lost on pulled-out routes between two periods.
- `Avg Lead Time (days)`: pax-weighted booking lead time.
- `Seats Unsold`, `Group Pax Confirmed`, `Group Sales IDR`, `Group Cancel Rate %`.

## Known definition to be aware of

`PAX` for **Sales** counts distinct tickets per fact row, and a round trip has two coupons on two route rows, so sales pax is segment-based. **Flown** pax counts the first-coupon flag only, so it is journey-based. This matches the production rule; compare Sales with Sales and Flown with Flown.
