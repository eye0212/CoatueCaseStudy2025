#!/usr/bin/env python3
"""
Comprehensive DAU Estimator
Maximum coverage search across Reddit to get the most accurate DAU/WAU/MAU estimates.
"""

import sys
import os
import time
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional
import random

sys.path.append('src')
from reddit_pitch.collector import reddit_client
from reddit_pitch.config import Settings, load_config
from reddit_pitch.db import connect

class ComprehensiveDAUEstimator:
    def __init__(self):
        self.settings = Settings()
        self.reddit = reddit_client(self.settings)
        self.conn = connect(self.settings.db_path)
        
        # Comprehensive subreddit lists for maximum coverage
        self.subreddit_categories = {
            'top_global': [
                'AskReddit', 'gaming', 'technology', 'personalfinance', 'stocks',
                'buildapc', 'wallstreetbets', 'investing', 'cryptocurrency', 'crypto',
                'movies', 'television', 'music', 'books', 'fitness', 'food',
                'news', 'worldnews', 'politics', 'science', 'askscience',
                'DIY', 'photography', 'art', 'writing', 'boardgames',
                'loseit', 'nutrition', 'mentalhealth', 'depression', 'anxiety',
                'home', 'travel', 'fashion', 'beauty', 'cooking', 'gardening',
                'space', 'biology', 'chemistry', 'physics', 'explainlikeimfive',
                'programming', 'MachineLearning', 'artificial', 'futurology',
                'dataisbeautiful', 'mildlyinteresting', 'interestingasfuck',
                'todayilearned', 'unpopularopinion', 'changemyview', 'casualconversation',
                'nostupidquestions', 'outoftheloop', 'explainlikeimfive', 'askscience',
                'tifu', 'amitheasshole', 'relationship_advice', 'relationships',
                'personalfinance', 'investing', 'stocks', 'cryptocurrency', 'crypto',
                'wallstreetbets', 'securityanalysis', 'options', 'dividends',
                'realestate', 'entrepreneur', 'startups', 'business', 'marketing',
                'sales', 'consulting', 'freelance', 'careerguidance', 'jobs',
                'cscareerquestions', 'ITCareerQuestions', 'careerchange',
                'financialindependence', 'FIRE', 'leanfire', 'fatfire', 'coastfire'
            ],
            'tech_subreddits': [
                'programming', 'MachineLearning', 'artificial', 'datascience',
                'statistics', 'math', 'compsci', 'cscareerquestions', 'ITCareerQuestions',
                'sysadmin', 'networking', 'cybersecurity', 'hacking', 'privacy',
                'linux', 'windows', 'macos', 'android', 'apple', 'iphone',
                'buildapc', 'buildapcsales', 'pcmasterrace', 'battlestations',
                'gaming', 'pcgaming', 'nintendo', 'playstation', 'xbox', 'steam',
                'gamedev', 'indiegaming', 'gaminglaptops', 'hardware',
                'software', 'webdev', 'frontend', 'backend', 'devops', 'cloud',
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform'
            ],
            'finance_subreddits': [
                'personalfinance', 'investing', 'stocks', 'cryptocurrency', 'crypto',
                'wallstreetbets', 'securityanalysis', 'options', 'dividends',
                'realestate', 'entrepreneur', 'startups', 'business', 'marketing',
                'sales', 'consulting', 'freelance', 'careerguidance', 'jobs',
                'cscareerquestions', 'ITCareerQuestions', 'careerchange',
                'financialindependence', 'FIRE', 'leanfire', 'fatfire', 'coastfire',
                'budgeting', 'debt', 'credit', 'banking', 'insurance', 'taxes',
                'retirement', 'pension', 'socialsecurity', 'medicare', 'medicaid'
            ],
            'lifestyle_subreddits': [
                'fitness', 'loseit', 'nutrition', 'bodybuilding', 'powerlifting',
                'crossfit', 'yoga', 'meditation', 'mindfulness', 'mentalhealth',
                'depression', 'anxiety', 'bipolar', 'ptsd', 'adhd', 'autism',
                'relationships', 'relationship_advice', 'dating', 'marriage',
                'parenting', 'childfree', 'pregnant', 'babybumps', 'toddlers',
                'homeschooling', 'teachers', 'college', 'university', 'gradschool',
                'studytips', 'productivity', 'organization', 'minimalism',
                'declutter', 'homemaking', 'cleaning', 'cooking', 'baking',
                'mealprep', 'recipes', 'food', 'restaurants', 'travel', 'solo',
                'backpacking', 'camping', 'hiking', 'climbing', 'running',
                'cycling', 'swimming', 'tennis', 'golf', 'soccer', 'basketball',
                'football', 'baseball', 'hockey', 'rugby', 'wrestling', 'boxing',
                'martialarts', 'dancing', 'singing', 'music', 'guitar', 'piano',
                'drums', 'violin', 'cello', 'saxophone', 'trumpet', 'flute',
                'art', 'painting', 'drawing', 'sculpture', 'photography', 'design',
                'fashion', 'beauty', 'makeup', 'skincare', 'hair', 'nails',
                'jewelry', 'watches', 'shoes', 'bags', 'accessories', 'style'
            ],
            'news_subreddits': [
                'news', 'worldnews', 'politics', 'europe', 'canada', 'australia',
                'unitedkingdom', 'ireland', 'scotland', 'wales', 'northernireland',
                'germany', 'france', 'spain', 'italy', 'netherlands', 'belgium',
                'switzerland', 'austria', 'sweden', 'norway', 'denmark', 'finland',
                'iceland', 'poland', 'czech', 'hungary', 'romania', 'bulgaria',
                'croatia', 'serbia', 'slovenia', 'slovakia', 'estonia', 'latvia',
                'lithuania', 'ukraine', 'russia', 'belarus', 'moldova', 'georgia',
                'armenia', 'azerbaijan', 'kazakhstan', 'uzbekistan', 'kyrgyzstan',
                'tajikistan', 'turkmenistan', 'mongolia', 'china', 'japan', 'korea',
                'taiwan', 'hongkong', 'singapore', 'malaysia', 'thailand', 'vietnam',
                'philippines', 'indonesia', 'brunei', 'cambodia', 'laos', 'myanmar',
                'bangladesh', 'india', 'pakistan', 'srilanka', 'maldives', 'nepal',
                'bhutan', 'afghanistan', 'iran', 'iraq', 'syria', 'lebanon',
                'jordan', 'israel', 'palestine', 'saudiarabia', 'uae', 'qatar',
                'kuwait', 'bahrain', 'oman', 'yemen', 'turkey', 'cyprus', 'greece',
                'albania', 'macedonia', 'montenegro', 'bosnia', 'kosovo', 'albania'
            ],
            'science_subreddits': [
                'science', 'askscience', 'explainlikeimfive', 'space', 'astronomy',
                'physics', 'chemistry', 'biology', 'medicine', 'health', 'fitness',
                'nutrition', 'psychology', 'neuroscience', 'cognitive', 'behavioral',
                'sociology', 'anthropology', 'archaeology', 'history', 'geography',
                'geology', 'meteorology', 'oceanography', 'environmental', 'climate',
                'ecology', 'botany', 'zoology', 'paleontology', 'evolution',
                'genetics', 'molecular', 'cell', 'microbiology', 'virology',
                'immunology', 'pathology', 'pharmacology', 'toxicology', 'epidemiology',
                'publichealth', 'globalhealth', 'tropicalmedicine', 'infectious',
                'chronic', 'mentalhealth', 'psychiatry', 'psychology', 'therapy',
                'counseling', 'socialwork', 'nursing', 'medicine', 'surgery',
                'cardiology', 'neurology', 'oncology', 'pediatrics', 'geriatrics',
                'emergency', 'trauma', 'criticalcare', 'anesthesia', 'radiology',
                'pathology', 'laboratory', 'pharmacy', 'dentistry', 'optometry',
                'podiatry', 'chiropractic', 'physicaltherapy', 'occupationaltherapy'
            ],
            'hobby_subreddits': [
                'DIY', 'woodworking', 'metalworking', 'welding', 'machining',
                'electronics', 'arduino', 'raspberry_pi', 'microcontrollers',
                'robotics', 'drones', 'quadcopter', 'fpv', 'aerial', 'photography',
                'videography', 'filmmaking', 'editing', 'postproduction', 'cinematography',
                'lighting', 'sound', 'audio', 'recording', 'mixing', 'mastering',
                'musicproduction', 'composing', 'songwriting', 'lyrics', 'poetry',
                'writing', 'screenwriting', 'playwriting', 'novels', 'shortstories',
                'fantasy', 'scifi', 'horror', 'mystery', 'thriller', 'romance',
                'literature', 'books', 'reading', 'bookclub', 'bookrecommendations',
                'libraries', 'librarians', 'archives', 'museums', 'galleries',
                'exhibitions', 'collections', 'antiques', 'vintage', 'retro',
                'nostalgia', 'memorabilia', 'collectibles', 'trading', 'bartering',
                'auctions', 'estatesales', 'garagesales', 'fleamarkets', 'thriftstores'
            ]
        }
        
        # Initialize database
        self._init_comprehensive_tables()
    
    def _init_comprehensive_tables(self):
        """Initialize comprehensive database tables."""
        cursor = self.conn.cursor()
        
        # Comprehensive activity tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comprehensive_activity (
                id TEXT PRIMARY KEY,
                author TEXT,
                subreddit TEXT,
                activity_type TEXT,
                created_utc INTEGER,
                date TEXT,
                score INTEGER,
                num_comments INTEGER,
                category TEXT,
                collected_at TEXT
            )
        """)
        
        # Daily comprehensive metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comprehensive_daily_metrics (
                date TEXT PRIMARY KEY,
                total_activities INTEGER,
                unique_authors INTEGER,
                unique_subreddits INTEGER,
                categories_covered INTEGER,
                dau_prime INTEGER,
                wau_prime INTEGER,
                mau_prime INTEGER,
                avg_score REAL,
                avg_comments REAL,
                collection_efficiency REAL,
                created_at TEXT
            )
        """)
        
        # Subreddit performance tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subreddit_performance (
                subreddit TEXT,
                date TEXT,
                activities_collected INTEGER,
                unique_authors INTEGER,
                avg_score REAL,
                avg_comments REAL,
                collection_success_rate REAL,
                PRIMARY KEY (subreddit, date)
            )
        """)
        
        self.conn.commit()
    
    def collect_comprehensive_data(self, days_back=1):
        """Collect comprehensive data from all subreddit categories."""
        print("🚀 Starting Comprehensive DAU Data Collection...")
        print("=" * 70)
        
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days_back-1)
        
        total_activities = 0
        total_authors = set()
        total_subreddits = set()
        category_stats = defaultdict(lambda: {'activities': 0, 'authors': set(), 'subreddits': set()})
        
        # Collect from each category
        for category, subreddits in self.subreddit_categories.items():
            print(f"\n📊 Collecting from {category.upper()} ({len(subreddits)} subreddits)...")
            print("-" * 50)
            
            category_activities = 0
            category_authors = set()
            category_subreddits = set()
            
            # Sample subreddits for comprehensive coverage
            sample_size = min(50, len(subreddits))  # Limit for API efficiency
            sampled_subreddits = random.sample(subreddits, sample_size)
            
            for i, subreddit_name in enumerate(sampled_subreddits, 1):
                print(f"  {i:3d}. Collecting from r/{subreddit_name}...")
                
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    # Collect recent posts and comments
                    activities = self._collect_subreddit_activities(subreddit, start_date, end_date)
                    
                    if activities:
                        # Store activities
                        self._store_activities(activities, category)
                        
                        # Update statistics
                        for activity in activities:
                            total_activities += 1
                            category_activities += 1
                            
                            if activity['author'] not in {'AutoModerator', '[deleted]', '[removed]', 'None', ''}:
                                total_authors.add(activity['author'])
                                category_authors.add(activity['author'])
                            
                            total_subreddits.add(activity['subreddit'])
                            category_subreddits.add(activity['subreddit'])
                        
                        print(f"      ✅ {len(activities)} activities, {len(category_authors)} unique authors")
                    else:
                        print(f"      ⚠️  No recent activity")
                    
                    time.sleep(0.1)  # Be respectful to API
                    
                except Exception as e:
                    print(f"      ❌ Error: {e}")
                    continue
            
            # Store category statistics
            category_stats[category] = {
                'activities': category_activities,
                'authors': len(category_authors),
                'subreddits': len(category_subreddits)
            }
            
            print(f"  📈 {category}: {category_activities} activities, {len(category_authors)} authors, {len(category_subreddits)} subreddits")
        
        # Calculate comprehensive metrics
        self._calculate_comprehensive_metrics(
            end_date, total_activities, len(total_authors), len(total_subreddits), category_stats
        )
        
        print(f"\n✅ Comprehensive Data Collection Complete!")
        print(f"📊 Total Activities: {total_activities:,}")
        print(f"👥 Unique Authors: {len(total_authors):,}")
        print(f"📱 Subreddits Covered: {len(total_subreddits):,}")
        print(f"📈 Categories: {len(category_stats)}")
        
        return {
            'total_activities': total_activities,
            'unique_authors': len(total_authors),
            'unique_subreddits': len(total_subreddits),
            'categories': len(category_stats),
            'category_stats': dict(category_stats)
        }
    
    def _collect_subreddit_activities(self, subreddit, start_date, end_date):
        """Collect activities from a subreddit within date range."""
        activities = []
        
        try:
            # Collect recent posts
            for post in subreddit.new(limit=100):
                post_date = datetime.fromtimestamp(post.created_utc, timezone.utc).date()
                
                if start_date <= post_date <= end_date:
                    activities.append({
                        'id': post.id,
                        'author': str(post.author) if post.author else '[deleted]',
                        'subreddit': subreddit.display_name,
                        'activity_type': 'post',
                        'created_utc': post.created_utc,
                        'date': post_date.isoformat(),
                        'score': getattr(post, 'score', 0),
                        'num_comments': getattr(post, 'num_comments', 0),
                        'category': 'general',
                        'collected_at': datetime.now().isoformat()
                    })
                elif post_date < start_date:
                    break
            
            # Collect recent comments
            for comment in subreddit.comments(limit=100):
                comment_date = datetime.fromtimestamp(comment.created_utc, timezone.utc).date()
                
                if start_date <= comment_date <= end_date:
                    activities.append({
                        'id': comment.id,
                        'author': str(comment.author) if comment.author else '[deleted]',
                        'subreddit': subreddit.display_name,
                        'activity_type': 'comment',
                        'created_utc': comment.created_utc,
                        'date': comment_date.isoformat(),
                        'score': getattr(comment, 'score', 0),
                        'num_comments': 0,
                        'category': 'general',
                        'collected_at': datetime.now().isoformat()
                    })
                elif comment_date < start_date:
                    break
                    
        except Exception as e:
            print(f"      ⚠️  Error collecting activities: {e}")
        
        return activities
    
    def _store_activities(self, activities, category):
        """Store activities in database."""
        cursor = self.conn.cursor()
        
        for activity in activities:
            cursor.execute("""
                INSERT OR REPLACE INTO comprehensive_activity 
                (id, author, subreddit, activity_type, created_utc, date, 
                 score, num_comments, category, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                activity['id'], activity['author'], activity['subreddit'],
                activity['activity_type'], activity['created_utc'], activity['date'],
                activity['score'], activity['num_comments'], category, activity['collected_at']
            ))
        
        self.conn.commit()
    
    def _calculate_comprehensive_metrics(self, target_date, total_activities, unique_authors, unique_subreddits, category_stats):
        """Calculate comprehensive DAU metrics."""
        cursor = self.conn.cursor()
        
        # Calculate rolling windows
        wau_prime = self._calculate_rolling_unique_authors(target_date, 7)
        mau_prime = self._calculate_rolling_unique_authors(target_date, 30)
        
        # Calculate collection efficiency
        total_possible_subreddits = sum(len(subreddits) for subreddits in self.subreddit_categories.values())
        collection_efficiency = unique_subreddits / total_possible_subreddits if total_possible_subreddits > 0 else 0
        
        # Calculate averages
        cursor.execute("""
            SELECT AVG(score), AVG(num_comments) 
            FROM comprehensive_activity 
            WHERE date = ?
        """, (target_date.isoformat(),))
        
        result = cursor.fetchone()
        avg_score = result[0] if result[0] else 0
        avg_comments = result[1] if result[1] else 0
        
        # Store comprehensive daily metrics
        cursor.execute("""
            INSERT OR REPLACE INTO comprehensive_daily_metrics 
            (date, total_activities, unique_authors, unique_subreddits, categories_covered,
             dau_prime, wau_prime, mau_prime, avg_score, avg_comments, collection_efficiency, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            target_date.isoformat(), total_activities, unique_authors, unique_subreddits,
            len(category_stats), unique_authors, wau_prime, mau_prime,
            avg_score, avg_comments, collection_efficiency, datetime.now().isoformat()
        ))
        
        self.conn.commit()
    
    def _calculate_rolling_unique_authors(self, target_date, window_days):
        """Calculate rolling unique authors for WAU/MAU."""
        start_date = target_date - timedelta(days=window_days-1)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT author) FROM comprehensive_activity 
            WHERE date >= ? AND date <= ? 
            AND author NOT IN ('AutoModerator', '[deleted]', '[removed]', 'None', '')
        """, (start_date.isoformat(), target_date.isoformat()))
        
        return cursor.fetchone()[0]
    
    def generate_comprehensive_report(self):
        """Generate comprehensive DAU report."""
        print("\n📊 Generating Comprehensive DAU Report...")
        print("=" * 60)
        
        cursor = self.conn.cursor()
        
        # Get latest comprehensive metrics
        cursor.execute("""
            SELECT date, total_activities, unique_authors, unique_subreddits, 
                   categories_covered, dau_prime, wau_prime, mau_prime,
                   avg_score, avg_comments, collection_efficiency
            FROM comprehensive_daily_metrics 
            ORDER BY date DESC LIMIT 1
        """)
        
        result = cursor.fetchone()
        if not result:
            print("  ⚠️  No comprehensive data available")
            return None
        
        date, total_activities, unique_authors, unique_subreddits, categories_covered, \
        dau_prime, wau_prime, mau_prime, avg_score, avg_comments, collection_efficiency = result
        
        # Get category breakdown
        cursor.execute("""
            SELECT category, COUNT(*) as activities, COUNT(DISTINCT author) as authors,
                   COUNT(DISTINCT subreddit) as subreddits
            FROM comprehensive_activity 
            WHERE date = ?
            GROUP BY category
            ORDER BY activities DESC
        """, (date,))
        
        category_breakdown = cursor.fetchall()
        
        # Print comprehensive report
        print(f"\n📈 COMPREHENSIVE DAU REPORT - {date}")
        print("=" * 60)
        print(f"📊 Total Activities: {total_activities:,}")
        print(f"👥 Unique Authors (DAU′): {dau_prime:,}")
        print(f"📱 Subreddits Covered: {unique_subreddits:,}")
        print(f"📈 Categories: {categories_covered}")
        print(f"⚡ Collection Efficiency: {collection_efficiency:.1%}")
        print(f"📊 Average Score: {avg_score:.1f}")
        print(f"💬 Average Comments: {avg_comments:.1f}")
        
        print(f"\n🔄 Rolling Windows:")
        print(f"   WAU′ (7-day): {wau_prime:,}")
        print(f"   MAU′ (30-day): {mau_prime:,}")
        
        print(f"\n📊 Category Breakdown:")
        for category, activities, authors, subreddits in category_breakdown:
            print(f"   {category:20s}: {activities:4d} activities | {authors:4d} authors | {subreddits:3d} subreddits")
        
        # Calculate calibrated metrics (using same factors as before)
        k_dau = 48346.56
        k_wau = 176917.99
        k_mau = 322310.41
        
        dau_calibrated = dau_prime * k_dau
        wau_calibrated = wau_prime * k_wau
        mau_calibrated = mau_prime * k_mau
        
        print(f"\n🎯 Calibrated Metrics:")
        print(f"   DAU: {dau_calibrated:,.0f}")
        print(f"   WAU: {wau_calibrated:,.0f}")
        print(f"   MAU: {mau_calibrated:,.0f}")
        print(f"   DAU/MAU Ratio: {dau_calibrated/mau_calibrated:.1%}")
        
        # Save comprehensive report
        report = {
            'generated_at': datetime.now().isoformat(),
            'date': date,
            'raw_metrics': {
                'total_activities': total_activities,
                'dau_prime': dau_prime,
                'wau_prime': wau_prime,
                'mau_prime': mau_prime,
                'unique_subreddits': unique_subreddits,
                'categories_covered': categories_covered,
                'collection_efficiency': collection_efficiency
            },
            'calibrated_metrics': {
                'dau': dau_calibrated,
                'wau': wau_calibrated,
                'mau': mau_calibrated
            },
            'category_breakdown': [
                {'category': cat, 'activities': act, 'authors': auth, 'subreddits': sub}
                for cat, act, auth, sub in category_breakdown
            ]
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_dau_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n💾 Comprehensive report saved to: {filename}")
        
        return report
    
    def run_comprehensive_analysis(self):
        """Run the complete comprehensive DAU analysis."""
        print("🚀 Starting Comprehensive Reddit DAU Analysis")
        print("=" * 70)
        
        # Step 1: Collect comprehensive data
        collection_results = self.collect_comprehensive_data(days_back=1)
        
        # Step 2: Generate comprehensive report
        report = self.generate_comprehensive_report()
        
        print(f"\n✅ Comprehensive DAU Analysis Complete!")
        print(f"📊 System Status: OPERATIONAL")
        print(f"👥 Raw DAU′: {collection_results['unique_authors']:,}")
        print(f"📈 Activities: {collection_results['total_activities']:,}")
        print(f"📱 Subreddits: {collection_results['unique_subreddits']:,}")
        
        return {
            'collection_results': collection_results,
            'report': report
        }

def main():
    """Main function to run comprehensive DAU analysis."""
    estimator = ComprehensiveDAUEstimator()
    
    try:
        results = estimator.run_comprehensive_analysis()
        
        print(f"\n🎉 Comprehensive DAU Analysis Complete!")
        print(f"📊 Raw DAU′: {results['collection_results']['unique_authors']:,}")
        print(f"📈 Total Activities: {results['collection_results']['total_activities']:,}")
        print(f"📱 Subreddits Covered: {results['collection_results']['unique_subreddits']:,}")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        return None

if __name__ == "__main__":
    main()
