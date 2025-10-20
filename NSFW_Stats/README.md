# Reddit Citation Audit (Reddit API only, no Pushshift)

This version samples recent posts directly from Reddit's API (PRAW), then estimates a **'not_citable'** rate using NSFW flags, profanity, and restricted keywords.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
# edit config.yaml → add Reddit API client_id, client_secret, user_agent
python reddit_citation_audit.py --config config.yaml
```

Outputs in `./outputs/`:
- `posts.csv`, `comments.csv`
- `summary_subreddit.csv`, `summary_platform.csv`