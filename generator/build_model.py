"""Runs the SQL layer (DuckDB) over data/raw and writes the Power BI-ready files to data/model.
Usage: python generator/build_model.py --asof 2026-09-29
"""
import argparse, pathlib, duckdb
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT, SQL = ROOT / "data" / "raw", ROOT / "data" / "model", ROOT / "sql" / "duckdb"
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default="2026-09-29")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    cast = "SELECT * REPLACE (CAST(doi AS DATE) AS doi, CAST(dot AS DATE) AS dot) FROM read_parquet"
    con.execute(f"CREATE VIEW sales_all AS {cast}('{RAW}/sales_*.parquet')")
    con.execute(f"CREATE VIEW flown_all AS {cast}('{RAW}/flown_*.parquet')")
    con.execute(f"CREATE VIEW booking_position AS SELECT * FROM read_parquet('{RAW}/booking_position.parquet')")
    for t in ["ref_channel_group", "ref_corporate", "ref_branch_region", "ref_route"]:
        con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('{RAW}/{t}.csv')")
    for f in sorted(SQL.glob("*.sql")):
        con.execute(f.read_text().replace("{asof}", a.asof))
    exports = {
        "fact_sales_flown": "SELECT * FROM fact_sales_flown ORDER BY ALL",
        "fact_sales_to_flown": "SELECT * FROM fact_sales_to_flown ORDER BY ALL",
        "fact_booking_position": "SELECT * FROM fact_booking_position ORDER BY ALL",
        "dim_corporate": "SELECT corporate_code AS \"CORP CODE\", corporate_name AS CORPORATE_NAME, corporate_cluster AS CORPORATE_CLUSTER, industry_type AS INDUSTRY_TYPE FROM ref_corporate",
        "dim_branch_region": "SELECT * FROM ref_branch_region",
        # one row per round-trip AND one-way itinerary key so fact, BLF and lead-time tables all join to it
        "dim_route": """SELECT route_vv, 'RT' AS itinerary, dest, service_type, subservice, aircraft, status FROM ref_route
                        UNION ALL SELECT 'CGK' || dest, 'OW', dest, service_type, subservice, aircraft, status FROM ref_route""",
    }
    for name, q in exports.items():
        con.execute(f"COPY ({q}) TO '{OUT}/{name}.csv' (HEADER, DELIMITER ',')")
        print(f"{name:24s} {con.execute(f'SELECT COUNT(*) FROM ({q})').fetchone()[0]:>9,} rows")
    (OUT / "group_bookings.csv").write_bytes((RAW / "group_bookings.csv").read_bytes())
if __name__ == "__main__":
    main()
