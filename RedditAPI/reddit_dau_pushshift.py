#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reddit_dau_pushshift.py

Comprehensive, incremental Reddit DAU estimator using Pushshift.
- Pulls **fresh** historical data (no reliance on local prior author lists)
- Deduplicates unique authors per day across submissions + comments
- Handles Pushshift API pagination + rate limits with retries/backoff
- Tracks progress per day to avoid double counting on re-runs
- Aggregates to **monthly DAU** and computes month-over-month growth
- Outputs: monthly table (columns=months; rows=DAU, MoM%), subreddits checked,
  representativeness estimate vs. total platform DAU via a configurable factor

Default period: 2024-09-01 to 2025-09-30 (inclusive).
"""

import os
import sys
import time
import json
import math
import sqlite3
import logging
import argparse
from datetime import datetime, timedelta, timezone, date
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Tuple, Set

import requests

# ---------- Configuration ----------
PUSHSHIFT_BASE = "https://api.pushshift.io/reddit"
# Endpoints (v2 style)
COMMENT_ENDPOINT = f"{PUSHSHIFT_BASE}/comment/search"
SUBMISSION_ENDPOINT = f"{PUSHSHIFT_BASE}/submission/search"

DB_PATH = os.path.join("data", "reddit_dau_pushshift.sqlite")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

LOG_PATH = os.path.join("data", "reddit_dau_pushshift.log")

# Requests config
REQ_TIMEOUT = 30
MAX_RETRIES = 5
BACKOFF_BASE = 1.6
BATCH_SIZE = 500  # per Pushshift call: maximum items per page
SLEEP_BETWEEN_CALLS = 0.2  # gentle pacing

# Robust user filters
EXCLUDED_AUTHORS = {"AutoModerator", "[deleted]", "[removed]", "None", ""}

# Representativeness: what fraction of total DAU are active contributors?
# You can tune this (e.g., 0.05 ~ 5%, 0.06 ~ 6%)
CONTRIBUTOR_FRACTION = 0.06

# Default date range
DEFAULT_START = date(2024, 9, 1)
DEFAULT_END = date(2025, 9, 30)

# Limit how many subreddits to print to console; full list is written to file
PRINT_SUBREDDITS_LIMIT = 100
SUBREDDITS_OUTFILE = os.path.join("data", "subreddits_checked.txt")

# ---------- Logging ----------
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger().addHandler(console)


# ---------- DB Helpers ----------
def connect_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # Track day-level progress + summary
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_dau (
        day TEXT PRIMARY KEY,            -- YYYY-MM-DD
        dau_contrib INTEGER NOT NULL,    -- unique authors (posts+comments)
        posts INTEGER NOT NULL,
        comments INTEGER NOT NULL,
        subreddits INTEGER NOT NULL,
        complete INTEGER NOT NULL DEFAULT 0, -- 1 when both comments+submissions fully fetched
        updated_at TEXT NOT NULL
    )
    """)

    # Checkpoint table per day and kind to support incremental paging
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fetch_checkpoint (
        day TEXT NOT NULL,
        kind TEXT NOT NULL,              -- 'comment' or 'submission'
        last_after INTEGER,              -- last created_utc processed (strictly growing)
        done INTEGER NOT NULL DEFAULT 0, -- 1 when fetching is complete for that (day,kind)
        retries INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (day, kind)
    )
    """)

    # For diagnostics: subreddits encountered per day
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subreddits_seen (
        day TEXT NOT NULL,
        subreddit TEXT NOT NULL,
        PRIMARY KEY (day, subreddit)
    )
    """)

    # Authors per day (optional, but helps integrity checks)
    # We won't persist all authors to keep DB smaller; dedup is in-memory per day.
    # If you want to persist, uncomment below (warning: large DB!)
    # cur.execute("""
    # CREATE TABLE IF NOT EXISTS authors_seen (
    #     day TEXT NOT NULL,
    #     author TEXT NOT NULL,
    #     PRIMARY KEY (day, author)
    # )
    # """)

    conn.commit()


# ---------- Pushshift Fetch ----------
def ps_get(url: str, params: dict) -> Optional[dict]:
    """GET with retries + backoff. Returns JSON dict or None."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=REQ_TIMEOUT)
            if r.status_code == 200:
                return r.json()
            else:
                logging.warning(f"HTTP {r.status_code} for {url} params={params}")
        except requests.RequestException as e:
            logging.warning(f"Req error: {e} for {url} params={params}")

        sleep_s = (BACKOFF_BASE ** (attempt - 1)) + (0.05 * attempt)
        logging.info(f"Backing off {sleep_s:.2f}s (attempt {attempt}/{MAX_RETRIES})…")
        time.sleep(sleep_s)
    return None


def fetch_day_stream(kind: str,
                     day: date,
                     last_after: Optional[int]) -> Tuple[List[dict], Optional[int], bool]:
    """
    Fetch one page of a day's data (comments or submissions) from Pushshift,
    sorted ascending by created_utc. Returns (items, new_last_after, done).
    """
    assert kind in ("comment", "submission")
    start_ts = int(datetime(day.year, day.month, day.day, 0, 0, tzinfo=timezone.utc).timestamp())
    end_ts = int(datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=timezone.utc).timestamp())

    endpoint = COMMENT_ENDPOINT if kind == "comment" else SUBMISSION_ENDPOINT

    after_ts = last_after + 1 if last_after else start_ts
    if after_ts > end_ts:
        # Already past end of day
        return [], last_after, True

    params = {
        "after": after_ts,
        "before": end_ts,
        "size": BATCH_SIZE,
        "sort": "asc",
        "sort_type": "created_utc",
        "fields": "author,subreddit,created_utc,id"
    }

    resp = ps_get(endpoint, params)
    if not resp or "data" not in resp:
        logging.warning(f"[{day}][{kind}] Empty/invalid response for {params}")
        return [], last_after, False

    data = resp["data"]
    if not data:
        # No more items in range
        return [], last_after, True

    # Determine new_last_after strictly increasing by created_utc
    new_last_after = data[-1].get("created_utc", after_ts)
    done = len(data) < BATCH_SIZE or new_last_after >= end_ts

    # Gentle pacing
    time.sleep(SLEEP_BETWEEN_CALLS)
    return data, new_last_after, done


# ---------- Core Day Processing ----------
def load_checkpoint(conn: sqlite3.Connection, day: date, kind: str) -> Tuple[Optional[int], bool]:
    cur = conn.cursor()
    cur.execute("SELECT last_after, done FROM fetch_checkpoint WHERE day=? AND kind=?",
                (day.isoformat(), kind))
    row = cur.fetchone()
    if row:
        return (row[0], bool(row[1]))
    # initialize
    cur.execute("INSERT OR IGNORE INTO fetch_checkpoint (day, kind, last_after, done, retries) VALUES (?, ?, ?, 0, 0)",
                (day.isoformat(), kind, None))
    conn.commit()
    return None, False


def save_checkpoint(conn: sqlite3.Connection, day: date, kind: str,
                    last_after: Optional[int], done: bool) -> None:
    cur = conn.cursor()
    cur.execute("""
        UPDATE fetch_checkpoint
           SET last_after=?, done=?
         WHERE day=? AND kind=?
    """, (last_after, int(done), day.isoformat(), kind))
    conn.commit()


def upsert_daily(conn: sqlite3.Connection, day: date,
                 dau: int, posts: int, comments: int, subreddits: int, complete: bool) -> None:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO daily_dau (day, dau_contrib, posts, comments, subreddits, complete, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(day) DO UPDATE SET
            dau_contrib=excluded.dau_contrib,
            posts=excluded.posts,
            comments=excluded.comments,
            subreddits=excluded.subreddits,
            complete=excluded.complete,
            updated_at=excluded.updated_at
    """, (day.isoformat(), dau, posts, comments, subreddits, int(complete), datetime.utcnow().isoformat()))
    conn.commit()


def add_subreddits(conn: sqlite3.Connection, day: date, subs: Set[str]) -> None:
    if not subs:
        return
    cur = conn.cursor()
    cur.executemany("""
        INSERT OR IGNORE INTO subreddits_seen (day, subreddit) VALUES (?, ?)
    """, [(day.isoformat(), s) for s in subs])
    conn.commit()


def process_day(conn: sqlite3.Connection, day: date) -> None:
    """
    Fetch full day's comments+submissions with pagination, dedup authors,
    and write daily summary. Safe to re-run; uses checkpoints to avoid double work.
    """
    logging.info(f"📅 Processing day {day} …")

    # In-memory sets for the day
    authors: Set[str] = set()
    subs_seen: Set[str] = set()
    posts_cnt = 0
    comments_cnt = 0

    complete = True  # will flip to False if any stream not done

    # 1) Comments stream
    ck_last_after, ck_done = load_checkpoint(conn, day, "comment")
    while not ck_done:
        items, new_last, done = fetch_day_stream("comment", day, ck_last_after)
        if not items and ck_last_after == new_last:
            # likely a transient issue, break to avoid infinite loop; mark incomplete
            logging.warning(f"[{day}] Comment stream yielded 0 new items; leaving as incomplete for retry.")
            complete = False
            break

        for it in items:
            author = it.get("author")
            if author and author not in EXCLUDED_AUTHORS:
                authors.add(author)
            sub = it.get("subreddit")
            if sub:
                subs_seen.add(sub)
            comments_cnt += 1

        ck_last_after = new_last
        ck_done = done
        save_checkpoint(conn, day, "comment", ck_last_after, ck_done)

        # Sanity: if batch == BATCH_SIZE, log that we are paging more
        if len(items) == BATCH_SIZE:
            logging.debug(f"[{day}] Comments: batch full ({BATCH_SIZE}); paging…")

    # 2) Submissions stream
    sk_last_after, sk_done = load_checkpoint(conn, day, "submission")
    while not sk_done:
        items, new_last, done = fetch_day_stream("submission", day, sk_last_after)
        if not items and sk_last_after == new_last:
            logging.warning(f"[{day}] Submission stream yielded 0 new items; leaving as incomplete for retry.")
            complete = False
            break

        for it in items:
            author = it.get("author")
            if author and author not in EXCLUDED_AUTHORS:
                authors.add(author)
            sub = it.get("subreddit")
            if sub:
                subs_seen.add(sub)
            posts_cnt += 1

        sk_last_after = new_last
        sk_done = done
        save_checkpoint(conn, day, "submission", sk_last_after, sk_done)

        if len(items) == BATCH_SIZE:
            logging.debug(f"[{day}] Submissions: batch full ({BATCH_SIZE}); paging…")

    # Persist subreddits seen for diagnostics
    add_subreddits(conn, day, subs_seen)

    # Daily summary upsert
    upsert_daily(conn, day,
                 dau=len(authors),
                 posts=posts_cnt,
                 comments=comments_cnt,
                 subreddits=len(subs_seen),
                 complete=complete)

    # Final sanity checks/logs
    if len(authors) == 0 and (posts_cnt > 0 or comments_cnt > 0):
        logging.warning(f"[{day}] ZERO authors but {posts_cnt}+{comments_cnt} activities – check EXCLUDED_AUTHORS logic or data fields.")
    if posts_cnt == 0 and comments_cnt == 0:
        logging.warning(f"[{day}] No posts/comments collected; Pushshift may have gaps or API hiccups. Will rely on retries on next run.")

    logging.info(f"✅ {day}: DAU′(contributors)={len(authors):,} | posts={posts_cnt:,} | comments={comments_cnt:,} | subs={len(subs_seen):,} | complete={complete}")


# ---------- Monthly Aggregation ----------
def month_range(start_d: date, end_d: date) -> List[Tuple[int,int]]:
    """Return list of (year, month) from start to end inclusive."""
    months = []
    y, m = start_d.year, start_d.month
    last = (end_d.year, end_d.month)
    while (y, m) <= last:
        months.append((y, m))
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return months


def days_in_month(y: int, m: int) -> int:
    if m == 12:
        nxt = date(y+1, 1, 1)
    else:
        nxt = date(y, m+1, 1)
    first = date(y, m, 1)
    return (nxt - first).days


def aggregate_monthly(conn: sqlite3.Connection,
                      start_d: date, end_d: date) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Returns:
      monthly_dau: map 'YYYY-MM' -> avg contributor DAU (float)
      monthly_growth: map 'YYYY-MM' -> MoM growth in %
    """
    cur = conn.cursor()
    monthly_dau: Dict[str, float] = {}
    monthly_growth: Dict[str, float] = {}

    months = month_range(start_d, end_d)
    prev_val = None

    for (y, m) in months:
        month_key = f"{y:04d}-{m:02d}"
        start_day = date(y, m, 1)
        end_day = date(y, m, days_in_month(y, m))
        if end_day < start_d or start_day > end_d:
            continue
        q_start = max(start_day, start_d).isoformat()
        q_end = min(end_day, end_d).isoformat()

        cur.execute("""
            SELECT day, dau_contrib, complete FROM daily_dau
             WHERE day BETWEEN ? AND ?
             ORDER BY day ASC
        """, (q_start, q_end))
        rows = cur.fetchall()

        if not rows:
            logging.warning(f"[{month_key}] No daily data stored.")
            continue

        # Use only days we at least attempted; we can choose to exclude incomplete, or include with caution.
        daily_vals = [r[1] for r in rows if r[1] is not None]
        if not daily_vals:
            logging.warning(f"[{month_key}] No contributor DAU values in rows.")
            continue

        avg_contrib_dau = sum(daily_vals) / len(daily_vals)
        monthly_dau[month_key] = avg_contrib_dau

        if prev_val is None:
            monthly_growth[month_key] = float("nan")
        else:
            monthly_growth[month_key] = 100.0 * (avg_contrib_dau - prev_val) / prev_val if prev_val > 0 else float("nan")

        prev_val = avg_contrib_dau

    return monthly_dau, monthly_growth


def render_month_table(monthly_dau: Dict[str, float], monthly_growth: Dict[str, float]) -> str:
    """Render a markdown-like table with columns=months, rows=DAU and MoM%."""
    months_sorted = sorted(monthly_dau.keys())
    if not months_sorted:
        return "No monthly data to display."

    # Header
    header = "| Metric | " + " | ".join([datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in months_sorted]) + " |"
    sep = "|" + "--------|" * (len(months_sorted) + 1)

    # Row 1: Estimated DAU (contributors), millions
    row1_vals = []
    for m in months_sorted:
        val = monthly_dau[m] / 1e6
        row1_vals.append(f"{val:.1f}M")
    row1 = "| Estimated DAU (contributors) | " + " | ".join(row1_vals) + " |"

    # Row 2: MoM Growth
    row2_vals = []
    for i, m in enumerate(months_sorted):
        g = monthly_growth.get(m, float("nan"))
        if i == 0 or math.isnan(g):
            row2_vals.append("–")
        else:
            row2_vals.append(f"{g:+.1f}%")
    row2 = "| MoM Growth | " + " | ".join(row2_vals) + " |"

    return "\n".join([header, sep, row1, row2])


def list_subreddits_checked(conn: sqlite3.Connection,
                            start_d: date, end_d: date) -> List[str]:
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT subreddit FROM subreddits_seen
         WHERE day BETWEEN ? AND ?
         ORDER BY subreddit COLLATE NOCASE
    """, (start_d.isoformat(), end_d.isoformat()))
    return [r[0] for r in cur.fetchall()]


# ---------- Representativeness ----------
def estimate_total_dau_from_contributors(avg_contrib_dau: float,
                                         contributor_fraction: float = CONTRIBUTOR_FRACTION) -> float:
    """Extrapolate total DAU given contributor DAU and assumed fraction."""
    if contributor_fraction <= 0:
        return float("nan")
    return avg_contrib_dau / contributor_fraction


# ---------- Orchestration ----------
def daterange(start_date: date, end_date: date):
    day = start_date
    while day <= end_date:
        yield day
        day += timedelta(days=1)


def run_pipeline(start: date, end: date, max_days: Optional[int] = None) -> None:
    """
    Incremental run:
      - For each day in [start, end], fetch comments+submissions with checkpoints
      - Aggregate monthly + print table
      - Save subreddits checked
    max_days: process at most N days from the start for incremental runs (optional)
    """
    conn = connect_db(DB_PATH)
    init_db(conn)

    logging.info(f"=== Reddit DAU Pushshift Run: {start} → {end} ===")

    processed = 0
    for d in daterange(start, end):
        process_day(conn, d)
        processed += 1
        if max_days is not None and processed >= max_days:
            logging.info(f"Reached max_days={max_days}; stopping day loop early for incremental run.")
            break

    # Monthly aggregation
    monthly_dau, monthly_growth = aggregate_monthly(conn, start, end)

    # Print table
    print("\n==== Monthly Contributor DAU (Pushshift, site-wide) ====\n")
    print(render_month_table(monthly_dau, monthly_growth))

    # Representativeness: print extrapolated total DAU per month (optional)
    if monthly_dau:
        months_sorted = sorted(monthly_dau.keys())
        print("\n(Info) Representativeness / Extrapolated total DAU (assuming contributors ~"
              f"{CONTRIBUTOR_FRACTION:.1%} of total):")
        for m in months_sorted:
            total_est = estimate_total_dau_from_contributors(monthly_dau[m], CONTRIBUTOR_FRACTION)
            print(f"  {m}: total DAU ≈ {total_est/1e6:.1f}M (from contributor DAU {monthly_dau[m]/1e6:.1f}M)")

    # Subreddits checked list
    subs = list_subreddits_checked(conn, start, end)
    with open(SUBREDDITS_OUTFILE, "w", encoding="utf-8") as f:
        for s in subs:
            f.write(s + "\n")
    print(f"\nSubreddits checked in period: {len(subs):,} (full list saved to {SUBREDDITS_OUTFILE})")
    if subs:
        print("Sample (first {}):".format(min(PRINT_SUBREDDITS_LIMIT, len(subs))))
        print(", ".join(subs[:PRINT_SUBREDDITS_LIMIT]))

    print("\nLogs:", LOG_PATH)
    conn.close()


# ---------- CLI ----------
def parse_args():
    ap = argparse.ArgumentParser(description="Estimate Reddit monthly DAU using Pushshift")
    ap.add_argument("--start", type=str, default=DEFAULT_START.isoformat(),
                    help="Start date YYYY-MM-DD (default 2024-09-01)")
    ap.add_argument("--end", type=str, default=DEFAULT_END.isoformat(),
                    help="End date YYYY-MM-DD (default 2025-09-30)")
    ap.add_argument("--max-days", type=int, default=None,
                    help="Process at most this many days (incremental run)")
    ap.add_argument("--contrib-frac", type=float, default=CONTRIBUTOR_FRACTION,
                    help="Assumed contributor fraction of total DAU (default 0.06)")
    return ap.parse_args()


def main():
    args = parse_args()
    try:
        global CONTRIBUTOR_FRACTION
        CONTRIBUTOR_FRACTION = max(1e-6, float(args.contrib_frac))

        start = datetime.strptime(args.start, "%Y-%m-%d").date()
        end = datetime.strptime(args.end, "%Y-%m-%d").date()
        if start > end:
            raise ValueError("start date must be <= end date")

        run_pipeline(start, end, max_days=args.max_days)
    except Exception as e:
        logging.exception(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
