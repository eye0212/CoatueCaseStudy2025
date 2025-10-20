#!/usr/bin/env python3
"""
Reddit DAU Monitoring System
Comprehensive monitoring, quality controls, and reporting for DAU/WAU/MAU tracking.
"""

import sys
import os
import time
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional
import matplotlib.pyplot as plt
import pandas as pd

sys.path.append('src')
from reddit_pitch.collector import reddit_client
from reddit_pitch.config import Settings, load_config
from reddit_pitch.db import connect

class RedditDAUMonitor:
    def __init__(self):
        self.settings = Settings()
        self.reddit = reddit_client(self.settings)
        self.conn = connect(self.settings.db_path)
        
        # Quality control thresholds
        self.quality_thresholds = {
            'min_daily_activities': 1000,
            'max_author_ratio': 0.5,  # Max ratio of single-day authors
            'min_panel_coverage': 0.8,  # Min % of panel subreddits with data
            'max_api_error_rate': 0.1  # Max % of API errors
        }
    
    def run_quality_controls(self, target_date=None):
        """Run comprehensive quality controls on the tracking system."""
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()
        
        print(f"🔍 Running Quality Controls for {target_date}...")
        print("=" * 50)
        
        quality_report = {
            'date': target_date.isoformat(),
            'checks': {},
            'overall_status': 'PASS',
            'recommendations': []
        }
        
        # Check 1: Data Coverage
        coverage_check = self._check_data_coverage(target_date)
        quality_report['checks']['data_coverage'] = coverage_check
        
        # Check 2: Author Distribution
        author_check = self._check_author_distribution(target_date)
        quality_report['checks']['author_distribution'] = author_check
        
        # Check 3: API Performance
        api_check = self._check_api_performance(target_date)
        quality_report['checks']['api_performance'] = api_check
        
        # Check 4: Engagement Patterns
        engagement_check = self._check_engagement_patterns(target_date)
        quality_report['checks']['engagement_patterns'] = engagement_check
        
        # Overall assessment
        failed_checks = [check for check in quality_report['checks'].values() if not check['status']]
        if failed_checks:
            quality_report['overall_status'] = 'FAIL'
            quality_report['recommendations'].extend([check['recommendation'] for check in failed_checks])
        
        # Generate recommendations
        self._generate_recommendations(quality_report)
        
        # Save quality report
        self._save_quality_report(quality_report)
        
        print(f"\n✅ Quality Control Summary:")
        print(f"   Status: {quality_report['overall_status']}")
        print(f"   Checks Passed: {len([c for c in quality_report['checks'].values() if c['status']])}/{len(quality_report['checks'])}")
        
        if quality_report['recommendations']:
            print(f"   Recommendations:")
            for rec in quality_report['recommendations']:
                print(f"     • {rec}")
        
        return quality_report
    
    def _check_data_coverage(self, target_date):
        """Check data coverage across the tracking panel."""
        cursor = self.conn.cursor()
        
        # Get total subreddits in panel
        cursor.execute("SELECT COUNT(*) FROM tracking_panel WHERE is_active = 1")
        total_panel = cursor.fetchone()[0]
        
        # Get subreddits with data for target date
        cursor.execute("""
            SELECT COUNT(DISTINCT subreddit) FROM daily_activity 
            WHERE date = ?
        """, (target_date.isoformat(),))
        covered_subreddits = cursor.fetchone()[0]
        
        coverage_ratio = covered_subreddits / total_panel if total_panel > 0 else 0
        
        status = coverage_ratio >= self.quality_thresholds['min_panel_coverage']
        
        return {
            'status': status,
            'coverage_ratio': coverage_ratio,
            'covered_subreddits': covered_subreddits,
            'total_panel': total_panel,
            'recommendation': f"Increase polling frequency" if not status else "Coverage adequate"
        }
    
    def _check_author_distribution(self, target_date):
        """Check author distribution patterns."""
        cursor = self.conn.cursor()
        
        # Get author activity patterns
        cursor.execute("""
            SELECT author, COUNT(*) as activity_count
            FROM daily_activity 
            WHERE date = ? AND author NOT IN ('AutoModerator', '[deleted]', '[removed]', 'None', '')
            GROUP BY author
        """, (target_date.isoformat(),))
        
        author_activities = cursor.fetchall()
        total_authors = len(author_activities)
        
        if total_authors == 0:
            return {
                'status': False,
                'single_day_authors': 0,
                'total_authors': 0,
                'recommendation': "No author data found - check data collection"
            }
        
        # Count single-day authors (authors with only 1 activity)
        single_day_authors = len([a for a in author_activities if a[1] == 1])
        single_day_ratio = single_day_authors / total_authors
        
        status = single_day_ratio <= self.quality_thresholds['max_author_ratio']
        
        return {
            'status': status,
            'single_day_authors': single_day_authors,
            'total_authors': total_authors,
            'single_day_ratio': single_day_ratio,
            'recommendation': f"High single-day author ratio ({single_day_ratio:.1%}) - check for spam" if not status else "Author distribution healthy"
        }
    
    def _check_api_performance(self, target_date):
        """Check API performance and error rates."""
        cursor = self.conn.cursor()
        
        # Get total API calls attempted
        cursor.execute("SELECT COUNT(*) FROM tracking_panel WHERE is_active = 1")
        total_attempts = cursor.fetchone()[0]
        
        # Get successful data collections
        cursor.execute("""
            SELECT COUNT(DISTINCT subreddit) FROM daily_activity 
            WHERE date = ?
        """, (target_date.isoformat(),))
        successful_calls = cursor.fetchone()[0]
        
        error_rate = 1 - (successful_calls / total_attempts) if total_attempts > 0 else 1
        
        status = error_rate <= self.quality_thresholds['max_api_error_rate']
        
        return {
            'status': status,
            'error_rate': error_rate,
            'successful_calls': successful_calls,
            'total_attempts': total_attempts,
            'recommendation': f"High API error rate ({error_rate:.1%}) - check API limits" if not status else "API performance adequate"
        }
    
    def _check_engagement_patterns(self, target_date):
        """Check engagement patterns for anomalies."""
        cursor = self.conn.cursor()
        
        # Get daily activity counts
        cursor.execute("""
            SELECT COUNT(*) as total_activities, 
                   COUNT(CASE WHEN activity_type = 'post' THEN 1 END) as posts,
                   COUNT(CASE WHEN activity_type = 'comment' THEN 1 END) as comments
            FROM daily_activity 
            WHERE date = ?
        """, (target_date.isoformat(),))
        
        result = cursor.fetchone()
        total_activities, posts, comments = result
        
        status = total_activities >= self.quality_thresholds['min_daily_activities']
        
        return {
            'status': status,
            'total_activities': total_activities,
            'posts': posts,
            'comments': comments,
            'recommendation': f"Low activity count ({total_activities}) - check data collection" if not status else "Engagement levels adequate"
        }
    
    def _generate_recommendations(self, quality_report):
        """Generate actionable recommendations based on quality checks."""
        recommendations = []
        
        # Coverage recommendations
        coverage = quality_report['checks']['data_coverage']
        if coverage['coverage_ratio'] < 0.9:
            recommendations.append(f"Increase polling frequency to improve coverage ({coverage['coverage_ratio']:.1%})")
        
        # API performance recommendations
        api_perf = quality_report['checks']['api_performance']
        if api_perf['error_rate'] > 0.05:
            recommendations.append(f"Optimize API calls to reduce error rate ({api_perf['error_rate']:.1%})")
        
        # Author distribution recommendations
        author_dist = quality_report['checks']['author_distribution']
        if author_dist.get('single_day_ratio', 0) > 0.4:
            recommendations.append("Review subreddit panel for spam/quality issues")
        
        quality_report['recommendations'].extend(recommendations)
    
    def _save_quality_report(self, quality_report):
        """Save quality control report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quality_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(quality_report, f, indent=2, default=str)
        
        print(f"💾 Quality report saved to: {filename}")
    
    def generate_trend_analysis(self, days=30):
        """Generate trend analysis for DAU/WAU/MAU metrics."""
        print(f"📈 Generating Trend Analysis ({days} days)...")
        print("=" * 50)
        
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days-1)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT date, dau_prime, wau_prime, mau_prime, total_posts, total_comments
            FROM daily_unique_authors 
            WHERE date >= ? AND date <= ?
            ORDER BY date
        """, (start_date.isoformat(), end_date.isoformat()))
        
        daily_data = cursor.fetchall()
        
        if not daily_data:
            print("  ⚠️  No data available for trend analysis")
            return None
        
        # Calculate trends
        dau_values = [row[1] for row in daily_data]
        wau_values = [row[2] for row in daily_data]
        mau_values = [row[3] for row in daily_data]
        
        # Calculate growth rates
        dau_growth = ((dau_values[-1] - dau_values[0]) / dau_values[0] * 100) if dau_values[0] > 0 else 0
        wau_growth = ((wau_values[-1] - wau_values[0]) / wau_values[0] * 100) if wau_values[0] > 0 else 0
        mau_growth = ((mau_values[-1] - mau_values[0]) / mau_values[0] * 100) if mau_values[0] > 0 else 0
        
        # Calculate averages
        avg_dau = sum(dau_values) / len(dau_values)
        avg_wau = sum(wau_values) / len(wau_values)
        avg_mau = sum(mau_values) / len(mau_values)
        
        # Calculate volatility
        dau_volatility = self._calculate_volatility(dau_values)
        wau_volatility = self._calculate_volatility(wau_values)
        mau_volatility = self._calculate_volatility(mau_values)
        
        trend_analysis = {
            'period': f"{start_date} to {end_date}",
            'days_analyzed': len(daily_data),
            'metrics': {
                'dau_prime': {
                    'average': avg_dau,
                    'growth_rate': dau_growth,
                    'volatility': dau_volatility,
                    'current': dau_values[-1],
                    'trend': 'increasing' if dau_growth > 0 else 'decreasing'
                },
                'wau_prime': {
                    'average': avg_wau,
                    'growth_rate': wau_growth,
                    'volatility': wau_volatility,
                    'current': wau_values[-1],
                    'trend': 'increasing' if wau_growth > 0 else 'decreasing'
                },
                'mau_prime': {
                    'average': avg_mau,
                    'growth_rate': mau_growth,
                    'volatility': mau_volatility,
                    'current': mau_values[-1],
                    'trend': 'increasing' if mau_growth > 0 else 'decreasing'
                }
            }
        }
        
        # Print trend analysis
        print(f"\n📊 TREND ANALYSIS RESULTS:")
        print(f"   Period: {trend_analysis['period']}")
        print(f"   Days Analyzed: {trend_analysis['days_analyzed']}")
        
        for metric, data in trend_analysis['metrics'].items():
            print(f"\n   {metric.upper()}:")
            print(f"     Current: {data['current']:,.0f}")
            print(f"     Average: {data['average']:,.0f}")
            print(f"     Growth: {data['growth_rate']:+.1f}%")
            print(f"     Volatility: {data['volatility']:.2f}")
            print(f"     Trend: {data['trend']}")
        
        # Save trend analysis
        self._save_trend_analysis(trend_analysis)
        
        return trend_analysis
    
    def _calculate_volatility(self, values):
        """Calculate volatility (standard deviation) of a series."""
        if len(values) < 2:
            return 0
        
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _save_trend_analysis(self, trend_analysis):
        """Save trend analysis to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trend_analysis_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(trend_analysis, f, indent=2, default=str)
        
        print(f"💾 Trend analysis saved to: {filename}")
    
    def generate_comprehensive_report(self, days=30):
        """Generate comprehensive DAU monitoring report."""
        print(f"📊 Generating Comprehensive DAU Report ({days} days)...")
        print("=" * 60)
        
        # Run quality controls
        quality_report = self.run_quality_controls()
        
        # Generate trend analysis
        trend_analysis = self.generate_trend_analysis(days)
        
        # Generate final report
        comprehensive_report = {
            'generated_at': datetime.now().isoformat(),
            'analysis_period_days': days,
            'quality_controls': quality_report,
            'trend_analysis': trend_analysis,
            'system_status': 'HEALTHY' if quality_report['overall_status'] == 'PASS' else 'NEEDS_ATTENTION'
        }
        
        # Save comprehensive report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_dau_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(comprehensive_report, f, indent=2, default=str)
        
        print(f"\n✅ Comprehensive Report Generated!")
        print(f"   System Status: {comprehensive_report['system_status']}")
        print(f"   Quality Controls: {quality_report['overall_status']}")
        print(f"   Report saved to: {filename}")
        
        return comprehensive_report

def main():
    """Main function to run the DAU monitoring system."""
    monitor = RedditDAUMonitor()
    
    try:
        # Run comprehensive monitoring
        report = monitor.generate_comprehensive_report(days=7)  # 7 days for testing
        
        print(f"\n🎉 DAU Monitoring Complete!")
        print(f"📊 System Status: {report['system_status']}")
        
        return report
        
    except Exception as e:
        print(f"\n❌ Error during monitoring: {e}")
        return None

if __name__ == "__main__":
    main()
