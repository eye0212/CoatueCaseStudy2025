# llm_citation_tracker.py
# Purpose: Estimate how often OpenAI's models cite major domains (Reddit, Wikipedia, etc.) over many prompts.

import re
import csv
import time
import random
import os
from datetime import datetime
from collections import Counter, defaultdict
import pandas as pd
from openai import OpenAI
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# ============ CONFIGURATION ============

# Load API key from key.env file
load_dotenv("key.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o-mini"
NUM_QUERIES = 200                      # Increase to 1000+ for stronger data
TEMPERATURE = 0.7
DELAY_BETWEEN_CALLS = 0.5              # seconds
RAW_LOG = "llm_citation_log.csv"
SUMMARY_FILE = "llm_citation_summary.csv"
CHART_FILE = "llm_citation_trends.png"

# Domains to track
DOMAINS = {
    "reddit": ["reddit.com", "redd.it"],
    "wikipedia": ["wikipedia.org"],
    "stackoverflow": ["stackoverflow.com"],
    "youtube": ["youtube.com", "youtu.be"],
    "x_twitter": ["twitter.com", "x.com"],
    "quora": ["quora.com"],
    "medium": ["medium.com"]
}

# Prompts to diversify responses
TOPICS = [
    "AI research", "politics", "climate change", "machine learning",
    "consumer tech", "cryptocurrency", "fitness", "nutrition",
    "music", "mental health", "education", "programming help",
    "relationships", "travel", "fashion", "sports", "business news",
    "gaming", "movies", "philosophy"
]

TEMPLATES = [
    "Where can I find online discussions about {}? Include URLs.",
    "Summarize what the internet says about {} and cite sources.",
    "List the top forums or sites people use to discuss {}.",
    "Show some web pages or communities that talk about {}.",
    "Find online opinions or advice on {} with links."
]

# ======================================

if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY environment variable not set!")
    print("Please set your OpenAI API key as an environment variable:")
    print("  set OPENAI_API_KEY=your_api_key_here")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

def extract_urls(text):
    """Extract URLs from text."""
    return re.findall(r'https?://[^\s)>\]]+', text)

def detect_domain(url):
    """Detect which tracked domain a URL belongs to."""
    for label, patterns in DOMAINS.items():
        if any(p in url for p in patterns):
            return label
    return "other"

def run_prompt(prompt):
    """Query OpenAI model and return text output."""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            messages=[
                {"role": "system", "content": "You are an assistant that provides helpful summaries and cites online sources with full URLs."},
                {"role": "user", "content": prompt}
            ]
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error: {e}")
        return ""

def main():
    print(f"\nRunning LLM citation tracker for {NUM_QUERIES} prompts...\n")

    records = []
    total_urls = 0
    domain_counter = Counter()

    for i in range(NUM_QUERIES):
        topic = random.choice(TOPICS)
        template = random.choice(TEMPLATES)
        prompt = template.format(topic)

        output = run_prompt(prompt)
        urls = extract_urls(output)

        for url in urls:
            domain = detect_domain(url)
            domain_counter[domain] += 1
            total_urls += 1
            records.append({
                "timestamp": datetime.utcnow().isoformat(),
                "prompt": prompt,
                "response_snippet": output[:180].replace("\n", " "),
                "url": url,
                "domain_detected": domain
            })

        print(f"[{i+1}/{NUM_QUERIES}] '{topic}' -> {len(urls)} URLs ({domain_counter['reddit']}/{total_urls} Reddit so far)")
        time.sleep(DELAY_BETWEEN_CALLS)

    # Save raw log
    pd.DataFrame(records).to_csv(RAW_LOG, index=False, encoding="utf-8-sig")

    # Summary table
    summary_data = []
    for d in DOMAINS.keys():
        summary_data.append({"domain": d, "count": domain_counter[d], "share_%": (domain_counter[d] / total_urls * 100) if total_urls else 0})
    summary_data.append({"domain": "other", "count": domain_counter["other"], "share_%": (domain_counter["other"] / total_urls * 100) if total_urls else 0})

    summary_df = pd.DataFrame(summary_data).sort_values("count", ascending=False)
    summary_df.to_csv(SUMMARY_FILE, index=False, encoding="utf-8-sig")

    # Chart
    plt.figure(figsize=(8,5))
    plt.bar(summary_df["domain"], summary_df["share_%"], color="skyblue")
    plt.title("Share of LLM Citations by Domain")
    plt.ylabel("Share (%)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(CHART_FILE)
    plt.close()

    # Console summary
    print("\n========== SUMMARY ==========")
    print(f"Total queries: {NUM_QUERIES}")
    print(f"Total URLs: {total_urls}")
    print(summary_df.to_string(index=False))
    print(f"\nSaved detailed log -> {RAW_LOG}")
    print(f"Saved summary table -> {SUMMARY_FILE}")
    print(f"Saved chart -> {CHART_FILE}")
    print("=============================\n")

if __name__ == "__main__":
    main()
