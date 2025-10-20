#!/usr/bin/env python3
import argparse, os, re, math, time, yaml
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import pandas as pd
from tqdm import tqdm
import praw
import requests



try:
    import praw
except ImportError:
    praw = None

ISO8601 = "%Y-%m-%dT%H:%M:%SZ"

def parse_time(tstr: str) -> datetime:
    now = datetime.now(timezone.utc)
    t = (tstr or "").strip().lower()
    if t == "now": return now
    if t.startswith("now-"):
        m = re.findall(r"now-(\d+)([dh])$", t)
        if m:
            n, unit = m[0]; n = int(n)
            return now - (timedelta(days=n) if unit == "d" else timedelta(hours=n))
        return now
    try:
        return datetime.strptime(tstr, ISO8601).replace(tzinfo=timezone.utc)
    except Exception:
        return now

def tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9']+", (text or "").lower())

def contains_keywords(text: str, keywords: List[str]) -> bool:
    low = (text or "").lower()
    return any(kw in low for kw in keywords)

def wilson_interval(successes: int, n: int, z: float = 1.96):
    if n == 0: return (0.0, 0.0)
    p = successes / n
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    half = z*math.sqrt((p*(1-p) + z**2/(4*n))/n) / denom
    return (max(0.0, center - half), min(1.0, center + half))

def reddit_client(client_id: str, client_secret: str, user_agent: str, username=None, password=None):
    import praw
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        username=username,
        password=password,
        check_for_async=False,
    )
    # Always read-only — Reddit no longer supports unset read_only for app-only clients
    reddit.read_only = True
    return reddit





def choose_subreddits(r, include: List[str], exclude: List[str], limit: int = 200) -> List[str]:
    chosen = []
    seen = set()
    for s in include or []:
        s = s.strip()
        if s and s not in seen and s not in (exclude or []):
            chosen.append(s); seen.add(s)
    try:
        for s in r.subreddits.popular(limit=limit):
            name = s.display_name
            if name not in seen and name not in (exclude or []):
                chosen.append(name); seen.add(name)
    except Exception:
        pass
    return chosen

def stratified_sample(cfg: Dict[str, Any]) -> pd.DataFrame:
    """
    Try Reddit API first; if it fails (401, etc.), use Pushshift public mirror instead.
    """
    try:
        r = reddit_client(
            cfg["client_id"],
            cfg["client_secret"],
            cfg["user_agent"],
            cfg.get("username"),
            cfg.get("password")
        )
        subs = cfg["subreddits_include"]
        target_posts = int(cfg["target_posts"])
        per_sub_cap = int(cfg["per_subreddit_cap"])
        rows = []
        print(f"Sampling up to {target_posts} posts across {len(subs)} subreddits (Reddit API)…")
        for sub in subs:
            for s in r.subreddit(sub).new(limit=per_sub_cap):
                rows.append({
                    "id": s.id,
                    "subreddit": sub,
                    "created_utc": int(getattr(s, "created_utc", 0)),
                    "title": getattr(s, "title", "") or "",
                    "selftext": getattr(s, "selftext", "") or "",
                    "over_18": bool(getattr(s, "over_18", False)),
                })
            time.sleep(0.2)
        if rows:
            return pd.DataFrame(rows).drop_duplicates(subset=["id"])
    except Exception as e:
        print(f"⚠️ Reddit API sampling failed ({e}). Falling back to Pushshift…")

    # --- Pushshift fallback ---
    subs = cfg["subreddits_include"]
    rows = []
    for sub in subs:
        try:
            url = f"https://api.pullpush.io/reddit/search/submission/?subreddit={sub}&size={cfg['per_subreddit_cap']}"
            data = requests.get(url, timeout=30).json().get("data", [])
            for d in data:
                rows.append({
                    "id": d.get("id"),
                    "subreddit": sub,
                    "created_utc": d.get("created_utc", 0),
                    "title": d.get("title", ""),
                    "selftext": d.get("selftext", ""),
                    "over_18": d.get("over_18", False),
                })
            time.sleep(1)
        except Exception as e:
            print(f"Skipping r/{sub}: {e}")
    return pd.DataFrame(rows).drop_duplicates(subset=["id"])


def enrich_with_reddit(cfg: Dict[str, Any], posts_df: pd.DataFrame):
    """
    Since Reddit API blocks app-only enrichment, use Pushshift to fetch comment text instead.
    """
    import requests
    posts_out, comments_out = [], []
    top_comments = int(cfg["top_comments_per_post"])
    for _, row in tqdm(posts_df.iterrows(), total=len(posts_df), desc="Enriching posts/comments"):
        sid = row["id"]
        try:
            # reuse the post data from sampling
            posts_out.append(row.to_dict())

            # Pull top comments via Pushshift
            if top_comments > 0:
                url = f"https://api.pullpush.io/reddit/comment/search/?link_id={sid}&size={top_comments}&sort=desc&sort_type=score"
                data = requests.get(url, timeout=30).json().get("data", [])
                for c in data:
                    comments_out.append({
                        "post_id": sid,
                        "comment_id": c.get("id"),
                        "body": c.get("body", ""),
                        "score": c.get("score", 0),
                        "is_submitter": c.get("is_submitter", False),
                    })
            time.sleep(0.5)
        except Exception as e:
            print(f"Skipping post {sid}: {e}")
            continue
    return pd.DataFrame(posts_out), pd.DataFrame(comments_out)


def profanity_counts(text: str, profane: set):
    toks = tokenize(text)
    if not toks: return 0, 0
    cnt = sum(1 for t in toks if t in profane)
    return cnt, len(toks)

def analyze(cfg: Dict[str, Any], posts: pd.DataFrame, comments: pd.DataFrame):
    profane = set(cfg["profanity_words"])
    post_rows = []
    for _, r in posts.iterrows():
        text = f"{r.get('title','')} \n {r.get('selftext','')}"
        p_bad, p_tot = profanity_counts(text, profane)
        piracy = contains_keywords(text, cfg["piracy_keywords"])
        restricted_kw = contains_keywords(text, cfg["other_restricted_keywords"])
        post_rows.append({
            **r.to_dict(),
            "profane_tokens": p_bad,
            "total_tokens": p_tot,
            "profanity_rate": (p_bad / p_tot) if p_tot > 0 else 0.0,
            "piracy_kw": piracy,
            "restricted_kw": restricted_kw,
        })
    post_df = pd.DataFrame(post_rows)
    comment_rows = []
    for _, r in comments.iterrows():
        p_bad, p_tot = profanity_counts(r.get("body",""), profane)
        comment_rows.append({
            **r.to_dict(),
            "profane_tokens": p_bad,
            "total_tokens": p_tot,
            "profanity_rate": (p_bad / p_tot) if p_tot > 0 else 0.0,
        })
    comment_df = pd.DataFrame(comment_rows)
    pr_thresh = float(cfg["profanity_rate_threshold"])
    def nc_row(r):
        nsfw = bool(r.get("over18_post")) or bool(r.get("over18_subreddit"))
        profanity_bad = (r.get("profanity_rate") or 0.0) >= pr_thresh
        piracy = bool(r.get("piracy_kw"))
        restricted = bool(r.get("restricted_kw"))
        return any([nsfw, profanity_bad, piracy, restricted])
    post_df["not_citable"] = post_df.apply(nc_row, axis=1)
    def summarize_posts(df: pd.DataFrame) -> Dict[str, Any]:
        n = len(df)
        # handle Pushshift (no over18_post/over18_subreddit columns)
        if "over18_post" in df.columns or "over18_subreddit" in df.columns:
            nsfw = df.get("over18_post", False).fillna(False) | df.get("over18_subreddit", False).fillna(False)
            nsfw = nsfw.sum()
        elif "over_18" in df.columns:
            nsfw = df["over_18"].fillna(False).sum()
        else:
            nsfw = 0
        notcit = df["not_citable"].sum()
        prof_mean = df["profanity_rate"].fillna(0.0).mean() if n>0 else 0.0
        from math import isnan
        def wilson(successes, n, z=1.96):
            if n == 0: return (0.0, 0.0)
            p = successes / n
            denom = 1 + z**2/n
            center = (p + z**2/(2*n)) / denom
            half = z*((p*(1-p) + z**2/(4*n))/n)**0.5 / denom
            return (max(0.0, center - half), min(1.0, center + half))
        nsfw_ci = wilson(nsfw, n)
        notcit_ci = wilson(notcit, n)
        return {
            "n_posts": n,
            "pct_nsfw": nsfw/n if n>0 else 0.0,
            "pct_nsfw_low": nsfw_ci[0],
            "pct_nsfw_high": nsfw_ci[1],
            "pct_not_citable": notcit/n if n>0 else 0.0,
            "pct_not_citable_low": notcit_ci[0],
            "pct_not_citable_high": notcit_ci[1],
            "mean_profanity_rate": prof_mean,
        }
    sub_groups = []
    for sub, g in post_df.groupby("subreddit"):
        s = summarize_posts(g); s["subreddit"] = sub; sub_groups.append(s)
    summary_sub = pd.DataFrame(sub_groups).sort_values("n_posts", ascending=False)
    summary_platform = pd.DataFrame([summarize_posts(post_df)])
    return post_df, comment_df, summary_sub, summary_platform

def main():
    ap = argparse.ArgumentParser(description="Reddit Citation Audit (Reddit API only)")
    ap.add_argument("--config", required=True, help="Path to config.yaml")
    args = ap.parse_args()
    with open(args.config, "r") as f:
        y = yaml.safe_load(f)
    cfg = {
        "client_id": y["reddit"]["client_id"],
        "client_secret": y["reddit"]["client_secret"],
        "user_agent": y["reddit"]["user_agent"],
        "start": parse_time(y["sampling"]["start"]),
        "end": parse_time(y["sampling"]["end"]),
        "target_posts": y["sampling"]["target_posts"],
        "per_subreddit_cap": y["sampling"]["per_subreddit_cap"],
        "top_comments_per_post": y["sampling"]["top_comments_per_post"],
        "subreddits_include": y.get("subreddits", {}).get("include", []) or [],
        "subreddits_exclude": y.get("subreddits", {}).get("exclude", []) or [],
        "profanity_words": [w.lower() for w in y["filters"]["profanity_words"]],
        "piracy_keywords": [w.lower() for w in y["filters"]["piracy_keywords"]],
        "other_restricted_keywords": [w.lower() for w in y["filters"]["other_restricted_keywords"]],
        "profanity_rate_threshold": y["thresholds"]["profanity_rate_threshold"],
        "out_dir": y["outputs"]["out_dir"],
        "write_post_dump": y["outputs"]["write_post_dump"],
        "write_comment_dump": y["outputs"]["write_comment_dump"],
    }
    os.makedirs(cfg["out_dir"], exist_ok=True)
    print("Sampling recent posts (Reddit API)…")
    sampled = stratified_sample(cfg)
    print("Enriching posts & fetching comments…")
    posts, comments = enrich_with_reddit(cfg, sampled)
    if cfg["write_post_dump"]:
        posts.to_csv(os.path.join(cfg["out_dir"], "posts_raw.csv"), index=False)
    if cfg["write_comment_dump"] and not comments.empty:
        comments.to_csv(os.path.join(cfg["out_dir"], "comments_raw.csv"), index=False)
    print("Analyzing…")
    if posts.empty:
        print("No posts fetched. Check Reddit credentials or subreddit access.")
        return
    post_df, comment_df, summary_sub, summary_platform = analyze(cfg, posts, comments)

    post_df.to_csv(os.path.join(cfg["out_dir"], "posts.csv"), index=False)
    comment_df.to_csv(os.path.join(cfg["out_dir"], "comments.csv"), index=False)
    summary_sub.to_csv(os.path.join(cfg["out_dir"], "summary_subreddit.csv"), index=False)
    summary_platform.to_csv(os.path.join(cfg["out_dir"], "summary_platform.csv"), index=False)
    print("\n=== Platform Summary ===")
    print(summary_platform.to_string(index=False))
    print("\nTop 20 subreddits by sample size:")
    print(summary_sub.head(20).to_string(index=False))

if __name__ == "__main__":
    main()