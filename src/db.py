import os, sqlite3
from pathlib import Path

DB_PATH = os.getenv("DATABASE_PATH", "data/news.db")

def connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          url TEXT UNIQUE NOT NULL,
          source TEXT NOT NULL,
          title TEXT NOT NULL,
          published_at TEXT,
          first_seen_at TEXT NOT NULL,
          category TEXT,
          subcategory TEXT,
          sentiment TEXT,
          negativity_score REAL,
          severity TEXT,
          is_human_tragedy INTEGER DEFAULT 0,
          is_good_news INTEGER DEFAULT 0,
          confidence REAL,
          classification_reason TEXT,
          classifier TEXT
        );
        CREATE TABLE IF NOT EXISTS observations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          article_id INTEGER NOT NULL,
          source TEXT NOT NULL,
          observed_at TEXT NOT NULL,
          observed_title TEXT NOT NULL,
          feed_name TEXT,
          FOREIGN KEY(article_id) REFERENCES articles(id)
        );
        CREATE TABLE IF NOT EXISTS runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          started_at TEXT NOT NULL,
          finished_at TEXT,
          status TEXT NOT NULL,
          items_seen INTEGER DEFAULT 0,
          new_articles INTEGER DEFAULT 0,
          errors TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_articles_seen ON articles(first_seen_at);
        CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
        CREATE INDEX IF NOT EXISTS idx_observations_time ON observations(observed_at);
        """)
