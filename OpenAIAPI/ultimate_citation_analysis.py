# ULTIMATE Comprehensive Citation Analysis
# Includes explicit Wikipedia prompts and covers ALL possible contexts

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

# ============ ULTIMATE COMPREHENSIVE CONFIGURATION ============

MODEL = "gpt-4o-mini"
NUM_QUERIES = 80  # Increased for comprehensive coverage
TEMPERATURE = 0.7
DELAY_BETWEEN_CALLS = 1.0
RAW_LOG = "ultimate_citation_log.csv"
SUMMARY_FILE = "ultimate_citation_summary.csv"
CHART_FILE = "ultimate_citation_trends.png"

# Comprehensive domain tracking
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
    "news": ["cnn.com", "bbc.com", "reuters.com", "nytimes.com", "washingtonpost.com", "theguardian.com", "npr.org"],
    "tech_news": ["techcrunch.com", "theverge.com", "arstechnica.com", "wired.com", "engadget.com"],
    "academic": ["scholar.google.com", "pubmed.ncbi.nlm.nih.gov", "arxiv.org", "jstor.org", "researchgate.net"],
    "ecommerce": ["amazon.com", "ebay.com", "etsy.com", "shopify.com"],
    "social": ["facebook.com", "instagram.com", "tiktok.com", "snapchat.com", "pinterest.com"],
    "health": ["webmd.com", "mayoclinic.org", "healthline.com", "medlineplus.gov"],
    "education": ["coursera.org", "udemy.com", "khanacademy.org", "edx.org"],
    "finance": ["bloomberg.com", "cnbc.com", "marketwatch.com", "investopedia.com"],
    "government": [".gov", ".edu"],
    "reference": ["britannica.com", "dictionary.com", "merriam-webster.com"]
}

# ULTIMATE comprehensive prompt templates - including explicit Wikipedia prompts
ULTIMATE_PROMPTS = {
    # Wikipedia-Specific Context (explicit Wikipedia requests)
    "wikipedia_specific": [
        "Tell me about {}. Include Wikipedia links.",
        "What is {}? Provide Wikipedia sources.",
        "Explain {}. Cite Wikipedia articles.",
        "I need information about {}. Include Wikipedia URLs.",
        "What are the key facts about {}? Provide Wikipedia references.",
        "Give me details about {}. Include Wikipedia links.",
        "What should I know about {}? Cite Wikipedia sources.",
        "Explain the history of {}. Include Wikipedia articles."
    ],
    
    # Educational/Factual Context (should naturally trigger Wikipedia)
    "educational": [
        "Explain {}. Provide authoritative sources.",
        "What is the history of {}? Include reliable references.",
        "Tell me about {}. Cite credible sources.",
        "I'm researching {}. What are the most authoritative sources?",
        "What are the key facts about {}? Include references.",
        "Give me an overview of {}. Include sources.",
        "What should I know about {}? Provide references.",
        "Explain the basics of {}. Include sources."
    ],
    
    # Social/Community Context
    "social": [
        "Where can I find discussions about {}?",
        "What do people think about {}? Include community links.",
        "I want to connect with others interested in {}. Where should I look?",
        "What are the best communities for {}?",
        "Where do people share experiences about {}?",
        "What are popular forums for {}?",
        "Where can I find advice about {}?",
        "What communities discuss {}?"
    ],
    
    # Problem-Solving Context
    "problem_solving": [
        "I'm having trouble with {}. Where can I get help?",
        "How do I solve {}? Include helpful resources.",
        "What are the best tutorials for {}?",
        "I need help with {}. What resources should I check?",
        "What are common solutions for {}?",
        "How can I learn {}? Include resources.",
        "What tools can help with {}?",
        "Where can I find solutions for {}?"
    ],
    
    # News/Current Events Context
    "news": [
        "What's happening with {}? Where can I read more?",
        "What are the latest developments in {}?",
        "I want to stay updated on {}. What are good news sources?",
        "What's the current situation with {}?",
        "What are recent news about {}?",
        "What's the latest on {}?",
        "What are current trends in {}?",
        "What's new with {}?"
    ],
    
    # Shopping/Reviews Context
    "shopping": [
        "I'm looking to buy {}. Where can I find reviews?",
        "What are the best places to shop for {}?",
        "I need recommendations for {}. Where should I look?",
        "What are good options for {}?",
        "Where can I find quality {}?",
        "What are the best brands for {}?",
        "Where should I buy {}?",
        "What are good deals on {}?"
    ],
    
    # Learning/Educational Context
    "learning": [
        "I want to learn {}. What are the best resources?",
        "What are good courses for {}?",
        "I'm a beginner in {}. Where should I start?",
        "What are the best learning platforms for {}?",
        "How can I improve my skills in {}?",
        "What resources can help me learn {}?",
        "Where can I study {}?",
        "What are good tutorials for {}?"
    ],
    
    # Health/Medical Context
    "health": [
        "I have questions about {}. Where can I find reliable information?",
        "What should I know about {}? Include medical sources.",
        "I'm concerned about {}. What resources should I check?",
        "What are the symptoms of {}? Include health references.",
        "Where can I learn about {} health?",
        "What are the health effects of {}?",
        "How does {} affect health?",
        "What should I know about {} health?"
    ],
    
    # Finance/Business Context
    "finance": [
        "I want to invest in {}. Where can I learn more?",
        "What should I know about {}? Include financial sources.",
        "How do I get started with {}? Include investment resources.",
        "What are the risks of {}? Include financial references.",
        "Where can I find advice about {}?",
        "What are good strategies for {}?",
        "How can I manage {}?",
        "What are the benefits of {}?"
    ],
    
    # Entertainment Context
    "entertainment": [
        "What are the best {} to watch/read/listen to?",
        "I'm looking for recommendations for {}.",
        "What's popular in {} right now?",
        "What are good {} options?",
        "Where can I find quality {}?",
        "What are the top {}?",
        "What should I try in {}?",
        "What are trending {}?"
    ],
    
    # General Knowledge Context (should trigger Wikipedia)
    "general_knowledge": [
        "What is {}?",
        "Tell me about {}.",
        "Explain {}.",
        "What are the basics of {}?",
        "Give me information about {}.",
        "What should I know about {}?",
        "Describe {}.",
        "What is {} all about?"
    ]
}

# Comprehensive topics covering all contexts
ULTIMATE_TOPICS = {
    "wikipedia_specific": [
        "World War II", "quantum physics", "photosynthesis", "democracy", 
        "periodic table", "evolution", "climate science", "ancient Rome",
        "machine learning", "solar system", "DNA", "gravity", "Einstein",
        "Shakespeare", "Renaissance", "French Revolution", "mitochondria"
    ],
    
    "educational": [
        "World War II", "quantum physics", "photosynthesis", "democracy", 
        "periodic table", "evolution", "climate science", "ancient Rome",
        "machine learning", "solar system", "DNA", "gravity", "Einstein",
        "Shakespeare", "Renaissance", "French Revolution", "mitochondria"
    ],
    
    "social": [
        "relationships", "mental health", "parenting", "dating", "friendship",
        "work-life balance", "social anxiety", "community building", "loneliness",
        "social skills", "networking", "family", "marriage"
    ],
    
    "problem_solving": [
        "programming bugs", "web development", "data analysis", "cybersecurity",
        "database design", "API integration", "debugging", "system administration",
        "Python programming", "JavaScript", "SQL", "Linux"
    ],
    
    "news": [
        "climate change", "artificial intelligence", "economy", "politics",
        "technology", "healthcare", "education", "international relations",
        "cryptocurrency", "space exploration", "renewable energy", "COVID-19"
    ],
    
    "shopping": [
        "laptops", "smartphones", "home appliances", "books", "clothing",
        "furniture", "cars", "electronics", "cameras", "headphones",
        "watches", "shoes"
    ],
    
    "learning": [
        "programming", "data science", "language learning", "photography",
        "cooking", "music", "writing", "design", "mathematics", "history",
        "science", "art"
    ],
    
    "health": [
        "diabetes", "mental health", "nutrition", "exercise", "sleep",
        "stress management", "meditation", "yoga", "heart disease", "cancer",
        "depression", "anxiety"
    ],
    
    "finance": [
        "investing", "cryptocurrency", "real estate", "retirement planning",
        "stock market", "personal finance", "budgeting", "tax planning",
        "mutual funds", "bonds", "insurance", "mortgages"
    ],
    
    "entertainment": [
        "movies", "TV shows", "books", "music", "video games", "podcasts",
        "streaming", "comics", "anime", "sports", "theater", "concerts"
    ],
    
    "general_knowledge": [
        "World War II", "quantum physics", "photosynthesis", "democracy", 
        "periodic table", "evolution", "climate science", "ancient Rome",
        "machine learning", "solar system", "DNA", "gravity", "Einstein",
        "Shakespeare", "Renaissance", "French Revolution", "mitochondria"
    ]
}

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
                {"role": "system", "content": "You are a helpful assistant that provides useful information and cites relevant sources with full URLs when appropriate. Include Wikipedia when it's a good source for the topic."},
                {"role": "user", "content": prompt}
            ]
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error: {e}")
        return ""

def main():
    print(f"\nRunning ULTIMATE comprehensive citation analysis for {NUM_QUERIES} queries...")
    print("This analysis includes explicit Wikipedia prompts and covers ALL contexts.\n")

    records = []
    total_urls = 0
    domain_counter = Counter()
    context_counter = Counter()
    
    # Ensure we get queries from each context
    queries_per_context = NUM_QUERIES // len(ULTIMATE_PROMPTS)
    remaining_queries = NUM_QUERIES % len(ULTIMATE_PROMPTS)
    
    query_count = 0
    
    for context, prompts in ULTIMATE_PROMPTS.items():
        topics = ULTIMATE_TOPICS[context]
        context_queries = queries_per_context + (1 if remaining_queries > 0 else 0)
        remaining_queries -= 1
        
        print(f"\n--- {context.upper()} CONTEXT ({context_queries} queries) ---")
        
        for i in range(context_queries):
            if query_count >= NUM_QUERIES:
                break
                
            topic = random.choice(topics)
            template = random.choice(prompts)
            prompt = template.format(topic)
            
            context_counter[context] += 1
            
            output = run_prompt(prompt)
            urls = extract_urls(output)
            
            for url in urls:
                domain = detect_domain(url)
                domain_counter[domain] += 1
                total_urls += 1
                records.append({
                    "timestamp": datetime.now().isoformat(),
                    "context": context,
                    "topic": topic,
                    "prompt": prompt,
                    "response_snippet": output[:200].replace("\n", " "),
                    "url": url,
                    "domain_detected": domain
                })
            
            query_count += 1
            print(f"[{query_count}/{NUM_QUERIES}] {context}: '{topic}' -> {len(urls)} URLs")
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

    # Context-specific analysis
    context_analysis = []
    for context in ULTIMATE_PROMPTS.keys():
        context_records = [r for r in records if r["context"] == context]
        context_urls = len(context_records)
        context_domains = Counter([r["domain_detected"] for r in context_records])
        
        top_domain = context_domains.most_common(1)[0] if context_domains else ("none", 0)
        wikipedia_count = context_domains.get("wikipedia", 0)
        wikipedia_pct = (wikipedia_count / context_urls * 100) if context_urls > 0 else 0
        
        context_analysis.append({
            "context": context,
            "total_urls": context_urls,
            "top_domain": top_domain[0],
            "top_domain_count": top_domain[1],
            "top_domain_%": (top_domain[1] / context_urls * 100) if context_urls > 0 else 0,
            "wikipedia_count": wikipedia_count,
            "wikipedia_%": wikipedia_pct
        })

    context_df = pd.DataFrame(context_analysis)
    context_df.to_csv("ultimate_context_analysis.csv", index=False, encoding="utf-8-sig")

    # Chart
    plt.figure(figsize=(16, 12))
    
    # Main chart
    plt.subplot(2, 2, 1)
    plt.bar(summary_df["domain"], summary_df["share_%"], color="skyblue")
    plt.title("Ultimate Citation Analysis - All Domains")
    plt.ylabel("Share (%)")
    plt.xticks(rotation=45, ha="right")
    
    # Context breakdown
    plt.subplot(2, 2, 2)
    context_counts = [context_counter[ctx] for ctx in ULTIMATE_PROMPTS.keys()]
    plt.bar(ULTIMATE_PROMPTS.keys(), context_counts, color="lightcoral")
    plt.title("Queries by Context")
    plt.ylabel("Number of Queries")
    plt.xticks(rotation=45, ha="right")
    
    # Wikipedia analysis
    plt.subplot(2, 2, 3)
    wiki_contexts = [row["wikipedia_%"] for _, row in context_df.iterrows()]
    plt.bar(context_df["context"], wiki_contexts, color="green")
    plt.title("Wikipedia Citations by Context")
    plt.ylabel("Wikipedia %")
    plt.xticks(rotation=45, ha="right")
    
    # Top domains by context
    plt.subplot(2, 2, 4)
    top_domains = [row["top_domain"] for _, row in context_df.iterrows()]
    plt.bar(context_df["context"], top_domains, color="orange")
    plt.title("Top Domain by Context")
    plt.ylabel("Domain")
    plt.xticks(rotation=45, ha="right")
    
    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=300, bbox_inches='tight')
    plt.close()

    # Console summary
    print("\n" + "="*70)
    print("ULTIMATE COMPREHENSIVE ANALYSIS SUMMARY")
    print("="*70)
    print(f"Total queries: {NUM_QUERIES}")
    print(f"Total URLs: {total_urls}")
    print(f"Average URLs per query: {total_urls/NUM_QUERIES:.1f}")
    
    print(f"\nTop domains by citation share:")
    print(summary_df.head(15).to_string(index=False))
    
    print(f"\nContext distribution:")
    for context, count in context_counter.most_common():
        print(f"  {context}: {count} queries")
    
    print(f"\nWikipedia analysis by context:")
    for _, row in context_df.iterrows():
        print(f"  {row['context']}: {row['wikipedia_count']} URLs ({row['wikipedia_%']:.1f}%)")
    
    print(f"\nFiles saved:")
    print(f"  Detailed log: {RAW_LOG}")
    print(f"  Summary: {SUMMARY_FILE}")
    print(f"  Context analysis: ultimate_context_analysis.csv")
    print(f"  Chart: {CHART_FILE}")
    print("="*70)

if __name__ == "__main__":
    main()
