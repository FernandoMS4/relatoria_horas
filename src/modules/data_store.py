import os
from datetime import datetime

import duckdb
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data_horas", "horas.duckdb")


def get_connection() -> duckdb.DuckDBPyConnection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return duckdb.connect(DB_PATH)


def table_exists() -> bool:
    con = get_connection()
    result = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = 'horas'"
    ).fetchone()
    con.close()
    return result[0] > 0


def get_last_update() -> str | None:
    if not table_exists():
        return None
    con = get_connection()
    result = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = 'metadata'"
    ).fetchone()
    if result[0] == 0:
        con.close()
        return None
    row = con.execute("SELECT updated_at FROM metadata ORDER BY updated_at DESC LIMIT 1").fetchone()
    con.close()
    return row[0] if row else None


def save_dataframe(df: pd.DataFrame) -> None:
    con = get_connection()
    con.execute("DROP TABLE IF EXISTS horas")
    con.execute("CREATE TABLE horas AS SELECT * FROM df")
    con.execute("DROP TABLE IF EXISTS metadata")
    con.execute("CREATE TABLE metadata (updated_at VARCHAR)")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con.execute("INSERT INTO metadata VALUES (?)", [now])
    con.close()


def load_dataframe() -> pd.DataFrame:
    con = get_connection()
    df = con.execute("SELECT * FROM horas WHERE regexp_matches(MES_ANO, '^\d{2}/\d{4}$')").df()
    con.close()
    return df


def alocacao_exists() -> bool:
    con = get_connection()
    result = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = 'alocacao'"
    ).fetchone()
    con.close()
    return result[0] > 0


def save_alocacao(df: pd.DataFrame) -> None:
    con = get_connection()
    con.execute("DROP TABLE IF EXISTS alocacao")
    con.execute("CREATE TABLE alocacao AS SELECT * FROM df")
    con.close()


def load_alocacao() -> pd.DataFrame:
    con = get_connection()
    df = con.execute("SELECT * FROM alocacao").df()
    con.close()
    return df
