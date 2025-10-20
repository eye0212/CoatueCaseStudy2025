import praw
reddit = praw.Reddit(
    client_id="b7mj-WzdiFN_YxV9T5Yqvw",
    client_secret="XglGnNmkaDVVI6nhCTNJcHhWmyQ",
    user_agent="reddit-citation-audit by u/eug0212"
)
print(reddit.subreddit("AskReddit").display_name)
