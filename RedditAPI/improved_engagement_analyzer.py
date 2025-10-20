#!/usr/bin/env python3
"""
Improved Reddit Engagement Analysis Tool
Uses alternative methods to get more accurate engagement statistics.
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

class ImprovedRedditAnalyzer:
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
    
    def get_subreddit_stats(self, subreddit_name):
        """Get comprehensive stats for a specific subreddit."""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Get basic info
            display_name = subreddit.display_name
            subscribers = subreddit.subscribers
            active_user_count = subreddit.active_user_count
            over18 = subreddit.over18
            
            # Get recent posts for engagement analysis
            recent_posts = list(subreddit.new(limit=10))
            hot_posts = list(subreddit.hot(limit=10))
            
            # Calculate engagement metrics
            total_score = sum(post.score for post in recent_posts)
            total_comments = sum(post.num_comments for post in recent_posts)
            avg_score = total_score / len(recent_posts) if recent_posts else 0
            avg_comments = total_comments / len(recent_posts) if recent_posts else 0
            
            # Get hot posts metrics
            hot_total_score = sum(post.score for post in hot_posts)
            hot_total_comments = sum(post.num_comments for post in hot_posts)
            hot_avg_score = hot_total_score / len(hot_posts) if hot_posts else 0
            hot_avg_comments = hot_total_comments / len(hot_posts) if hot_posts else 0
            
            return {
                'name': display_name,
                'subscribers': subscribers,
                'active_user_count': active_user_count,
                'over18': over18,
                'recent_engagement': {
                    'avg_score': avg_score,
                    'avg_comments': avg_comments,
                    'total_posts_analyzed': len(recent_posts)
                },
                'hot_engagement': {
                    'avg_score': hot_avg_score,
                    'avg_comments': hot_avg_comments,
                    'total_posts_analyzed': len(hot_posts)
                },
                'category': self._categorize_subreddit(display_name)
            }
            
        except Exception as e:
            print(f"    ⚠️  Error analyzing r/{subreddit_name}: {e}")
            return None
    
    def _categorize_subreddit(self, subreddit_name):
        """Categorize a subreddit based on its name."""
        subreddit_lower = subreddit_name.lower()
        
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword.lower() in subreddit_lower:
                    return category
        
        return 'Other'
    
    def analyze_engagement_by_category(self, subreddit_list):
        """Analyze engagement patterns by category."""
        print("🔍 Analyzing Engagement by Category...")
        print("=" * 50)
        
        category_stats = defaultdict(lambda: {
            'subreddits': [],
            'total_subscribers': 0,
            'total_active_users': 0,
            'engagement_scores': [],
            'comment_rates': [],
            'subreddit_count': 0
        })
        
        for i, sub_name in enumerate(subreddit_list, 1):
            print(f"  {i:2d}. Analyzing r/{sub_name}...")
            
            stats = self.get_subreddit_stats(sub_name)
            if stats:
                category = stats['category']
                category_stats[category]['subreddits'].append(stats)
                category_stats[category]['total_subscribers'] += stats['subscribers']
                category_stats[category]['total_active_users'] += stats['active_user_count']
                category_stats[category]['engagement_scores'].append(stats['recent_engagement']['avg_score'])
                category_stats[category]['comment_rates'].append(stats['recent_engagement']['avg_comments'])
                category_stats[category]['subreddit_count'] += 1
                
                print(f"      ✅ {stats['subscribers']:,} subs | {stats['recent_engagement']['avg_score']:.1f} avg score | {category}")
            
            time.sleep(0.2)  # Be respectful to API
        
        return dict(category_stats)
    
    def analyze_engagement_types(self, subreddit_list):
        """Analyze different types of engagement."""
        print("\n💬 Analyzing Engagement Types...")
        print("=" * 40)
        
        engagement_data = []
        
        for sub_name in subreddit_list[:10]:  # Analyze top 10 for detailed engagement
            print(f"  📊 Analyzing engagement in r/{sub_name}...")
            
            try:
                subreddit = self.reddit.subreddit(sub_name)
                
                # Get recent posts
                recent_posts = list(subreddit.new(limit=20))
                
                if recent_posts:
                    # Calculate engagement metrics
                    scores = [post.score for post in recent_posts]
                    comments = [post.num_comments for post in recent_posts]
                    upvote_ratios = [getattr(post, 'upvote_ratio', 0) for post in recent_posts]
                    
                    engagement_data.append({
                        'subreddit': sub_name,
                        'subscribers': subreddit.subscribers,
                        'avg_score': mean(scores),
                        'avg_comments': mean(comments),
                        'avg_upvote_ratio': mean(upvote_ratios),
                        'total_posts': len(recent_posts),
                        'engagement_rate': mean(comments) / max(1, subreddit.subscribers) * 1000000  # Comments per million subscribers
                    })
                    
                    print(f"      📈 {mean(scores):.1f} avg score | {mean(comments):.1f} avg comments | {mean(upvote_ratios):.2f} upvote ratio")
                
                time.sleep(0.3)
                
            except Exception as e:
                print(f"      ⚠️  Error: {e}")
                continue
        
        return engagement_data
    
    def generate_comprehensive_report(self, category_stats, engagement_data):
        """Generate a comprehensive engagement report."""
        print("\n📊 COMPREHENSIVE REDDIT ENGAGEMENT REPORT")
        print("=" * 60)
        
        # Platform Overview
        total_subscribers = sum(cat['total_subscribers'] for cat in category_stats.values())
        total_active_users = sum(cat['total_active_users'] for cat in category_stats.values())
        total_subreddits = sum(cat['subreddit_count'] for cat in category_stats.values())
        
        print(f"\n🌐 PLATFORM OVERVIEW:")
        print(f"   Total Subreddits Analyzed: {total_subreddits}")
        print(f"   Total Subscribers: {total_subscribers:,}")
        print(f"   Total Active Users: {total_active_users:,}")
        print(f"   Average Subscribers per Subreddit: {total_subscribers / max(1, total_subreddits):,.0f}")
        
        # Category Analysis
        print(f"\n📈 CATEGORY BREAKDOWN:")
        for category, stats in category_stats.items():
            if stats['subreddit_count'] > 0:
                avg_subscribers = stats['total_subscribers'] / stats['subreddit_count']
                avg_engagement = mean(stats['engagement_scores']) if stats['engagement_scores'] else 0
                avg_comments = mean(stats['comment_rates']) if stats['comment_rates'] else 0
                
                print(f"   {category:15s}: {stats['subreddit_count']:2d} subs | {stats['total_subscribers']:8,} total | {avg_subscribers:8,.0f} avg | {avg_engagement:6.1f} score | {avg_comments:6.1f} comments")
        
        # Engagement Analysis
        if engagement_data:
            print(f"\n💬 ENGAGEMENT ANALYSIS:")
            sorted_engagement = sorted(engagement_data, key=lambda x: x['engagement_rate'], reverse=True)
            
            print(f"   Top Engagement Subreddits:")
            for i, sub in enumerate(sorted_engagement[:5], 1):
                print(f"     {i}. r/{sub['subreddit']:20s}: {sub['engagement_rate']:8.2f} engagement rate | {sub['avg_comments']:6.1f} avg comments")
        
        # Save detailed report
        self._save_engagement_report(category_stats, engagement_data)
        
        return {
            'platform_overview': {
                'total_subreddits': total_subreddits,
                'total_subscribers': total_subscribers,
                'total_active_users': total_active_users
            },
            'category_breakdown': category_stats,
            'engagement_analysis': engagement_data
        }
    
    def _save_engagement_report(self, category_stats, engagement_data):
        """Save detailed engagement report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reddit_engagement_detailed_{timestamp}.json"
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'category_statistics': category_stats,
            'engagement_data': engagement_data,
            'summary': {
                'total_categories': len(category_stats),
                'total_subreddits_analyzed': sum(cat['subreddit_count'] for cat in category_stats.values()),
                'total_subscribers': sum(cat['total_subscribers'] for cat in category_stats.values())
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n💾 Detailed engagement report saved to: {filename}")
    
    def run_engagement_analysis(self, subreddit_list=None):
        """Run the complete engagement analysis."""
        if subreddit_list is None:
            # Default list of popular subreddits to analyze
            subreddit_list = [
                'AskReddit', 'gaming', 'technology', 'personalfinance', 'stocks',
                'buildapc', 'wallstreetbets', 'investing', 'cryptocurrency', 'crypto',
                'movies', 'television', 'music', 'books', 'fitness', 'food',
                'news', 'worldnews', 'politics', 'science', 'askscience',
                'DIY', 'photography', 'art', 'writing', 'boardgames',
                'loseit', 'nutrition', 'mentalhealth', 'depression', 'anxiety'
            ]
        
        print("🚀 Starting Improved Reddit Engagement Analysis")
        print("=" * 60)
        print(f"📊 Analyzing {len(subreddit_list)} subreddits...")
        
        # Step 1: Analyze by category
        category_stats = self.analyze_engagement_by_category(subreddit_list)
        
        # Step 2: Analyze engagement types
        engagement_data = self.analyze_engagement_types(subreddit_list)
        
        # Step 3: Generate comprehensive report
        results = self.generate_comprehensive_report(category_stats, engagement_data)
        
        print(f"\n✅ Engagement Analysis Complete!")
        print(f"📊 Analyzed {len(subreddit_list)} subreddits across {len(category_stats)} categories")
        
        return results

def main():
    """Main function to run the engagement analysis."""
    analyzer = ImprovedRedditAnalyzer()
    
    # Custom subreddit list for analysis
    subreddit_list = [
        'AskReddit', 'gaming', 'technology', 'personalfinance', 'stocks',
        'buildapc', 'wallstreetbets', 'investing', 'cryptocurrency', 'crypto',
        'movies', 'television', 'music', 'books', 'fitness', 'food',
        'news', 'worldnews', 'politics', 'science', 'askscience',
        'DIY', 'photography', 'art', 'writing', 'boardgames',
        'loseit', 'nutrition', 'mentalhealth', 'depression', 'anxiety',
        'home', 'travel', 'fashion', 'beauty', 'cooking', 'gardening',
        'space', 'biology', 'chemistry', 'physics', 'explainlikeimfive'
    ]
    
    try:
        results = analyzer.run_engagement_analysis(subreddit_list)
        print("\n🎉 Reddit engagement analysis completed successfully!")
        return results
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        return None

if __name__ == "__main__":
    main()
