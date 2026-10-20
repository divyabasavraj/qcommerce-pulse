"""DuckDB connection with a `reviews` view over the monthly Parquet files."""
import duckdb

from qpulse.config import DB_PATH, RAW_DIR


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH), read_only=read_only)
    if not read_only:
        con.execute(f"""
            CREATE OR REPLACE VIEW reviews AS
            SELECT * FROM read_parquet('{RAW_DIR.as_posix()}/reviews_*.parquet')
        """)
    return con
