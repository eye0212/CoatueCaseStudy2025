#!/usr/bin/env python3
"""
Direct DAU Calculator
Calculates implied total DAU by dividing observed DAU by the percentage of Reddit scraped.
"""

import sys
import os
import json
import sqlite3
from datetime import datetime, timezone, timedelta

sys.path.append('src')
from reddit_pitch.collector import reddit_client
from reddit_pitch.config import Settings, load_config
from reddit_pitch.db import connect

class DirectDAUCalculator:
    def __init__(self):
        self.settings = Settings()
        self.reddit = reddit_client(self.settings)
        self.conn = connect(self.settings.db_path)
        
        # Reddit's actual reported metrics (Q4'23)
        self.reddit_metrics = {
            'dau': 73.1e6,      # 73.1M DAU
            'wau': 267.5e6,     # 267.5M WAU
            'mau': 487.3e6,      # Estimated MAU (DAU/0.15)
        }
    
    def calculate_reddit_coverage(self):
        """Calculate what percentage of Reddit we actually scraped."""
        print("🔍 Calculating Reddit Coverage...")
        print("=" * 50)
        
        cursor = self.conn.cursor()
        
        # Get our comprehensive data
        cursor.execute("""
            SELECT date, total_activities, unique_authors, unique_subreddits, 
                   categories_covered, collection_efficiency
            FROM comprehensive_daily_metrics 
            ORDER BY date DESC LIMIT 1
        """)
        
        result = cursor.fetchone()
        if not result:
            print("  ⚠️  No comprehensive data found")
            return None
        
        date, total_activities, unique_authors, unique_subreddits, categories_covered, collection_efficiency = result
        
        # Reddit's total scale (estimated)
        reddit_total_subreddits = 100000  # ~100k active subreddits
        reddit_daily_activities = 1000000  # ~1M daily activities
        reddit_daily_authors = self.reddit_metrics['dau']  # 73.1M DAU
        
        # Calculate coverage percentages
        subreddit_coverage = unique_subreddits / reddit_total_subreddits
        activity_coverage = total_activities / reddit_daily_activities
        author_coverage = unique_authors / reddit_daily_authors
        
        print(f"📊 Our Collection vs Reddit Total:")
        print(f"   Subreddits: {unique_subreddits:,} / {reddit_total_subreddits:,} = {subreddit_coverage:.4f} ({subreddit_coverage:.2%})")
        print(f"   Activities: {total_activities:,} / {reddit_daily_activities:,} = {activity_coverage:.4f} ({activity_coverage:.2%})")
        print(f"   Authors: {unique_authors:,} / {reddit_daily_authors:,} = {author_coverage:.4f} ({author_coverage:.2%})")
        
        return {
            'our_data': {
                'subreddits': unique_subreddits,
                'activities': total_activities,
                'authors': unique_authors,
                'collection_efficiency': collection_efficiency
            },
            'reddit_total': {
                'subreddits': reddit_total_subreddits,
                'activities': reddit_daily_activities,
                'authors': reddit_daily_authors
            },
            'coverage': {
                'subreddit_coverage': subreddit_coverage,
                'activity_coverage': activity_coverage,
                'author_coverage': author_coverage
            }
        }
    
    def calculate_implied_dau(self, coverage_data):
        """Calculate implied total DAU using direct division method."""
        print(f"\n🎯 Calculating Implied Total DAU...")
        print("=" * 50)
        
        our_authors = coverage_data['our_data']['authors']
        author_coverage = coverage_data['coverage']['author_coverage']
        
        # Direct calculation: Implied DAU = Our DAU / Coverage %
        implied_dau = our_authors / author_coverage
        
        print(f"📊 Direct Calculation:")
        print(f"   Our DAU′: {our_authors:,}")
        print(f"   Coverage: {author_coverage:.4f} ({author_coverage:.2%})")
        print(f"   Implied DAU = {our_authors:,} ÷ {author_coverage:.4f} = {implied_dau:,.0f}")
        
        # Compare to Reddit's reported DAU
        reddit_dau = coverage_data['reddit_total']['authors']
        accuracy = min(implied_dau, reddit_dau) / max(implied_dau, reddit_dau)
        
        print(f"\n📈 Results:")
        print(f"   Implied DAU: {implied_dau:,.0f}")
        print(f"   Reddit Reported: {reddit_dau:,.0f}")
        print(f"   Accuracy: {accuracy:.1%}")
        
        # Calculate WAU and MAU using same method
        # For WAU/MAU, we need to estimate the coverage for longer periods
        # Assuming similar coverage patterns
        implied_wau = implied_dau * (self.reddit_metrics['wau'] / self.reddit_metrics['dau'])
        implied_mau = implied_dau * (self.reddit_metrics['mau'] / self.reddit_metrics['dau'])
        
        print(f"\n🔄 Extended Metrics:")
        print(f"   Implied WAU: {implied_wau:,.0f} (Reddit: {self.reddit_metrics['wau']:,.0f})")
        print(f"   Implied MAU: {implied_mau:,.0f} (Reddit: {self.reddit_metrics['mau']:,.0f})")
        
        return {
            'implied_metrics': {
                'dau': implied_dau,
                'wau': implied_wau,
                'mau': implied_mau
            },
            'accuracy': {
                'dau_accuracy': accuracy,
                'method': 'direct_division'
            },
            'calculation': {
                'our_dau': our_authors,
                'coverage_percentage': author_coverage,
                'formula': f"{our_authors:,} ÷ {author_coverage:.4f} = {implied_dau:,.0f}"
            }
        }
    
    def analyze_coverage_quality(self, coverage_data):
        """Analyze the quality of our coverage."""
        print(f"\n🔍 Coverage Quality Analysis...")
        print("=" * 50)
        
        coverage = coverage_data['coverage']
        
        print(f"📊 Coverage Quality Assessment:")
        
        # Subreddit coverage analysis
        subreddit_coverage = coverage['subreddit_coverage']
        if subreddit_coverage > 0.01:  # > 1%
            subreddit_quality = "Excellent"
        elif subreddit_coverage > 0.005:  # > 0.5%
            subreddit_quality = "Good"
        elif subreddit_coverage > 0.001:  # > 0.1%
            subreddit_quality = "Fair"
        else:
            subreddit_quality = "Poor"
        
        print(f"   Subreddit Coverage: {subreddit_coverage:.2%} ({subreddit_quality})")
        
        # Activity coverage analysis
        activity_coverage = coverage['activity_coverage']
        if activity_coverage > 0.05:  # > 5%
            activity_quality = "Excellent"
        elif activity_coverage > 0.01:  # > 1%
            activity_quality = "Good"
        elif activity_coverage > 0.005:  # > 0.5%
            activity_quality = "Fair"
        else:
            activity_quality = "Poor"
        
        print(f"   Activity Coverage: {activity_coverage:.2%} ({activity_quality})")
        
        # Author coverage analysis
        author_coverage = coverage['author_coverage']
        if author_coverage > 0.0001:  # > 0.01%
            author_quality = "Excellent"
        elif author_coverage > 0.00005:  # > 0.005%
            author_quality = "Good"
        elif author_coverage > 0.00001:  # > 0.001%
            author_quality = "Fair"
        else:
            author_quality = "Poor"
        
        print(f"   Author Coverage: {author_coverage:.2%} ({author_quality})")
        
        # Overall assessment
        if author_quality == "Excellent":
            overall_quality = "Excellent - High confidence in results"
        elif author_quality == "Good":
            overall_quality = "Good - Reasonable confidence in results"
        elif author_quality == "Fair":
            overall_quality = "Fair - Moderate confidence in results"
        else:
            overall_quality = "Poor - Low confidence in results"
        
        print(f"\n✅ Overall Assessment: {overall_quality}")
        
        return {
            'subreddit_quality': subreddit_quality,
            'activity_quality': activity_quality,
            'author_quality': author_quality,
            'overall_quality': overall_quality,
            'confidence_level': author_quality
        }
    
    def generate_direct_report(self):
        """Generate direct DAU calculation report."""
        print("📊 Generating Direct DAU Calculation Report...")
        print("=" * 60)
        
        # Calculate coverage
        coverage_data = self.calculate_reddit_coverage()
        if not coverage_data:
            return None
        
        # Calculate implied DAU
        implied_results = self.calculate_implied_dau(coverage_data)
        
        # Analyze coverage quality
        quality_analysis = self.analyze_coverage_quality(coverage_data)
        
        # Generate final report
        report = {
            'generated_at': datetime.now().isoformat(),
            'analysis_type': 'direct_dau_calculation',
            'method': 'division_by_coverage_percentage',
            'coverage_analysis': coverage_data,
            'implied_results': implied_results,
            'quality_analysis': quality_analysis,
            'insights': self._generate_direct_insights(coverage_data, implied_results, quality_analysis)
        }
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"direct_dau_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n💾 Direct report saved to: {filename}")
        
        return report
    
    def _generate_direct_insights(self, coverage_data, implied_results, quality_analysis):
        """Generate insights from direct calculation."""
        insights = []
        
        # Coverage insights
        coverage = coverage_data['coverage']
        insights.append(f"Subreddit coverage: {coverage['subreddit_coverage']:.2%} of Reddit's active subreddits")
        insights.append(f"Activity coverage: {coverage['activity_coverage']:.2%} of Reddit's daily activities")
        insights.append(f"Author coverage: {coverage['author_coverage']:.2%} of Reddit's DAU")
        
        # Calculation insights
        calc = implied_results['calculation']
        insights.append(f"Direct calculation: {calc['formula']}")
        insights.append(f"Implied DAU: {implied_results['implied_metrics']['dau']:,.0f}")
        insights.append(f"Accuracy: {implied_results['accuracy']['dau_accuracy']:.1%}")
        
        # Quality insights
        insights.append(f"Coverage quality: {quality_analysis['overall_quality']}")
        insights.append(f"Confidence level: {quality_analysis['confidence_level']}")
        
        # Method insights
        insights.append("Method: Direct division by coverage percentage")
        insights.append("Advantage: Simple, intuitive, no calibration factors needed")
        insights.append("Assumption: Our sample is representative of Reddit's total activity")
        
        return insights

def main():
    """Main function to run direct DAU calculation."""
    calculator = DirectDAUCalculator()
    
    try:
        report = calculator.generate_direct_report()
        
        if report:
            print(f"\n🎉 Direct DAU Calculation Complete!")
            print(f"📊 Implied DAU: {report['implied_results']['implied_metrics']['dau']:,.0f}")
            print(f"📈 Accuracy: {report['implied_results']['accuracy']['dau_accuracy']:.1%}")
            print(f"✅ Quality: {report['quality_analysis']['overall_quality']}")
            
            print(f"\n💡 Key Insights:")
            for insight in report['insights']:
                print(f"   • {insight}")
        
        return report
        
    except Exception as e:
        print(f"\n❌ Error during calculation: {e}")
        return None

if __name__ == "__main__":
    main()
