#!/usr/bin/env python3
"""
Comprehensive Reddit Engagement Analysis Tool
Collects platform-wide engagement statistics and breaks them down by category and engagement type.
"""

import sys
import os
import time
import json
from datetime import datetime, timezone
from collections import defaultdict, Counter
from statistics import mean, median, stdev
import sqlite3

sys.path.append('src')
from reddit_pitch.collector import reddit_client
from reddit_pitch.config import Settings, load_config
from reddit_pitch.db import connect

class RedditEngagementAnalyzer:
    def __init__(self):
        self.settings = Settings()
        self.reddit = reddit_client(self.settings)
        self.conn = connect(self.settings.db_path)
        self.categories = self._define_categories()
        
    def _define_categories(self):
        """Define subreddit categories for analysis."""
        return {
            'Technology': ['technology', 'programming', 'buildapc', 'buildapcsales', 'gadgets', 'apple', 'android', 'windows', 'linux'],
            'Finance': ['personalfinance', 'stocks', 'investing', 'cryptocurrency', 'crypto', 'wallstreetbets', 'securityanalysis'],
            'Gaming': ['gaming', 'pcgaming', 'nintendo', 'playstation', 'xbox', 'steam', 'gamedev', 'indiegaming'],
            'Entertainment': ['movies', 'television', 'music', 'books', 'comics', 'anime', 'netflix', 'disney'],
            'Lifestyle': ['fitness', 'food', 'travel', 'fashion', 'beauty', 'home', 'gardening', 'cooking'],
            'News': ['news', 'worldnews', 'politics', 'europe', 'canada', 'australia', 'unitedkingdom'],
            'Science': ['science', 'askscience', 'explainlikeimfive', 'space', 'biology', 'chemistry', 'physics'],
            'Social': ['askreddit', 'nostupidquestions', 'casualconversation', 'unpopularopinion', 'changemyview'],
            'Hobbies': ['diy', 'woodworking', 'photography', 'art', 'writing', 'crafts', 'boardgames'],
            'Health': ['fitness', 'loseit', 'nutrition', 'mentalhealth', 'depression', 'anxiety', 'meditation']
        }
    
    def collect_platform_statistics(self, sample_size=100):
        """Collect comprehensive platform statistics."""
        print("🚀 Collecting Reddit Platform Statistics...")
        print("=" * 60)
        
        stats = {
            'total_subreddits_analyzed': 0,
            'total_subscribers': 0,
            'total_active_users': 0,
            'categories': defaultdict(lambda: {
                'subreddits': [],
                'total_subscribers': 0,
                'total_active_users': 0,
                'avg_subscribers': 0,
                'avg_active_users': 0,
                'engagement_metrics': {}
            }),
            'engagement_types': {
                'high_engagement': [],
                'medium_engagement': [],
                'low_engagement': []
            },
            'top_subreddits': [],
            'category_breakdown': {}
        }
        
        print(f"📊 Analyzing top {sample_size} subreddits...")
        
        # Collect data from popular subreddits
        subreddit_data = []
        for i, sr in enumerate(self.reddit.subreddits.popular(limit=sample_size)):
            try:
                about = sr._fetch()
                sub_data = {
                    'name': sr.display_name,
                    'subscribers': getattr(about, 'subscribers', 0),
                    'active_user_count': getattr(about, 'active_user_count', 0),
                    'over18': bool(sr.over18),
                    'description': getattr(about, 'description', '')[:100] + '...' if getattr(about, 'description', '') else '',
                    'category': self._categorize_subreddit(sr.display_name)
                }
                subreddit_data.append(sub_data)
                stats['total_subreddits_analyzed'] += 1
                stats['total_subscribers'] += sub_data['subscribers']
                stats['total_active_users'] += sub_data['active_user_count']
                
                # Categorize
                category = sub_data['category']
                stats['categories'][category]['subreddits'].append(sub_data)
                stats['categories'][category]['total_subscribers'] += sub_data['subscribers']
                stats['categories'][category]['total_active_users'] += sub_data['active_user_count']
                
                print(f"  {i+1:3d}. r/{sr.display_name:20s} | {sub_data['subscribers']:8,} subs | {category}")
                time.sleep(0.1)  # Be respectful to Reddit API
                
            except Exception as e:
                print(f"  ⚠️  Error with r/{sr.display_name}: {e}")
                continue
        
        # Calculate category averages
        for category, data in stats['categories'].items():
            if data['subreddits']:
                data['avg_subscribers'] = data['total_subscribers'] / len(data['subreddits'])
                data['avg_active_users'] = data['total_active_users'] / len(data['subreddits'])
        
        # Sort and get top subreddits
        stats['top_subreddits'] = sorted(subreddit_data, key=lambda x: x['subscribers'], reverse=True)[:20]
        
        # Categorize by engagement level
        self._categorize_engagement_levels(stats, subreddit_data)
        
        return stats
    
    def _categorize_subreddit(self, subreddit_name):
        """Categorize a subreddit based on its name."""
        subreddit_lower = subreddit_name.lower()
        
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword.lower() in subreddit_lower:
                    return category
        
        return 'Other'
    
    def _categorize_engagement_levels(self, stats, subreddit_data):
        """Categorize subreddits by engagement level."""
        # Calculate engagement ratio (active users / subscribers)
        engagement_ratios = []
        for sub in subreddit_data:
            if sub['subscribers'] > 0:
                ratio = sub['active_user_count'] / sub['subscribers']
                engagement_ratios.append((sub['name'], ratio, sub['subscribers']))
        
        # Sort by engagement ratio
        engagement_ratios.sort(key=lambda x: x[1], reverse=True)
        
        # Categorize into high/medium/low engagement
        total = len(engagement_ratios)
        high_threshold = int(total * 0.2)  # Top 20%
        medium_threshold = int(total * 0.6)  # Top 60%
        
        stats['engagement_types']['high_engagement'] = engagement_ratios[:high_threshold]
        stats['engagement_types']['medium_engagement'] = engagement_ratios[high_threshold:medium_threshold]
        stats['engagement_types']['low_engagement'] = engagement_ratios[medium_threshold:]
    
    def analyze_engagement_patterns(self, stats):
        """Analyze engagement patterns across categories."""
        print("\n🔍 Analyzing Engagement Patterns...")
        print("=" * 50)
        
        patterns = {
            'category_engagement': {},
            'engagement_insights': [],
            'recommendations': []
        }
        
        # Analyze each category
        for category, data in stats['categories'].items():
            if not data['subreddits']:
                continue
                
            # Calculate engagement metrics
            subscribers = [sub['subscribers'] for sub in data['subreddits']]
            active_users = [sub['active_user_count'] for sub in data['subreddits']]
            
            if subscribers and active_users:
                avg_engagement_ratio = mean([a/s if s > 0 else 0 for s, a in zip(subscribers, active_users)])
                patterns['category_engagement'][category] = {
                    'avg_engagement_ratio': avg_engagement_ratio,
                    'total_subscribers': data['total_subscribers'],
                    'total_active_users': data['total_active_users'],
                    'subreddit_count': len(data['subreddits'])
                }
        
        # Generate insights
        if patterns['category_engagement']:
            best_category = max(patterns['category_engagement'].items(), key=lambda x: x[1]['avg_engagement_ratio'])
            patterns['engagement_insights'].append(f"Highest engagement category: {best_category[0]} ({best_category[1]['avg_engagement_ratio']:.3f} ratio)")
        
        return patterns
    
    def generate_summary_report(self, stats, patterns):
        """Generate a comprehensive summary report."""
        print("\n📊 REDDIT PLATFORM ENGAGEMENT SUMMARY")
        print("=" * 60)
        
        # Platform Overview
        print(f"\n🌐 PLATFORM OVERVIEW:")
        print(f"   Total Subreddits Analyzed: {stats['total_subreddits_analyzed']:,}")
        print(f"   Total Subscribers: {stats['total_subscribers']:,}")
        print(f"   Total Active Users: {stats['total_active_users']:,}")
        print(f"   Average Subscribers per Subreddit: {stats['total_subscribers'] / stats['total_subreddits_analyzed']:,.0f}")
        
        # Category Breakdown
        print(f"\n📈 CATEGORY BREAKDOWN:")
        for category, data in stats['categories'].items():
            if data['subreddits']:
                print(f"   {category:15s}: {len(data['subreddits']):3d} subreddits | {data['total_subscribers']:8,} total subs | {data['avg_subscribers']:8,.0f} avg subs")
        
        # Top Subreddits
        print(f"\n🏆 TOP 10 SUBREDDITS BY SUBSCRIBERS:")
        for i, sub in enumerate(stats['top_subreddits'][:10], 1):
            print(f"   {i:2d}. r/{sub['name']:20s}: {sub['subscribers']:8,} subscribers")
        
        # Engagement Analysis
        print(f"\n💬 ENGAGEMENT ANALYSIS:")
        high_eng = stats['engagement_types']['high_engagement']
        print(f"   High Engagement Subreddits: {len(high_eng)}")
        if high_eng:
            print(f"   Top High Engagement: r/{high_eng[0][0]} ({high_eng[0][1]:.3f} ratio)")
        
        # Save detailed report
        self._save_detailed_report(stats, patterns)
        
        return {
            'platform_overview': {
                'total_subreddits': stats['total_subreddits_analyzed'],
                'total_subscribers': stats['total_subscribers'],
                'total_active_users': stats['total_active_users']
            },
            'category_breakdown': dict(stats['categories']),
            'top_subreddits': stats['top_subreddits'][:10],
            'engagement_analysis': stats['engagement_types']
        }
    
    def _save_detailed_report(self, stats, patterns):
        """Save detailed report to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reddit_engagement_report_{timestamp}.json"
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'analysis_parameters': {
                'sample_size': len(stats['top_subreddits']),
                'categories_analyzed': len(stats['categories'])
            },
            'platform_statistics': stats,
            'engagement_patterns': patterns
        }
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n💾 Detailed report saved to: {filename}")
    
    def run_complete_analysis(self, sample_size=100):
        """Run the complete engagement analysis."""
        print("🚀 Starting Comprehensive Reddit Engagement Analysis")
        print("=" * 70)
        
        # Step 1: Collect platform statistics
        stats = self.collect_platform_statistics(sample_size)
        
        # Step 2: Analyze engagement patterns
        patterns = self.analyze_engagement_patterns(stats)
        
        # Step 3: Generate summary report
        summary = self.generate_summary_report(stats, patterns)
        
        print(f"\n✅ Analysis Complete!")
        print(f"📊 Analyzed {stats['total_subreddits_analyzed']} subreddits across {len(stats['categories'])} categories")
        
        return summary

def main():
    """Main function to run the engagement analysis."""
    analyzer = RedditEngagementAnalyzer()
    
    # Run analysis with sample size
    sample_size = 50  # Start with 50 for faster testing, increase for more comprehensive analysis
    print(f"🎯 Running analysis on top {sample_size} subreddits...")
    
    try:
        results = analyzer.run_complete_analysis(sample_size)
        print("\n🎉 Reddit engagement analysis completed successfully!")
        return results
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        return None

if __name__ == "__main__":
    main()
