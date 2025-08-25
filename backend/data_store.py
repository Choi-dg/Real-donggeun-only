import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict, Any

@contextmanager
def get_conn(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()

def init_db(db_path: str):
    with get_conn(db_path) as conn:
        c = conn.cursor()
        c.execute("""        CREATE TABLE IF NOT EXISTS quotes (
            ticker TEXT,
            asof TEXT,
            price REAL,
            pe_ttm REAL,
            pb REAL,
            ev_ebitda REAL,
            market_cap REAL,
            updated_at TEXT,
            PRIMARY KEY (ticker, asof)
        )
        """ )
        c.execute("""        CREATE TABLE IF NOT EXISTS news (
            ticker TEXT,
            published TEXT,
            source TEXT,
            title TEXT,
            url TEXT,
            summary TEXT,
            fetched_at TEXT
        )
        """ )
        conn.commit()

def upsert_quote(db_path: str, row: Dict[str, Any]):
    with get_conn(db_path) as conn:
        c = conn.cursor()
        c.execute("""        INSERT OR REPLACE INTO quotes (ticker, asof, price, pe_ttm, pb, ev_ebitda, market_cap, updated_at)
        VALUES (:ticker, :asof, :price, :pe_ttm, :pb, :ev_ebitda, :market_cap, :updated_at)
        """ , row)
        conn.commit()

def insert_news_batch(db_path: str, rows: List[Dict,]):
    if not rows:
        return
    with get_conn(db_path) as conn:
        c = conn.cursor()
        c.executemany("""        INSERT INTO news (ticker, published, source, title, url, summary, fetched_at)
        VALUES (:ticker, :published, :source, :title, :url, :summary, :fetched_at)
        """ , rows)
        conn.commit()

def query_latest_quotes(db_path: str, tickers: List[str]):
    if not tickers:
        return []
    with get_conn(db_path) as conn:
        q = "SELECT * FROM quotes WHERE ticker IN ({}) ORDER BY ticker, asof DESC".format(
            ",".join(["?"]*len(tickers))
        )
        cur = conn.execute(q, tickers)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

def query_news(db_path: str, ticker: str, limit: int = 50):
    with get_conn(db_path) as conn:
        q = """        SELECT published, source, title, url, summary FROM news
        WHERE ticker = ? ORDER BY published DESC LIMIT ?
        """
        return conn.execute(q, (ticker, limit)).fetchall()
