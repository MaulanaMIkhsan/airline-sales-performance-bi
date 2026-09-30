-- Booking lead time profile: how many days before departure pax bought (H-0 ... H-121+), by trip shape.
-- Grain: route_vv x service x lead days x trip duration x trip type x flown year.
CREATE OR REPLACE TABLE fact_sales_to_flown AS
SELECT route_vv,
       servicetypecode,
       date_diff('day', doi, dot)          AS sales_to_flown,
       trip_duration,
       trip_type,
       year(dot)                           AS year,
       COUNT(*)                            AS pax
FROM flown_all
WHERE doctype = 'PAX' AND note = 1 AND cpnsts = 'Flown'
GROUP BY ALL;
