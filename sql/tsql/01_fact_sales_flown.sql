/* ============================================================================
   fact_sales_flown  (SQL Server / T-SQL)
   Production-style version of the query behind the Power BI import table.
   Same logic as sql/duckdb/01_fact_sales_flown.sql, written for SQL Server.
   Design notes
   - Sales (by date of issue) and Flown (by date of travel) share ONE grain, so a single
     fact table + a DATA TYPE column feeds every visual (no duplicate measures per source).
   - UNION ALL of raw rows first, joins + GROUP BY once afterwards (was 4 joined/grouped
     sub-queries originally; ~4x less join work on the server).
   - The corporate cluster lookup is de-duplicated once in a CTE instead of per branch.
   - Custom airline week number: week 1 = days before the first Monday of the year.
   ============================================================================ */
WITH cluster AS (
    SELECT DISTINCT corporate_code, corporate_cluster
    FROM   ref_corporate
),
unioned AS (
    -- Flown 2026 : PAX counted once per ticket via first-coupon flag
    SELECT 'Flown' AS data_type, f.servicetypecode, f.subservicecode, f.agent_no, f.agent_grouping,
           f.poi, f.branch_office, f.route_vv, f.route,
           f.dot AS dates, CAST(NULL AS date) AS date_travel,
           f.corporate_code, f.channel_iata AS channel, f.subclass, f.bo_poo, f.agent_name, f.corporate,
           CASE WHEN f.note = 1 THEN f.ticket_no END AS pax_ticket,
           f.gross_usd, f.disc_usd, f.yq_usd
    FROM   flown_2026 f
    WHERE  f.cpnsts = 'Flown' AND f.doctype IN ('PAX','FIM') AND f.oprt_aln NOT IN ('//','/-','s')
    UNION ALL
    -- Sales 2026 : every issued coupon still valid (flown or open)
    SELECT 'Sales', s.servicetypecode, s.subservicecode, s.agent_no, s.agent_grouping,
           s.poi, s.branch_office, s.route_vv, s.route,
           s.doi, s.dot,
           s.corporate_code, s.channel_iata, s.subclass, s.bo_poo, s.agent_name, s.corporate,
           s.ticket_no,
           s.gross_usd, s.disc_usd, s.yq_usd
    FROM   sales_2026 s
    WHERE  s.cpnsts IN ('Flown','Unutilised') AND s.doctype IN ('PAX','FIM') AND s.oprt_aln NOT IN ('//','/-','s')
    UNION ALL
    SELECT 'Flown', f.servicetypecode, f.subservicecode, f.agent_no, f.agent_grouping,
           f.poi, f.branch_office, f.route_vv, f.route, f.dot, NULL,
           f.corporate_code, f.channel_iata, f.subclass, f.bo_poo, f.agent_name, f.corporate,
           CASE WHEN f.note = 1 THEN f.ticket_no END,
           f.gross_usd, f.disc_usd, f.yq_usd
    FROM   flown_2025 f
    WHERE  f.cpnsts = 'Flown' AND f.doctype IN ('PAX','FIM') AND f.oprt_aln NOT IN ('//','/-','s')
    UNION ALL
    SELECT 'Sales', s.servicetypecode, s.subservicecode, s.agent_no, s.agent_grouping,
           s.poi, s.branch_office, s.route_vv, s.route, s.doi, s.dot,
           s.corporate_code, s.channel_iata, s.subclass, s.bo_poo, s.agent_name, s.corporate,
           s.ticket_no,
           s.gross_usd, s.disc_usd, s.yq_usd
    FROM   sales_2025 s
    WHERE  s.cpnsts IN ('Flown','Unutilised') AND s.doctype IN ('PAX','FIM') AND s.oprt_aln NOT IN ('//','/-','s')
),
agg AS (
    SELECT
        u.data_type                 AS [DATA TYPE],
        u.servicetypecode           AS [SERVICE TYPE],
        u.subservicecode            AS [SUBSERVICE],
        u.agent_no                  AS [AGEN NO],
        u.agent_grouping            AS [AGENT GROUPING],
        u.poi                       AS [POI],
        u.branch_office             AS [BRANCH OFFICE],
        u.route_vv                  AS [ROUTEVV],
        u.route                     AS [ROUTE],
        u.dates                     AS [DATES],
        u.corporate_code            AS [CORP CODE],
        rg.Grouping_channel         AS [GROUPING CHANNEL],
        u.subclass                  AS [SUBCLASS],
        u.bo_poo                    AS [BO POO],
        cd.corporate_name           AS [CORP NAME],
        cc.corporate_cluster        AS [CORPORATE CLUSTER],
        u.agent_name                AS [AGENT NAME],
        CASE WHEN u.corporate IN ('corp','corv','corx') THEN 'Corp' ELSE 'Non Corp' END AS [CORP SHARE],
        CASE WHEN u.subservicecode IN ('DPS','JKT','MES','SUB','UPG') THEN 'DOM'
             WHEN u.subservicecode IN ('CTH','ASA','JPK','SWP','EUR') THEN 'INT'
             WHEN u.subservicecode = 'MEA' THEN 'MEA'
             ELSE u.subservicecode END AS [AREA],
        u.date_travel               AS [DATE TRAVEL],
        COUNT(DISTINCT u.pax_ticket)                                            AS PAX,
        SUM(ISNULL(u.gross_usd,0) - ISNULL(u.disc_usd,0) + ISNULL(u.yq_usd,0))  AS [NETT USD],
        SUM(ISNULL(u.gross_usd,0))                                              AS [BASIC FARE USD]
    FROM      unioned u
    LEFT JOIN ref_channel_group rg ON u.channel        = rg.Channel
    LEFT JOIN ref_corporate     cd ON u.corporate_code = cd.corporate_code
    LEFT JOIN cluster           cc ON u.corporate_code = cc.corporate_code
    GROUP BY  u.data_type, u.servicetypecode, u.subservicecode, u.agent_no, u.agent_grouping,
              u.poi, u.branch_office, u.route_vv, u.route, u.dates, u.corporate_code,
              rg.Grouping_channel, u.subclass, u.bo_poo, cd.corporate_name,
              cc.corporate_cluster, u.agent_name, u.corporate, u.date_travel
),
base AS (
    SELECT agg.*,
           -- first Monday of the year, independent of @@DATEFIRST
           DATEADD(DAY, (7 - DATEDIFF(DAY, '19000101', DATEFROMPARTS(YEAR([DATES]),1,1)) % 7) % 7,
                   DATEFROMPARTS(YEAR([DATES]),1,1)) AS first_monday
    FROM agg
)
SELECT base.[DATA TYPE], base.[SERVICE TYPE], base.[SUBSERVICE], base.[AGEN NO], base.[AGENT GROUPING], base.[POI],
       base.[BRANCH OFFICE], base.[ROUTEVV], base.[ROUTE], base.[DATES], base.[CORP CODE], base.[GROUPING CHANNEL],
       base.[SUBCLASS], base.[BO POO], base.[CORP NAME], base.[CORPORATE CLUSTER], base.[AGENT NAME], base.[CORP SHARE],
       base.[AREA], base.[DATE TRAVEL], base.PAX, base.[NETT USD], base.[BASIC FARE USD],
       CASE WHEN base.[DATES] < base.first_monday THEN 1
            ELSE DATEDIFF(DAY, base.first_monday, base.[DATES]) / 7 + 2 END AS [WEEK NUM]
FROM base;
