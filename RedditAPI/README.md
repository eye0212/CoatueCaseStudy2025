
# reddit-pitch-kit

A tiny, investor-oriented toolkit to collect engagement and commercial-adjacency signals from Reddit for a $RDDT pitch.

## What it does

- Snapshots **subreddit size & active users** (breadth of attention)  
- Measures **comment velocity** (depth/heat of discussion)  
- Estimates **outbound link share** (commercial adjacency / shoppable moments)  
- Simple **keyword screens** by verticals (e.g., AI PCs, GLP‑1, ETFs)  
- Stores results in **SQLite** and can export to CSVs and **plot** basic charts

## Quick start (Cursor-friendly)

1) **Create an app** at Reddit → User Settings → Developer → create an app (`script` app is fine).  
   Capture `client_id` and `client_secret`. Choose a clear user agent (e.g., `PitchRedditBot/1.0 by u/yourhandle`).

2) **Copy `.env.example` to `.env`** and fill your credentials.
   ```bash
   cp .env.example .env
   ```

3) **Install deps** (Python 3.10+ recommended):
   ```bash
   pip install -r requirements.txt
   ```

4) **Initialize DB** (creates `data/reddit_pitch.sqlite`):
   ```bash
   python -m reddit_pitch.cli init-db
   ```

5) **Run a full daily pull** for the defaults in `config.yaml`:
   ```bash
   python -m reddit_pitch.cli daily-all
   ```

6) **Export CSVs** to `./exports`:
   ```bash
   python -m reddit_pitch.cli export-csv
   ```

7) **Make quick charts** to `./exports/plots`:
   ```bash
   python -m reddit_pitch.cli plot
   ```

## Configuration

- **`config.yaml`**: pick how many popular subreddits to snapshot, which subs to measure velocity/outbound links for, and your keyword themes.
- **`.env`**: put credentials and user agent. Never commit real secrets.

## Commands (CLI)

```bash
python -m reddit_pitch.cli init-db
python -m reddit_pitch.cli snapshot-subs       # top N subreddits: subscribers + active_user_count
python -m reddit_pitch.cli velocity            # comment velocity for targeted subs
python -m reddit_pitch.cli outbound            # outbound link ratio for targeted subs
python -m reddit_pitch.cli keywords            # keyword hits for themes across subs
python -m reddit_pitch.cli daily-all           # run all of the above
python -m reddit_pitch.cli export-csv          # write tables as CSV in ./exports
python -m reddit_pitch.cli plot                # basic matplotlib plots
```

## Data model (SQLite)

Tables:
- `subreddit_snapshot(date, name, subscribers, active_user_count, over18)`
- `comment_velocity(date, sub, median_cpm, p90_cpm, sample)`
- `outbound_links(date, sub, outbound_share, sample)`
- `keyword_hits(date, sub, query, hits)`

## Notes

- **Respect Reddit API limits** and terms. Use a descriptive user agent and be gentle with pacing.
- If you have Ads API access, integrate those stats separately in your own modules.
- This repo does **read-only** public data via OAuth client credentials or PRAW read-only mode.
