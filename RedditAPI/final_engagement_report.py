#!/usr/bin/env python3
"""
Final Reddit Engagement Analysis Tool
Provides comprehensive Reddit platform engagement statistics with proper error handling.
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

class FinalRedditAnalyzer:
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
    
    def get_subreddit_engagement(self, subreddit_name):
        """Get engagement metrics for a specific subreddit."""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Get basic info (handle missing attributes gracefully)
            display_name = subreddit.display_name
            subscribers = getattr(subreddit, 'subscribers', 0)
            over18 = getattr(subreddit, 'over18', False)
            
            # Get recent posts for engagement analysis
            recent_posts = list(subreddit.new(limit=20))
            hot_posts = list(subreddit.hot(limit=20))
            
            # Calculate engagement metrics
            recent_scores = [post.score for post in recent_posts if hasattr(post, 'score')]
            recent_comments = [post.num_comments for post in recent_posts if hasattr(post, 'num_comments')]
            recent_upvote_ratios = [getattr(post, 'upvote_ratio', 0) for post in recent_posts if hasattr(post, 'upvote_ratio')]
            
            hot_scores = [post.score for post in hot_posts if hasattr(post, 'score')]
            hot_comments = [post.num_comments for post in hot_posts if hasattr(post, 'num_comments')]
            hot_upvote_ratios = [getattr(post, 'upvote_ratio', 0) for post in hot_posts if hasattr(post, 'upvote_ratio')]
            
            # Calculate averages
            recent_avg_score = mean(recent_scores) if recent_scores else 0
            recent_avg_comments = mean(recent_comments) if recent_comments else 0
            recent_avg_upvote_ratio = mean(recent_upvote_ratios) if recent_upvote_ratios else 0
            
            hot_avg_score = mean(hot_scores) if hot_scores else 0
            hot_avg_comments = mean(hot_comments) if hot_comments else 0
            hot_avg_upvote_ratio = mean(hot_upvote_ratios) if hot_upvote_ratios else 0
            
            # Calculate engagement rate (comments per subscriber)
            engagement_rate = (recent_avg_comments / max(1, subscribers)) * 1000000 if subscribers > 0 else 0
            
            return {
                'name': display_name,
                'subscribers': subscribers,
                'over18': over18,
                'recent_engagement': {
                    'avg_score': recent_avg_score,
                    'avg_comments': recent_avg_comments,
                    'avg_upvote_ratio': recent_avg_upvote_ratio,
                    'total_posts_analyzed': len(recent_posts)
                },
                'hot_engagement': {
                    'avg_score': hot_avg_score,
                    'avg_comments': hot_avg_comments,
                    'avg_upvote_ratio': hot_avg_upvote_ratio,
                    'total_posts_analyzed': len(hot_posts)
                },
                'engagement_rate': engagement_rate,
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
    
    def analyze_platform_engagement(self, subreddit_list):
        """Analyze engagement across the platform."""
        print("🚀 Analyzing Reddit Platform Engagement...")
        print("=" * 60)
        
        results = {
            'subreddit_data': [],
            'category_stats': defaultdict(lambda: {
                'subreddits': [],
                'total_subscribers': 0,
                'total_engagement_score': 0,
                'total_comments': 0,
                'engagement_rates': [],
                'subreddit_count': 0
            }),
            'platform_summary': {
                'total_subreddits': 0,
                'total_subscribers': 0,
                'avg_engagement_rate': 0,
                'top_engagement_subreddits': []
            }
        }
        
        successful_analyses = 0
        
        for i, sub_name in enumerate(subreddit_list, 1):
            print(f"  {i:2d}. Analyzing r/{sub_name}...")
            
            engagement_data = self.get_subreddit_engagement(sub_name)
            if engagement_data:
                results['subreddit_data'].append(engagement_data)
                successful_analyses += 1
                
                # Categorize
                category = engagement_data['category']
                results['category_stats'][category]['subreddits'].append(engagement_data)
                results['category_stats'][category]['total_subscribers'] += engagement_data['subscribers']
                results['category_stats'][category]['total_engagement_score'] += engagement_data['recent_engagement']['avg_score']
                results['category_stats'][category]['total_comments'] += engagement_data['recent_engagement']['avg_comments']
                results['category_stats'][category]['engagement_rates'].append(engagement_data['engagement_rate'])
                results['category_stats'][category]['subreddit_count'] += 1
                
                print(f"      ✅ {engagement_data['subscribers']:,} subs | {engagement_data['recent_engagement']['avg_score']:.1f} score | {engagement_data['recent_engagement']['avg_comments']:.1f} comments | {engagement_data['category']}")
            
            time.sleep(0.2)  # Be respectful to API
        
        # Calculate platform summary
        if results['subreddit_data']:
            results['platform_summary']['total_subreddits'] = successful_analyses
            results['platform_summary']['total_subscribers'] = sum(sub['subscribers'] for sub in results['subreddit_data'])
            results['platform_summary']['avg_engagement_rate'] = mean(sub['engagement_rate'] for sub in results['subreddit_data'])
            
            # Top engagement subreddits
            sorted_by_engagement = sorted(results['subreddit_data'], key=lambda x: x['engagement_rate'], reverse=True)
            results['platform_summary']['top_engagement_subreddits'] = sorted_by_engagement[:10]
        
        return results
    
    def generate_final_report(self, results):
        """Generate the final comprehensive report."""
        print("\n📊 FINAL REDDIT PLATFORM ENGAGEMENT REPORT")
        print("=" * 70)
        
        summary = results['platform_summary']
        category_stats = results['category_stats']
        
        # Platform Overview
        print(f"\n🌐 PLATFORM OVERVIEW:")
        print(f"   Total Subreddits Analyzed: {summary['total_subreddits']}")
        print(f"   Total Subscribers: {summary['total_subscribers']:,}")
        print(f"   Average Engagement Rate: {summary['avg_engagement_rate']:.2f} (comments per million subscribers)")
        
        # Category Breakdown
        print(f"\n📈 ENGAGEMENT BY CATEGORY:")
        for category, stats in category_stats.items():
            if stats['subreddit_count'] > 0:
                avg_subscribers = stats['total_subscribers'] / stats['subreddit_count']
                avg_engagement_score = stats['total_engagement_score'] / stats['subreddit_count']
                avg_comments = stats['total_comments'] / stats['subreddit_count']
                avg_engagement_rate = mean(stats['engagement_rates']) if stats['engagement_rates'] else 0
                
                print(f"   {category:15s}: {stats['subreddit_count']:2d} subs | {stats['total_subscribers']:8,} total | {avg_subscribers:8,.0f} avg subs | {avg_engagement_score:6.1f} score | {avg_comments:6.1f} comments | {avg_engagement_rate:6.2f} rate")
        
        # Top Engagement Subreddits
        print(f"\n🏆 TOP 10 HIGHEST ENGAGEMENT SUBREDDITS:")
        for i, sub in enumerate(summary['top_engagement_subreddits'], 1):
            print(f"   {i:2d}. r/{sub['name']:20s}: {sub['engagement_rate']:8.2f} rate | {sub['subscribers']:8,} subs | {sub['recent_engagement']['avg_comments']:6.1f} comments | {sub['category']}")
        
        # Engagement Insights
        print(f"\n💡 ENGAGEMENT INSIGHTS:")
        if summary['top_engagement_subreddits']:
            top_sub = summary['top_engagement_subreddits'][0]
            print(f"   🥇 Highest Engagement: r/{top_sub['name']} ({top_sub['engagement_rate']:.2f} rate)")
            print(f"   📊 Most Comments: r/{top_sub['name']} ({top_sub['recent_engagement']['avg_comments']:.1f} avg comments)")
            print(f"   🎯 Category: {top_sub['category']}")
        
        # Category Analysis
        if category_stats:
            best_category = max(category_stats.items(), key=lambda x: mean(x[1]['engagement_rates']) if x[1]['engagement_rates'] else 0)
            print(f"   🏆 Best Performing Category: {best_category[0]} (avg rate: {mean(best_category[1]['engagement_rates']):.2f})")
        
        # Save detailed report
        self._save_final_report(results)
        
        return results
    
    def _save_final_report(self, results):
        """Save the final comprehensive report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reddit_final_engagement_report_{timestamp}.json"
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'analysis_type': 'comprehensive_reddit_engagement',
            'platform_summary': results['platform_summary'],
            'category_statistics': dict(results['category_stats']),
            'detailed_subreddit_data': results['subreddit_data'],
            'insights': {
                'total_categories_analyzed': len(results['category_stats']),
                'successful_analyses': len(results['subreddit_data']),
                'engagement_distribution': {
                    'high_engagement': len([s for s in results['subreddit_data'] if s['engagement_rate'] > 5]),
                    'medium_engagement': len([s for s in results['subreddit_data'] if 1 <= s['engagement_rate'] <= 5]),
                    'low_engagement': len([s for s in results['subreddit_data'] if s['engagement_rate'] < 1])
                }
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n💾 Final comprehensive report saved to: {filename}")
    
    def run_final_analysis(self):
        """Run the final comprehensive engagement analysis."""
        # Curated list of diverse subreddits for analysis
        subreddit_list = [
            # Technology
            'technology', 'programming', 'buildapc', 'apple', 'android', 'linux',
            
            # Finance & Investing
            'personalfinance', 'stocks', 'investing', 'wallstreetbets', 'cryptocurrency', 'crypto',
            
            # Gaming
            'gaming', 'pcgaming', 'nintendo', 'playstation', 'xbox', 'steam',
            
            # Entertainment
            'movies', 'television', 'music', 'books', 'comics', 'anime',
            
            # Lifestyle
            'fitness', 'food', 'travel', 'fashion', 'beauty', 'home', 'cooking',
            
            # News & Politics
            'news', 'worldnews', 'politics', 'europe', 'canada',
            
            # Science & Education
            'science', 'askscience', 'explainlikeimfive', 'space', 'biology', 'chemistry',
            
            # Social & Discussion
            'askreddit', 'nostupidquestions', 'casualconversation', 'unpopularopinion',
            
            # Hobbies & Interests
            'DIY', 'photography', 'art', 'writing', 'boardgames', 'woodworking',
            
            # Health & Wellness
            'fitness', 'loseit', 'nutrition', 'mentalhealth', 'depression', 'anxiety'
        ]
        
        print("🚀 Starting Final Reddit Engagement Analysis")
        print("=" * 60)
        print(f"📊 Analyzing {len(subreddit_list)} diverse subreddits...")
        
        # Run the analysis
        results = self.analyze_platform_engagement(subreddit_list)
        
        # Generate final report
        final_results = self.generate_final_report(results)
        
        print(f"\n✅ Final Analysis Complete!")
        print(f"📊 Successfully analyzed {len(results['subreddit_data'])} subreddits")
        print(f"📈 Covered {len(results['category_stats'])} categories")
        
        return final_results

def main():
    """Main function to run the final engagement analysis."""
    analyzer = FinalRedditAnalyzer()
    
    try:
        results = analyzer.run_final_analysis()
        print("\n🎉 Reddit engagement analysis completed successfully!")
        print("\n📋 SUMMARY:")
        print(f"   • Analyzed {len(results['subreddit_data'])} subreddits")
        print(f"   • Covered {len(results['category_stats'])} categories")
        print(f"   • Total subscribers: {results['platform_summary']['total_subscribers']:,}")
        print(f"   • Average engagement rate: {results['platform_summary']['avg_engagement_rate']:.2f}")
        return results
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        return None

if __name__ == "__main__":
    main()
