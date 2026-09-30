-- Forward booking position (next 12 months) aggregated per flight leg, used for Booked Load Factor (BLF).
-- In production this reads an inventory snapshot table refreshed daily; here the snapshot is synthetic.
CREATE OR REPLACE TABLE fact_booking_position AS
SELECT RegionCode, FltNbr, DOW, Bulan, FlightType, SubServiceCode, Tahun, TipeAircraft, STD, ServiceTypeCode,
       RouteVV, Route, Depart, Arrived, DiffDate,
       SUM(Book_Total)     AS Book_Total,
       SUM(Capacity_Total) AS Capacity_Total
FROM booking_position
WHERE CAST(STD AS DATE) BETWEEN DATE '{asof}' + 1 AND DATE '{asof}' + INTERVAL 12 MONTH
GROUP BY ALL;
