# Optimized Citation Analysis for Remaining Credits
# Focus on diverse, realistic prompts that reflect actual user behavior

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

# Load API key
load_dotenv("key.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY not found!")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

# ============ OPTIMIZED CONFIGURATION ============

MODEL = "gpt-4o-mini"
NUM_QUERIES = 50  # Reduced to conserve credits
TEMPERATURE = 0.7
DELAY_BETWEEN_CALLS = 1.0  # Increased delay to be respectful
RAW_LOG = "optimized_citation_log.csv"
SUMMARY_FILE = "optimized_citation_summary.csv"
CHART_FILE = "optimized_citation_trends.png"

# Expanded domains to track
DOMAINS = {
    "reddit": ["reddit.com", "redd.it"],
    "wikipedia": ["wikipedia.org", "en.wikipedia.org"],
    "stackoverflow": ["stackoverflow.com"],
    "youtube": ["youtube.com", "youtu.be"],
    "x_twitter": ["twitter.com", "x.com"],
    "quora": ["quora.com"],
    "medium": ["medium.com"],
    "github": ["github.com"],
    "linkedin": ["linkedin.com"],
    "news": ["cnn.com", "bbc.com", "reuters.com", "nytimes.com", "washingtonpost.com", "theguardian.com"],
    "tech_news": ["techcrunch.com", "theverge.com", "arstechnica.com", "wired.com"],
    "academic": ["scholar.google.com", "pubmed.ncbi.nlm.nih.gov", "arxiv.org", "jstor.org"],
    "ecommerce": ["amazon.com", "ebay.com", "etsy.com"],
    "social": ["facebook.com", "instagram.com", "tiktok.com", "snapchat.com"]
}

# Realistic prompt templates that reflect actual user behavior
REALISTIC_PROMPTS = [
    # Casual/Conversational
    "I'm looking for {}. Can you help me find some good resources?",
    "What's the best way to learn about {}?",
    "I need help with {}. Where should I look?",
    "Can you recommend some websites about {}?",
    
    # Research-oriented
    "I'm researching {}. What are the most reliable sources?",
    "I need credible information about {}. What sources should I check?",
    "What are the authoritative sources on {}?",
    
    # Problem-solving
    "I'm having trouble with {}. Where can I get help?",
    "What are the best forums or communities for {}?",
    "I need advice about {}. Where should I ask?",
    
    # News/Current events
    "What's happening with {}? Where can I read more?",
    "I want to stay updated on {}. What are good news sources?",
    "What are the latest developments in {}?",
    
    # Learning/Educational
    "I want to learn {}. What are the best learning resources?",
    "What are good tutorials or courses for {}?",
    "I'm a beginner in {}. Where should I start?",
    
    # Shopping/Reviews
    "I'm looking to buy {}. Where can I find reviews?",
    "What are the best places to shop for {}?",
    "I need recommendations for {}.",
    
    # Social/Community
    "Where do people discuss {} online?",
    "What are the best communities for {}?",
    "I want to connect with others interested in {}."
]

# Diverse topics that reflect real user interests
TOPICS = [
    # Technology
    "artificial intelligence", "machine learning", "programming", "web development", 
    "cybersecurity", "data science", "cloud computing", "mobile apps",
    
    # Health & Wellness
    "mental health", "fitness", "nutrition", "meditation", "yoga", 
    "weight loss", "sleep", "stress management",
    
    # Finance & Business
    "investing", "cryptocurrency", "real estate", "entrepreneurship", 
    "personal finance", "stock market", "business strategy",
    
    # Education & Learning
    "online learning", "language learning", "college", "career advice",
    "skill development", "certification", "online courses",
    
    # Lifestyle & Hobbies
    "cooking", "travel", "photography", "music", "gaming", "reading",
    "gardening", "crafts", "fashion", "home improvement",
    
    # News & Current Events
    "climate change", "politics", "technology news", "world events",
    "economy", "healthcare", "education policy",
    
    # Relationships & Social
    "dating", "relationships", "parenting", "family", "friendship",
    "social skills", "communication", "marriage",
    
    # Entertainment
    "movies", "TV shows", "books", "music", "video games", "sports",
    "streaming", "podcasts", "comics", "anime"
]

def extract_urls(text):
    """Extract URLs from text."""
    return re.findall(r'https?://[^\s)>\]]+', text)

def detect_domain(url):
    """Detect which tracked domain a URL belongs to."""
    url_lower = url.lower()
    for label, patterns in DOMAINS.items():
        if any(pattern.lower() in url_lower for pattern in patterns):
            return label
    return "other"

def run_prompt(prompt):
    """Query OpenAI model and return text output."""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides useful information and cites relevant sources with full URLs when appropriate."},
                {"role": "user", "content": prompt}
            ]
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error: {e}")
        return ""

def main():
    print(f"\nRunning optimized citation analysis for {NUM_QUERIES} realistic prompts...\n")
    print("This analysis focuses on diverse, realistic prompts that reflect actual user behavior.\n")

    records = []
    total_urls = 0
    domain_counter = Counter()
    prompt_types = Counter()

    for i in range(NUM_QUERIES):
        topic = random.choice(TOPICS)
        template = random.choice(REALISTIC_PROMPTS)
        prompt = template.format(topic)
        
        # Track prompt types
        prompt_type = template.split('{}')[0].strip()
        prompt_types[prompt_type] += 1

        output = run_prompt(prompt)
        urls = extract_urls(output)

        for url in urls:
            domain = detect_domain(url)
            domain_counter[domain] += 1
            total_urls += 1
            records.append({
                "timestamp": datetime.now().isoformat(),
                "prompt_type": prompt_type,
                "topic": topic,
                "prompt": prompt,
                "response_snippet": output[:200].replace("\n", " "),
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
        count = domain_counter[d]
        share_pct = (count / total_urls * 100) if total_urls else 0
        summary_data.append({"domain": d, "count": count, "share_%": share_pct})
    
    summary_data.append({
        "domain": "other", 
        "count": domain_counter["other"], 
        "share_%": (domain_counter["other"] / total_urls * 100) if total_urls else 0
    })

    summary_df = pd.DataFrame(summary_data).sort_values("count", ascending=False)
    summary_df.to_csv(SUMMARY_FILE, index=False, encoding="utf-8-sig")

    # Chart
    plt.figure(figsize=(12, 8))
    plt.bar(summary_df["domain"], summary_df["share_%"], color="skyblue")
    plt.title("Citation Share by Domain (Optimized Analysis)")
    plt.ylabel("Share (%)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=300, bbox_inches='tight')
    plt.close()

    # Console summary
    print("\n========== OPTIMIZED ANALYSIS SUMMARY ==========")
    print(f"Total queries: {NUM_QUERIES}")
    print(f"Total URLs: {total_urls}")
    print(f"Average URLs per query: {total_urls/NUM_QUERIES:.1f}")
    print("\nTop domains by citation share:")
    print(summary_df.head(10).to_string(index=False))
    
    print(f"\nPrompt type distribution:")
    for prompt_type, count in prompt_types.most_common(5):
        print(f"  {prompt_type}: {count}")
    
    print(f"\nFiles saved:")
    print(f"  Detailed log: {RAW_LOG}")
    print(f"  Summary: {SUMMARY_FILE}")
    print(f"  Chart: {CHART_FILE}")
    print("===============================================\n")

if __name__ == "__main__":
    main()
