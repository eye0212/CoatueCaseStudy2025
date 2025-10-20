#!/usr/bin/env python3
"""
Complete Reddit DAU/WAU/MAU Tracking System (Full Sampling)
------------------------------------------------------------
- Collects DAU′ (unique daily Reddit authors) across ALL tracked subreddits
- Calibrates estimates to Reddit’s reported metrics
- Aggregates into monthly trends
- Prints month-over-month DAU growth
"""

import sys
import os
import time
import json
import sqlite3
import numpy as np
from datetime import datetime, timezone
from collections import defaultdict
from statistics import mean

sys.path.append('src')
from reddit_pitch.collector import reddit_client
from reddit_pitch.config import Settings, load_config
from reddit_pitch.db import connect


class CompleteRedditDAUSystem:
    def __init__(self):
        self.settings = Settings()
        self.reddit = reddit_client(self.settings)
        self.conn = connect(self.settings.db_path)

        # Reddit's reported Q4’23 metrics for calibration
        self.reported_metrics = {
            'dau_q4_23': 73.1e6,
            'wau_q4_23': 267.5e6,
            'dau_mau_ratio': 0.15
        }

        self._init_database_tables()

    # ---------------------------------------------------
    # DATABASE SETUP
    # ---------------------------------------------------
    def _init_database_tables(self):
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
    # DAILY SNAPSHOT
    # ---------------------------------------------------
    def collect_daily_snapshot(self):
        """Collect DAU′ from ALL tracked subreddits."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT subreddit, subscribers FROM tracking_panel WHERE is_active = 1")
        all_subs = cursor.fetchall()

        if not all_subs:
            print("⚠️ No subreddits found in tracking panel.")
            return None

        # Clean invalid subscriber values
        valid_rows = [(s, subs if subs and subs > 0 else 1) for s, subs in all_subs]
        subs, weights = zip(*valid_rows)
        weights = np.array(weights, dtype=float)
        weights /= np.sum(weights)

        target_date = datetime.utcnow().date()
        unique_authors = set()
        total_posts = total_comments = 0

        print(f"📸 Collecting daily snapshot for {target_date} across {len(subs)} subreddits...")

        for i, sr_name in enumerate(subs):
            try:
                subreddit = self.reddit.subreddit(sr_name)

                # Collect posts
                for post in subreddit.new(limit=100):
                    post_date = datetime.fromtimestamp(post.created_utc, timezone.utc).date()
                    if post_date == target_date and post.author:
                        unique_authors.add(str(post.author))
                        total_posts += 1

                # Collect comments
                for comment in subreddit.comments(limit=200):
                    c_date = datetime.fromtimestamp(comment.created_utc, timezone.utc).date()
                    if c_date == target_date and comment.author:
                        unique_authors.add(str(comment.author))
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
    # CALIBRATION
    # ---------------------------------------------------
    def calculate_calibration_factors(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT AVG(dau_prime) FROM daily_unique_authors ORDER BY date DESC LIMIT 30")
        result = cursor.fetchone()
        if not result or not result[0]:
            print("⚠️ Not enough data for calibration.")
            return None

        avg_dau_prime = result[0]
        k_dau = self.reported_metrics['dau_q4_23'] / avg_dau_prime
        k_wau = self.reported_metrics['wau_q4_23'] / (avg_dau_prime * 7)
        k_mau = (self.reported_metrics['dau_q4_23'] / self.reported_metrics['dau_mau_ratio']) / (avg_dau_prime * 30)

        cursor.execute("""
            INSERT INTO calibration_factors (period, k_dau, k_wau, k_mau, created_date)
            VALUES (?, ?, ?, ?, ?)
        """, ('Q4_2023', k_dau, k_wau, k_mau, datetime.now().isoformat()))
        self.conn.commit()

        print(f"🎯 Calibration factors updated → k_DAU={k_dau:.2f}, k_WAU={k_wau:.2f}, k_MAU={k_mau:.2f}")
        return {'k_dau': k_dau, 'k_wau': k_wau, 'k_mau': k_mau}

    # ---------------------------------------------------
    # MONTHLY AGGREGATION
    # ---------------------------------------------------
    def update_monthly_trends(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT strftime('%Y-%m', date), dau_prime FROM daily_unique_authors ORDER BY date")
        data = cursor.fetchall()
        if not data:
            print("⚠️ No daily data to aggregate.")
            return None

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

    # ---------------------------------------------------
    # REPORTING
    # ---------------------------------------------------
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
    # RUN SYSTEM
    # ---------------------------------------------------
    def run_complete_system(self):
        print("🚀 Running Complete Reddit DAU Tracking System (Full Sampling)")
        print("=" * 60)
        self.collect_daily_snapshot()
        self.calculate_calibration_factors()
        self.update_monthly_trends()
        self.generate_monthly_report()
        print("\n✅ Complete DAU system run complete.")


def main():
    system = CompleteRedditDAUSystem()
    try:
        system.run_complete_system()
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
