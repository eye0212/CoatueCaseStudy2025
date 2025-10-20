#!/usr/bin/env python3
"""
Reddit DAU/WAU/MAU Tracker (Full Sampling)
------------------------------------------
Collects unique daily Reddit authors (DAU′) across ALL tracked subreddits.
Fully compatible with complete_dau_system.py.
"""

import sys
import os
import time
import sqlite3
import numpy as np
from datetime import datetime, timezone
from collections import defaultdict
from statistics import mean

sys.path.append('src')
from reddit_pitch.collector import reddit_client
from reddit_pitch.config import Settings, load_config
from reddit_pitch.db import connect


class RedditDAUTracker:
    def __init__(self):
        self.settings = Settings()
        self.reddit = reddit_client(self.settings)
        self.conn = connect(self.settings.db_path)
        self.excluded_authors = {'AutoModerator', '[deleted]', '[removed]', 'None', ''}

        self._init_tables()

        self.reported_metrics = {
            'dau_q4_23': 73.1e6,
            'wau_q4_23': 267.5e6,
            'dau_mau_ratio': 0.15
        }

    # ---------------------------------------------------
    # DB SETUP
    # ---------------------------------------------------
    def _init_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracking_panel (
                subreddit TEXT PRIMARY KEY,
                subscribers INTEGER,
                added_date TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_unique_authors (
                date TEXT PRIMARY KEY,
                dau_prime INTEGER,
                total_posts INTEGER,
                total_comments INTEGER,
                total_activities INTEGER,
                unique_subreddits INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calibration_factors (
                id INTEGER PRIMARY KEY,
                period TEXT,
                k_dau REAL,
                k_wau REAL,
                k_mau REAL,
                created_date TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monthly_dau_trends (
                month TEXT PRIMARY KEY,
                dau_prime_avg REAL,
                dau_calibrated_avg REAL,
                dau_growth REAL,
                sample_days INTEGER,
                updated_at TEXT
            )
        """)

        self.conn.commit()

    # ---------------------------------------------------
    # BUILD PANEL
    # ---------------------------------------------------
    def build_tracking_panel(self, top_n=2000):
        print(f"🏗️ Building subreddit tracking panel (top {top_n})...")
        cursor = self.conn.cursor()
        added = 0

        for i, subreddit in enumerate(self.reddit.subreddits.popular(limit=top_n)):
            try:
                about = subreddit._fetch()
                subs = getattr(about, "subscribers", 1)
                cursor.execute("""
                    INSERT OR REPLACE INTO tracking_panel (subreddit, subscribers, added_date, is_active)
                    VALUES (?, ?, ?, 1)
                """, (subreddit.display_name, subs, datetime.now().isoformat()))
                added += 1
                time.sleep(0.05)
            except Exception as e:
                print(f"⚠️ Error fetching r/{subreddit.display_name}: {e}")

        self.conn.commit()
        print(f"✅ Added/updated {added} subreddits in tracking panel.")
        return added

    # ---------------------------------------------------
    # DAILY SNAPSHOT
    # ---------------------------------------------------
    def collect_daily_snapshot(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT subreddit, subscribers FROM tracking_panel WHERE is_active = 1")
        all_subs = cursor.fetchall()

        if not all_subs:
            print("⚠️ No subreddits available.")
            return None

        # Clean invalid subscriber values
        valid_rows = [(s, subs if subs and subs > 0 else 1) for s, subs in all_subs]
        subs, _ = zip(*valid_rows)

        target_date = datetime.utcnow().date()
        unique_authors = set()
        total_posts = total_comments = 0

        print(f"📸 Collecting daily snapshot for {target_date} across {len(subs)} subreddits...")

        for i, sr_name in enumerate(subs):
            try:
                subreddit = self.reddit.subreddit(sr_name)

                for post in subreddit.new(limit=100):
                    post_date = datetime.fromtimestamp(post.created_utc, timezone.utc).date()
                    if post_date == target_date and post.author:
                        author = str(post.author)
                        if author not in self.excluded_authors:
                            unique_authors.add(author)
                            total_posts += 1

                for comment in subreddit.comments(limit=200):
                    c_date = datetime.fromtimestamp(comment.created_utc, timezone.utc).date()
                    if c_date == target_date and comment.author:
                        author = str(comment.author)
                        if author not in self.excluded_authors:
                            unique_authors.add(author)
                            total_comments += 1

                if i % 100 == 0:
                    print(f"   {i}/{len(subs)} subreddits processed...")
                time.sleep(0.05)
            except Exception as e:
                print(f"⚠️ Error collecting r/{sr_name}: {e}")

        dau_prime = len(unique_authors)
        total_activities = total_posts + total_comments

        cursor.execute("""
            INSERT OR REPLACE INTO daily_unique_authors
            (date, dau_prime, total_posts, total_comments, total_activities, unique_subreddits)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (target_date.isoformat(), dau_prime, total_posts, total_comments, total_activities, len(subs)))
        self.conn.commit()

        print(f"✅ {target_date}: DAU′={dau_prime:,} | Posts={total_posts:,} | Comments={total_comments:,}")
        return {'date': target_date, 'unique_authors': dau_prime, 'total_activities': total_activities}

    # ---------------------------------------------------
    # AGGREGATION + REPORT
    # ---------------------------------------------------
    def update_monthly_trends(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT strftime('%Y-%m', date), dau_prime FROM daily_unique_authors ORDER BY date")
        data = cursor.fetchall()
        if not data:
            print("⚠️ No daily data to aggregate.")
            return

        cursor.execute("SELECT k_dau FROM calibration_factors ORDER BY created_date DESC LIMIT 1")
        row = cursor.fetchone()
        k_dau = row[0] if row else 1.0

        monthly = defaultdict(list)
        for m, v in data:
            monthly[m].append(v)

        last_avg = None
        for month, values in monthly.items():
            avg_dau_prime = mean(values)
            avg_dau = avg_dau_prime * k_dau
            growth = 0.0
            if last_avg:
                growth = (avg_dau - last_avg) / last_avg
            cursor.execute("""
                INSERT OR REPLACE INTO monthly_dau_trends
                (month, dau_prime_avg, dau_calibrated_avg, dau_growth, sample_days, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (month, avg_dau_prime, avg_dau, growth, len(values), datetime.now().isoformat()))
            last_avg = avg_dau

        self.conn.commit()
        print("📅 Monthly DAU trend table updated successfully.")

    def generate_monthly_report(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT month, dau_calibrated_avg, dau_growth FROM monthly_dau_trends ORDER BY month")
        rows = cursor.fetchall()
        if not rows:
            print("⚠️ No monthly data found.")
            return

        print("\n📊 Reddit Estimated DAU Over Time (Calibrated)")
        print("=" * 60)
        print(f"{'Month':<10} {'DAU (M)':<12} {'MoM Growth':<12}")
        print("-" * 60)
        for month, dau, growth in rows:
            print(f"{month:<10} {dau/1e6:<12.1f} {growth*100:<12.1f}%")

    # ---------------------------------------------------
    # RUN TRACKER
    # ---------------------------------------------------
    def run_tracker(self):
        print("🚀 Running Reddit DAU Tracker (Full Sampling)")
        print("=" * 60)
        self.collect_daily_snapshot()
        self.update_monthly_trends()
        self.generate_monthly_report()
        print("\n✅ Tracker run complete.")


def main():
    tracker = RedditDAUTracker()
    try:
        tracker.run_tracker()
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
