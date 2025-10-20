#!/usr/bin/env python3
"""
Simple test script to verify Reddit API credentials are working.
Run this after setting up your .env file with Reddit credentials.
"""

import os
from dotenv import load_dotenv
import praw

# Load environment variables
load_dotenv()

def test_reddit_connection():
    """Test Reddit API connection with user credentials."""
    
    # Get credentials from environment
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "reddit-pitch-kit/1.0")
    
    # Check if credentials are set
    if not client_id or client_id == "your_actual_client_id_here":
        print("❌ REDDIT_CLIENT_ID not set in .env file")
        return False
        
    if not client_secret or client_secret == "your_actual_client_secret_here":
        print("❌ REDDIT_CLIENT_SECRET not set in .env file")
        return False
    
    print(f"🔑 Using Client ID: {client_id[:8]}...")
    print(f"🤖 User Agent: {user_agent}")
    
    try:
        # Create Reddit client
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        
        # Test connection by getting a simple subreddit
        subreddit = reddit.subreddit("test")
        print(f"✅ Successfully connected to Reddit API")
        print(f"📊 Test subreddit 'test' has {subreddit.subscribers:,} subscribers")
        
        # Test getting a few popular subreddits
        print("\n🔍 Testing popular subreddits access...")
        popular_subs = list(reddit.subreddits.popular(limit=3))
        for sub in popular_subs:
            print(f"  - r/{sub.display_name}: {sub.subscribers:,} subscribers")
        
        print("\n🎉 Reddit API setup is working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to Reddit API: {e}")
        print("\n💡 Troubleshooting tips:")
        print("  1. Check your .env file has correct REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")
        print("  2. Verify your Reddit app is set up as 'script' type")
        print("  3. Make sure your user agent includes your Reddit username")
        return False

if __name__ == "__main__":
    print("🚀 Testing Reddit API Connection...")
    print("=" * 50)
    test_reddit_connection()
