#!/usr/bin/env python3
"""
South Korea AI Development Analysis
Deep dive into how people are discussing AI developments in infrastructure and general AI topics in South Korea.
"""

import sys
import os
import time
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional
import re

sys.path.append('src')
from reddit_pitch.collector import reddit_client
from reddit_pitch.config import Settings, load_config
from reddit_pitch.db import connect

class KoreaAIAnalysis:
    def __init__(self):
        self.settings = Settings()
        self.reddit = reddit_client(self.settings)
        self.conn = connect(self.settings.db_path)
        
        # AI-related keywords for South Korea
        self.ai_keywords = {
            'infrastructure': [
                'AI infrastructure', 'AI data center', 'AI server', 'AI chip', 'AI hardware',
                'AI computing', 'AI cloud', 'AI network', 'AI platform', 'AI system',
                'AI architecture', 'AI framework', 'AI deployment', 'AI scaling'
            ],
            'general_ai': [
                'artificial intelligence', 'machine learning', 'deep learning', 'neural network',
                'AI model', 'AI algorithm', 'AI technology', 'AI development', 'AI research',
                'AI innovation', 'AI application', 'AI solution', 'AI service'
            ],
            'korea_specific': [
                'Korea AI', 'South Korea AI', 'Korean AI', 'K-ai', 'K-AI',
                'Samsung AI', 'LG AI', 'SK AI', 'Naver AI', 'Kakao AI',
                'Korean AI companies', 'Korea AI policy', 'Korea AI strategy'
            ],
            'recent_developments': [
                'ChatGPT Korea', 'AI regulation Korea', 'AI ethics Korea', 'AI governance Korea',
                'AI investment Korea', 'AI startup Korea', 'AI talent Korea', 'AI education Korea',
                'AI healthcare Korea', 'AI finance Korea', 'AI manufacturing Korea'
            ]
        }
        
        # South Korea related subreddits and keywords
        self.korea_subreddits = [
            'korea', 'SouthKorea', 'korean', 'Seoul', 'kpop', 'koreanvariety',
            'koreanfood', 'koreanmusic', 'koreanbeauty', 'koreandrama', 'koreanmovies',
            'koreanlearning', 'koreanlanguage', 'koreanculture', 'koreanhistory'
        ]
        
        # Initialize database
        self._init_analysis_tables()
    
    def _init_analysis_tables(self):
        """Initialize database tables for Korea AI analysis."""
        cursor = self.conn.cursor()
        
        # AI discussions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS korea_ai_discussions (
                id TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                author TEXT,
                subreddit TEXT,
                url TEXT,
                score INTEGER,
                num_comments INTEGER,
                created_utc INTEGER,
                date TEXT,
                ai_category TEXT,
                sentiment_score REAL,
                keywords TEXT,
                is_korea_related BOOLEAN,
                collected_at TEXT
            )
        """)
        
        # Keyword analysis table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keyword_analysis (
                id INTEGER PRIMARY KEY,
                keyword TEXT,
                category TEXT,
                frequency INTEGER,
                subreddit TEXT,
                date TEXT,
                sentiment REAL,
                created_at TEXT
            )
        """)
        
        # Sentiment analysis table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_analysis (
                id INTEGER PRIMARY KEY,
                subreddit TEXT,
                date TEXT,
                positive_count INTEGER,
                negative_count INTEGER,
                neutral_count INTEGER,
                total_discussions INTEGER,
                avg_sentiment REAL,
                created_at TEXT
            )
        """)
        
        self.conn.commit()
    
    def search_ai_discussions(self, days_back=30):
        """Search for AI-related discussions in Korea-focused subreddits."""
        print("🔍 Searching for AI Discussions in South Korea...")
        print("=" * 60)
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)
        
        all_discussions = []
        
        # Search in Korea-related subreddits
        for subreddit_name in self.korea_subreddits:
            print(f"📊 Searching r/{subreddit_name}...")
            
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Search for AI-related posts
                for category, keywords in self.ai_keywords.items():
                    for keyword in keywords:
                        discussions = self._search_keyword_in_subreddit(
                            subreddit, keyword, category, start_date, end_date
                        )
                        all_discussions.extend(discussions)
                        time.sleep(0.2)  # Be respectful to API
                
            except Exception as e:
                print(f"  ⚠️  Error searching r/{subreddit_name}: {e}")
                continue
        
        # Also search in general AI/tech subreddits for Korea mentions
        general_subreddits = ['artificial', 'MachineLearning', 'technology', 'programming', 'futurology']
        for subreddit_name in general_subreddits:
            print(f"📊 Searching r/{subreddit_name} for Korea AI mentions...")
            
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Search for Korea + AI combinations
                korea_ai_queries = [
                    'Korea AI', 'South Korea AI', 'Korean AI', 'K-ai', 'K-AI',
                    'Samsung AI', 'LG AI', 'SK AI', 'Naver AI', 'Kakao AI'
                ]
                
                for query in korea_ai_queries:
                    discussions = self._search_keyword_in_subreddit(
                        subreddit, query, 'korea_specific', start_date, end_date
                    )
                    all_discussions.extend(discussions)
                    time.sleep(0.2)
                
            except Exception as e:
                print(f"  ⚠️  Error searching r/{subreddit_name}: {e}")
                continue
        
        # Deduplicate and store
        unique_discussions = self._deduplicate_discussions(all_discussions)
        self._store_discussions(unique_discussions)
        
        print(f"\n✅ Found {len(unique_discussions)} unique AI discussions")
        return unique_discussions
    
    def _search_keyword_in_subreddit(self, subreddit, keyword, category, start_date, end_date):
        """Search for a specific keyword in a subreddit."""
        discussions = []
        
        try:
            # Search for posts containing the keyword
            for post in subreddit.search(keyword, sort='new', limit=50):
                post_date = datetime.fromtimestamp(post.created_utc, timezone.utc)
                
                if start_date <= post_date <= end_date:
                    # Check if post is Korea-related
                    is_korea_related = self._is_korea_related(post.title + ' ' + getattr(post, 'selftext', ''))
                    
                    discussion = {
                        'id': post.id,
                        'title': post.title,
                        'content': getattr(post, 'selftext', ''),
                        'author': str(post.author) if post.author else '[deleted]',
                        'subreddit': subreddit.display_name,
                        'url': f"https://reddit.com{post.permalink}",
                        'score': getattr(post, 'score', 0),
                        'num_comments': getattr(post, 'num_comments', 0),
                        'created_utc': post.created_utc,
                        'date': post_date.date().isoformat(),
                        'ai_category': category,
                        'sentiment_score': self._calculate_sentiment(post.title + ' ' + getattr(post, 'selftext', '')),
                        'keywords': keyword,
                        'is_korea_related': is_korea_related,
                        'collected_at': datetime.now().isoformat()
                    }
                    discussions.append(discussion)
        
        except Exception as e:
            print(f"    ⚠️  Error searching for '{keyword}': {e}")
        
        return discussions
    
    def _is_korea_related(self, text):
        """Check if text is related to South Korea."""
        korea_indicators = [
            'korea', 'korean', 'south korea', 'seoul', 'busan', 'incheon',
            'samsung', 'lg', 'sk', 'naver', 'kakao', 'hyundai', 'kia',
            'k-pop', 'k-drama', 'korean', 'k-ai', 'k-ai'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in korea_indicators)
    
    def _calculate_sentiment(self, text):
        """Simple sentiment analysis (basic implementation)."""
        positive_words = [
            'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'positive', 'success', 'achievement', 'progress', 'innovation',
            'breakthrough', 'advancement', 'improvement', 'benefit'
        ]
        
        negative_words = [
            'bad', 'terrible', 'awful', 'horrible', 'negative', 'failure',
            'problem', 'issue', 'concern', 'worry', 'risk', 'threat',
            'challenge', 'difficulty', 'obstacle', 'setback'
        ]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count + negative_count == 0:
            return 0.0
        
        return (positive_count - negative_count) / (positive_count + negative_count)
    
    def _deduplicate_discussions(self, discussions):
        """Remove duplicate discussions."""
        seen = set()
        unique = []
        
        for discussion in discussions:
            if discussion['id'] not in seen:
                seen.add(discussion['id'])
                unique.append(discussion)
        
        return unique
    
    def _store_discussions(self, discussions):
        """Store discussions in database."""
        cursor = self.conn.cursor()
        
        for discussion in discussions:
            cursor.execute("""
                INSERT OR REPLACE INTO korea_ai_discussions 
                (id, title, content, author, subreddit, url, score, num_comments,
                 created_utc, date, ai_category, sentiment_score, keywords,
                 is_korea_related, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                discussion['id'], discussion['title'], discussion['content'],
                discussion['author'], discussion['subreddit'], discussion['url'],
                discussion['score'], discussion['num_comments'], discussion['created_utc'],
                discussion['date'], discussion['ai_category'], discussion['sentiment_score'],
                discussion['keywords'], discussion['is_korea_related'], discussion['collected_at']
            ))
        
        self.conn.commit()
    
    def analyze_ai_trends(self):
        """Analyze AI trends and patterns."""
        print("\n📈 Analyzing AI Trends in South Korea...")
        print("=" * 50)
        
        cursor = self.conn.cursor()
        
        # Get all discussions
        cursor.execute("""
            SELECT ai_category, COUNT(*) as count, AVG(sentiment_score) as avg_sentiment,
                   AVG(score) as avg_score, AVG(num_comments) as avg_comments
            FROM korea_ai_discussions 
            GROUP BY ai_category
            ORDER BY count DESC
        """)
        
        category_stats = cursor.fetchall()
        
        print("📊 AI Category Analysis:")
        for category, count, avg_sentiment, avg_score, avg_comments in category_stats:
            print(f"   {category:20s}: {count:3d} discussions | {avg_sentiment:6.2f} sentiment | {avg_score:6.1f} score | {avg_comments:6.1f} comments")
        
        # Get top keywords
        cursor.execute("""
            SELECT keywords, COUNT(*) as frequency
            FROM korea_ai_discussions 
            GROUP BY keywords
            ORDER BY frequency DESC
            LIMIT 20
        """)
        
        top_keywords = cursor.fetchall()
        
        print(f"\n🔍 Top AI Keywords:")
        for keyword, frequency in top_keywords:
            print(f"   {keyword:30s}: {frequency:3d} mentions")
        
        # Get subreddit analysis
        cursor.execute("""
            SELECT subreddit, COUNT(*) as discussions, AVG(sentiment_score) as avg_sentiment
            FROM korea_ai_discussions 
            GROUP BY subreddit
            ORDER BY discussions DESC
        """)
        
        subreddit_stats = cursor.fetchall()
        
        print(f"\n📱 Subreddit Analysis:")
        for subreddit, discussions, avg_sentiment in subreddit_stats:
            print(f"   r/{subreddit:20s}: {discussions:3d} discussions | {avg_sentiment:6.2f} sentiment")
        
        return {
            'category_stats': category_stats,
            'top_keywords': top_keywords,
            'subreddit_stats': subreddit_stats
        }
    
    def analyze_infrastructure_discussions(self):
        """Deep dive into AI infrastructure discussions."""
        print("\n🏗️  Analyzing AI Infrastructure Discussions...")
        print("=" * 50)
        
        cursor = self.conn.cursor()
        
        # Get infrastructure-specific discussions
        cursor.execute("""
            SELECT title, content, subreddit, score, num_comments, sentiment_score, url
            FROM korea_ai_discussions 
            WHERE ai_category = 'infrastructure' OR keywords LIKE '%infrastructure%'
            ORDER BY score DESC
        """)
        
        infrastructure_discussions = cursor.fetchall()
        
        print(f"📊 Found {len(infrastructure_discussions)} infrastructure discussions")
        
        # Analyze infrastructure topics
        infrastructure_topics = defaultdict(int)
        for discussion in infrastructure_discussions:
            title, content, subreddit, score, num_comments, sentiment, url = discussion
            full_text = (title + ' ' + content).lower()
            
            # Categorize infrastructure topics
            if 'data center' in full_text or 'datacenter' in full_text:
                infrastructure_topics['Data Centers'] += 1
            if 'chip' in full_text or 'semiconductor' in full_text:
                infrastructure_topics['AI Chips/Semiconductors'] += 1
            if 'cloud' in full_text:
                infrastructure_topics['Cloud Computing'] += 1
            if 'server' in full_text:
                infrastructure_topics['AI Servers'] += 1
            if 'network' in full_text or '5g' in full_text:
                infrastructure_topics['Networking/5G'] += 1
            if 'samsung' in full_text:
                infrastructure_topics['Samsung'] += 1
            if 'lg' in full_text:
                infrastructure_topics['LG'] += 1
            if 'sk' in full_text:
                infrastructure_topics['SK Group'] += 1
        
        print(f"\n🏗️  Infrastructure Topic Breakdown:")
        for topic, count in sorted(infrastructure_topics.items(), key=lambda x: x[1], reverse=True):
            print(f"   {topic:25s}: {count:3d} mentions")
        
        # Show top infrastructure discussions
        print(f"\n🔥 Top Infrastructure Discussions:")
        for i, discussion in enumerate(infrastructure_discussions[:10], 1):
            title, content, subreddit, score, num_comments, sentiment, url = discussion
            print(f"   {i:2d}. r/{subreddit}: {title[:60]}...")
            print(f"       Score: {score}, Comments: {num_comments}, Sentiment: {sentiment:.2f}")
            print(f"       URL: {url}")
            print()
        
        return infrastructure_discussions
    
    def analyze_general_ai_sentiment(self):
        """Analyze general AI sentiment in Korea discussions."""
        print("\n💭 Analyzing General AI Sentiment...")
        print("=" * 50)
        
        cursor = self.conn.cursor()
        
        # Get sentiment distribution
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN sentiment_score > 0.1 THEN 'Positive'
                    WHEN sentiment_score < -0.1 THEN 'Negative'
                    ELSE 'Neutral'
                END as sentiment_category,
                COUNT(*) as count,
                AVG(score) as avg_score,
                AVG(num_comments) as avg_comments
            FROM korea_ai_discussions 
            GROUP BY sentiment_category
            ORDER BY count DESC
        """)
        
        sentiment_stats = cursor.fetchall()
        
        print("📊 Sentiment Distribution:")
        for category, count, avg_score, avg_comments in sentiment_stats:
            print(f"   {category:10s}: {count:3d} discussions | {avg_score:6.1f} avg score | {avg_comments:6.1f} avg comments")
        
        # Get recent trends
        cursor.execute("""
            SELECT date, COUNT(*) as discussions, AVG(sentiment_score) as avg_sentiment
            FROM korea_ai_discussions 
            GROUP BY date
            ORDER BY date DESC
            LIMIT 10
        """)
        
        recent_trends = cursor.fetchall()
        
        print(f"\n📈 Recent Trends (Last 10 days):")
        for date, discussions, avg_sentiment in recent_trends:
            sentiment_emoji = "😊" if avg_sentiment > 0.1 else "😐" if avg_sentiment > -0.1 else "😞"
            print(f"   {date}: {discussions:2d} discussions | {avg_sentiment:6.2f} sentiment {sentiment_emoji}")
        
        return sentiment_stats, recent_trends
    
    def generate_comprehensive_report(self):
        """Generate comprehensive Korea AI analysis report."""
        print("\n📊 Generating Comprehensive Korea AI Report...")
        print("=" * 60)
        
        # Search for discussions
        discussions = self.search_ai_discussions(days_back=30)
        
        # Analyze trends
        trends = self.analyze_ai_trends()
        
        # Analyze infrastructure
        infrastructure = self.analyze_infrastructure_discussions()
        
        # Analyze sentiment
        sentiment_stats, recent_trends = self.analyze_general_ai_sentiment()
        
        # Generate final report
        report = {
            'generated_at': datetime.now().isoformat(),
            'analysis_period': '30 days',
            'total_discussions': len(discussions),
            'trends_analysis': trends,
            'infrastructure_analysis': {
                'total_discussions': len(infrastructure),
                'top_topics': dict(trends['category_stats'])
            },
            'sentiment_analysis': {
                'distribution': sentiment_stats,
                'recent_trends': recent_trends
            },
            'key_insights': self._generate_insights(trends, infrastructure, sentiment_stats)
        }
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"korea_ai_analysis_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n✅ Comprehensive Report Generated!")
        print(f"📊 Total discussions analyzed: {len(discussions)}")
        print(f"🏗️  Infrastructure discussions: {len(infrastructure)}")
        print(f"💾 Report saved to: {filename}")
        
        return report
    
    def _generate_insights(self, trends, infrastructure, sentiment_stats):
        """Generate key insights from the analysis."""
        insights = []
        
        # Total discussions insight
        total_discussions = sum(count for _, count, _, _, _ in trends['category_stats'])
        insights.append(f"Found {total_discussions} AI-related discussions in Korea-focused communities")
        
        # Top category insight
        if trends['category_stats']:
            top_category, top_count, _, _, _ = trends['category_stats'][0]
            insights.append(f"Most discussed category: {top_category} ({top_count} discussions)")
        
        # Infrastructure insight
        if infrastructure:
            insights.append(f"AI infrastructure is actively discussed with {len(infrastructure)} specific discussions")
        
        # Sentiment insight
        if sentiment_stats:
            positive_count = sum(count for category, count, _, _ in sentiment_stats if category == 'Positive')
            total_sentiment = sum(count for _, count, _, _ in sentiment_stats)
            if total_sentiment > 0:
                positive_ratio = positive_count / total_sentiment
                insights.append(f"Sentiment analysis shows {positive_ratio:.1%} positive discussions")
        
        return insights

def main():
    """Main function to run Korea AI analysis."""
    analyzer = KoreaAIAnalysis()
    
    try:
        report = analyzer.generate_comprehensive_report()
        
        print(f"\n🎉 Korea AI Analysis Complete!")
        print(f"📊 Total discussions: {report['total_discussions']}")
        print(f"🏗️  Infrastructure focus: {report['infrastructure_analysis']['total_discussions']} discussions")
        
        print(f"\n💡 Key Insights:")
        for insight in report['key_insights']:
            print(f"   • {insight}")
        
        return report
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        return None

if __name__ == "__main__":
    main()
