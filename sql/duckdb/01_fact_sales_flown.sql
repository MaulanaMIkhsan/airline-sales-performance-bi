-- Builds the reporting fact table (one grain for both Sales and Flown) from coupon-level extracts.
-- DuckDB dialect, run by generator/build_model.py. The SQL Server version lives in sql/tsql/.
-- Business rules
--   Sales : coupons issued (DOI) with status Flown or Unutilised; PAX = distinct tickets
--   Flown : coupons flown (DOT); PAX = distinct tickets on the first-coupon flag (note = 1)
--   Both  : doctype PAX/FIM only, exclude interline/codeshare markers in oprt_aln
--   NETT  : gross - discount + YQ (carrier surcharge), in USD
CREATE OR REPLACE TABLE fact_sales_flown AS
WITH cluster AS (                                   -- de-duplicated once, joined once
    SELECT DISTINCT corporate_code, corporate_cluster FROM ref_corporate
),
unioned AS (                                        -- raw rows only: no joins, no grouping here
    SELECT 'Flown' AS data_type, servicetypecode, subservicecode, agent_no, agent_grouping, poi, branch_office,
           route_vv, route, dot AS dates, CAST(NULL AS DATE) AS date_travel, corporate_code, channel_iata AS channel,
           subclass, bo_poo, agent_name, corporate,
           CASE WHEN note = 1 THEN ticket_no END AS pax_ticket, gross_usd, disc_usd, yq_usd
    FROM flown_all
    WHERE cpnsts = 'Flown' AND doctype IN ('PAX','FIM') AND oprt_aln NOT IN ('//','/-','s')
    UNION ALL
    SELECT 'Sales', servicetypecode, subservicecode, agent_no, agent_grouping, poi, branch_office,
           route_vv, route, doi, dot, corporate_code, channel_iata,
           subclass, bo_poo, agent_name, corporate,
           ticket_no, gross_usd, disc_usd, yq_usd
    FROM sales_all
    WHERE cpnsts IN ('Flown','Unutilised') AND doctype IN ('PAX','FIM') AND oprt_aln NOT IN ('//','/-','s')
),
agg AS (                                            -- joins + aggregation happen once
    SELECT
        u.data_type                                  AS "DATA TYPE",
        u.servicetypecode                            AS "SERVICE TYPE",
        u.subservicecode                             AS "SUBSERVICE",
        u.agent_no                                   AS "AGEN NO",
        u.agent_grouping                             AS "AGENT GROUPING",
        u.poi                                        AS "POI",
        u.branch_office                              AS "BRANCH OFFICE",
        u.route_vv                                   AS "ROUTEVV",
        u.route                                      AS "ROUTE",
        u.dates                                      AS "DATES",
        u.corporate_code                             AS "CORP CODE",
        rg.Grouping_channel                          AS "GROUPING CHANNEL",
        u.subclass                                   AS "SUBCLASS",
        u.bo_poo                                     AS "BO POO",
        cd.corporate_name                            AS "CORP NAME",
        cc.corporate_cluster                         AS "CORPORATE CLUSTER",
        u.agent_name                                 AS "AGENT NAME",
        CASE WHEN u.corporate IN ('corp','corv','corx') THEN 'Corp' ELSE 'Non Corp' END AS "CORP SHARE",
        CASE WHEN u.subservicecode IN ('DPS','JKT','MES','SUB','UPG') THEN 'DOM'
             WHEN u.subservicecode IN ('CTH','ASA','JPK','SWP','EUR') THEN 'INT'
             WHEN u.subservicecode = 'MEA' THEN 'MEA'
             ELSE u.subservicecode END               AS "AREA",
        u.date_travel                                AS "DATE TRAVEL",
        COUNT(DISTINCT u.pax_ticket)                 AS "PAX",
        ROUND(SUM(COALESCE(u.gross_usd,0) - COALESCE(u.disc_usd,0) + COALESCE(u.yq_usd,0)), 2) AS "NETT USD",
        ROUND(SUM(COALESCE(u.gross_usd,0)), 2)       AS "BASIC FARE USD"
    FROM unioned u
    LEFT JOIN ref_channel_group rg ON u.channel = rg.Channel
    LEFT JOIN ref_corporate     cd ON u.corporate_code = cd.corporate_code
    LEFT JOIN cluster           cc ON u.corporate_code = cc.corporate_code
    GROUP BY ALL
),
base AS (                                           -- first Monday of each year (dayofweek: Sun=0)
    SELECT agg.*,
           CAST(make_date(year("DATES"), 1, 1)
                + to_days(CAST((8 - dayofweek(make_date(year("DATES"), 1, 1))) % 7 AS INTEGER)) AS DATE) AS first_monday
    FROM agg
)
SELECT * EXCLUDE (first_monday),
       -- airline sales week: week 1 = days before the first Monday, then Monday-based weeks
       CASE WHEN "DATES" < first_monday THEN 1
            ELSE CAST(FLOOR(date_diff('day', first_monday, "DATES") / 7) AS INTEGER) + 2 END AS "WEEK NUM"
FROM base;
