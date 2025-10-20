# Reddit API Setup Guide

## Quick Setup Steps

### 1. Create Reddit App
1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill out:
   - **Name**: "Reddit Pitch Kit" (or any name you prefer)
   - **App type**: Select **"script"**
   - **Description**: "Data collection tool for Reddit engagement analysis"
   - **About URL**: Leave blank
   - **Redirect URI**: Leave blank
4. Click "Create app"
5. **Copy your credentials**:
   - **Client ID**: The string under your app name (looks like `abc123def456`)
   - **Client Secret**: The "secret" field (longer string)

### 2. Create Environment File
Create a file called `.env` in your project root with this content:

```bash
# Reddit API Credentials
REDDIT_CLIENT_ID=your_actual_client_id_here
REDDIT_CLIENT_SECRET=your_actual_client_secret_here

# User agent string (be descriptive and include your Reddit username)
REDDIT_USER_AGENT=reddit-pitch-kit/1.0 by u/your_reddit_username

# Database path (optional, defaults to data/reddit_pitch.sqlite)
DB_PATH=data/reddit_pitch.sqlite
```

**Important**: Replace the placeholder values with your actual credentials and Reddit username.

### 3. Test Your Setup
Run the test script to verify everything works:

```bash
python3 test_reddit_api.py
```

### 4. Run Your First Data Collection
Once the test passes, you can start collecting data:

```bash
# Get popular subreddits snapshot
python3 -c "
import sys
sys.path.append('src')
from reddit_pitch.collector import reddit_client, snapshot_popular_subs
from reddit_pitch.config import Settings, load_config
from reddit_pitch.db import connect, init_db
import sqlite3

settings = Settings()
conn = connect(settings.db_path)
reddit = reddit_client(settings)
cfg = load_config()

# Get top 10 subreddits
rows = []
for sr in reddit.subreddits.popular(limit=10):
    about = sr._fetch()
    rows.append({
        'name': sr.display_name,
        'subscribers': getattr(about, 'subscribers', None),
        'active_user_count': getattr(about, 'active_user_count', None),
        'over18': int(bool(sr.over18)),
    })
    print(f'r/{sr.display_name}: {getattr(about, "subscribers", 0):,} subscribers')

print(f'\\n✅ Successfully collected data for {len(rows)} subreddits!')
"
```

## What This Tool Does

This Reddit pitch kit helps you analyze Reddit engagement for investment research:

- **Subreddit Snapshots**: Track subscriber counts and active users
- **Comment Velocity**: Measure how fast discussions happen
- **Outbound Links**: Track commercial activity (external links)
- **Keyword Analysis**: Search for specific topics across subreddits

## Available Commands

Once set up, you can use these commands:

```bash
# Initialize database (already done)
python3 init_db.py

# Test Reddit API connection
python3 test_reddit_api.py

# Get popular subreddits data
python3 -m reddit_pitch.cli snapshot-subs --limit 100

# Analyze comment velocity
python3 -m reddit_pitch.cli velocity

# Check outbound link ratios
python3 -m reddit_pitch.cli outbound

# Search for keywords
python3 -m reddit_pitch.cli keywords

# Run everything at once
python3 -m reddit_pitch.cli daily-all

# Export data to CSV
python3 -m reddit_pitch.cli export-csv

# Generate charts
python3 -m reddit_pitch.cli plot
```

## Troubleshooting

### Common Issues

1. **"ModuleNotFoundError: No module named 'reddit_pitch'"**
   - Make sure you're in the project root directory
   - Try: `cd /Users/eugeneye/Downloads/reddit-pitch-kit`

2. **"Error connecting to Reddit API"**
   - Check your `.env` file has correct credentials
   - Verify your Reddit app is set up as "script" type
   - Make sure your user agent includes your Reddit username

3. **Architecture errors with numpy/pandas**
   - The test script avoids these issues
   - For full functionality, you may need to reinstall packages with: `pip3 install --force-reinstall numpy pandas`

### Getting Help

- Check the main README.md for more details
- The tool respects Reddit's API limits and terms of service
- Use a descriptive user agent and be gentle with API calls

## Next Steps

1. ✅ Create Reddit app and get credentials
2. ✅ Create `.env` file with your credentials  
3. ✅ Test the connection with `python3 test_reddit_api.py`
4. 🚀 Start collecting data with the commands above!

Happy analyzing! 📊
