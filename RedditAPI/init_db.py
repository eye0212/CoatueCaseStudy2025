#!/usr/bin/env python3
"""
Initialize the SQLite database for the Reddit pitch kit.
"""

import sqlite3
import os
from pathlib import Path

def init_database():
    """Initialize the SQLite database with required tables."""
    
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    db_path = "data/reddit_pitch.sqlite"
    
    # Create database connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    tables = [
        """CREATE TABLE IF NOT EXISTS subreddit_snapshot (
            date TEXT,
            name TEXT,
            subscribers INTEGER,
            active_user_count INTEGER,
            over18 INTEGER,
            PRIMARY KEY (date, name)
        )""",
        
        """CREATE TABLE IF NOT EXISTS comment_velocity (
            date TEXT,
            sub TEXT,
            median_cpm REAL,
            p90_cpm REAL,
            sample INTEGER,
            PRIMARY KEY (date, sub)
        )""",
        
        """CREATE TABLE IF NOT EXISTS outbound_links (
            date TEXT,
            sub TEXT,
            outbound_share REAL,
            sample INTEGER,
            PRIMARY KEY (date, sub)
        )""",
        
        """CREATE TABLE IF NOT EXISTS keyword_hits (
            date TEXT,
            sub TEXT,
            query TEXT,
            hits INTEGER,
            PRIMARY KEY (date, sub, query)
        )"""
    ]
    
    for table_sql in tables:
        cursor.execute(table_sql)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database initialized at {db_path}")
    print("📊 Created tables:")
    print("   - subreddit_snapshot")
    print("   - comment_velocity") 
    print("   - outbound_links")
    print("   - keyword_hits")

if __name__ == "__main__":
    print("🗄️  Initializing Reddit Pitch Kit Database...")
    print("=" * 50)
    init_database()
