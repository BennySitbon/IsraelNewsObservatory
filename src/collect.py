import json, hashlib, re, os
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
import feedparser
from dateutil import parser as dateparser
from src.db import init_db, connect
from src.classifier import classify

NOW = datetime.now(timezone.utc).isoformat()

def clean_url(url):
    if not url:
        return ""
    p = urlsplit(url.strip())
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", ""))

def parse_date(entry):
    value = entry.get("published") or entry.get("updated")
    if value:
        try:
            dt = dateparser.parse(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    return None

def main():
    init_db()
    with open("feeds.json", encoding="utf-8") as f:
        feeds = json.load(f)
    with connect() as db:
        cur = db.execute("INSERT INTO runs(started_at,status) VALUES(?,?)", (NOW, "running"))
        run_id = cur.lastrowid
    seen = new_count = 0
    errors = []
    for feed in feeds:
    if not feed.get("enabled") or not feed.get("url"):
        print(f"Skipping {feed['name']}: disabled or missing URL", flush=True)
        continue

    print(f"Fetching {feed['name']}...", flush=True)

    try:
        parsed = feedparser.parse(
            feed["url"],
            request_headers={"User-Agent": "IsraelNewsObservatory/0.1 (personal research)"}
        )

        print(
            f"{feed['name']}: received {len(parsed.entries)} entries",
            flush=True
        )
            if parsed.bozo and not parsed.entries:
                raise RuntimeError(str(parsed.bozo_exception))
            for entry in parsed.entries[:100]:
                title = re.sub(r"\s+", " ", entry.get("title", "")).strip()
                link = clean_url(entry.get("link", ""))
                if not title or not link:
                    continue
                seen += 1
                published = parse_date(entry)
                summary = re.sub("<[^>]+>", " ", entry.get("summary", "") or "")
                with connect() as db:
                    row = db.execute("SELECT id FROM articles WHERE url=?", (link,)).fetchone()
                    if row:
                        article_id = row["id"]
                    else:
                        result = classify(title, summary)
                        db.execute("""
                          INSERT INTO articles(url,source,title,published_at,first_seen_at,category,subcategory,
                          sentiment,negativity_score,severity,is_human_tragedy,is_good_news,confidence,
                          classification_reason,classifier)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (link, feed["name"], title, published, NOW, result.get("category","אחר"),
                              result.get("subcategory",""), result.get("sentiment","ניטרלי"),
                              float(result.get("negativity_score",0)), result.get("severity","נמוכה"),
                              int(bool(result.get("is_human_tragedy"))), int(bool(result.get("is_good_news"))),
                              float(result.get("confidence",0)), result.get("reason",""), result.get("classifier","unknown")))
                        article_id = db.execute("SELECT id FROM articles WHERE url=?", (link,)).fetchone()["id"]
                        new_count += 1
                    db.execute("INSERT INTO observations(article_id,source,observed_at,observed_title,feed_name) VALUES(?,?,?,?,?)",
                               (article_id, feed["name"], NOW, title, feed["name"]))
        except Exception as e:
            error = f'{feed["name"]}: {type(e).__name__}: {e}'
            errors.append(error)
            print(f"ERROR: {error}", flush=True)
    with connect() as db:
        db.execute("UPDATE runs SET finished_at=?,status=?,items_seen=?,new_articles=?,errors=? WHERE id=?",
                   (datetime.now(timezone.utc).isoformat(), "partial" if errors else "success",
                    seen, new_count, "\n".join(errors), run_id))
    print(f"Run {run_id}: {seen} feed items, {new_count} new articles, {len(errors)} errors")
    if errors:
        print("\n".join(errors))

if __name__ == "__main__":
    main()
