#!/usr/bin/env python3
"""
Daily X (Twitter) Promotion Script for Evergreen Lead Gen

Posts daily organic promotional content about Evergreen Lead Gen
to @theryancameron. Uses the X API v2 with Bearer token authentication.

Runs daily via cron. Set to run at 9:00 AM UTC.
"""

import os
import random
import requests
from datetime import datetime

# X API Configuration
BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
X_API_ENDPOINT = "https://api.x.com/2/tweets"

# Promotional content templates
PROMOTION_POSTS = [
    "🌲 Just scraped 50 fresh B2B leads for {niche}. CSV ready to download. No manual work, no API calls from you. Evergreen Lead Gen handles it all.\n\nTry it: https://app.evergreenleadgen.ai",
    
    "B2B lead gen shouldn't require 5 different tools + a PhD in data. We built Evergreen to be stupidly simple:\n\n1. Enter a niche\n2. Get 50 real leads in CSV\n3. Done\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "Your sales team is wasting 20 hours/week finding B2B leads manually.\n\nEvergreen Lead Gen does it in 30 seconds. $149 lifetime access. Try it: https://app.evergreenleadgen.ai 🌲",
    
    "Sick of lead gen APIs that:\n- Require 10 setups\n- Have confusing rate limits\n- Cost $1000s/month\n\nEvergreen does lead gen right. $149 lifetime. No BS.\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "Your Apollo/ZoomInfo/Clearbit are costing you money. They're tools, not solutions.\n\nEvergreen Lead Gen is the solution. Search any B2B niche, get 50 real leads instantly.\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "We analyzed 1000s of B2B lead gen workflows. Found the pattern: people need leads fast, cheap, and actually valid.\n\nThat's Evergreen. $149. No subscriptions. No limits.\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "We're building the standard lead gen layer for the agentic AI economy.\n\nRight now? We're helping humans find leads in seconds. That's just the start.\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "Why Evergreen?\n\n✅ 50 real B2B leads per search\n✅ Works with Apollo, Lusha, ZoomInfo, Clay, RocketReach, etc.\n✅ $149 lifetime (no recurring BS)\n✅ CSV download in 30 seconds\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "We get 100+ signups asking the same question: 'Why didn't this exist before?'\n\nBecause the market was broken. We fixed it.\n\nEvergreen Lead Gen. Try it free: https://app.evergreenleadgen.ai 🌲",
]

def get_auth_header():
    """Return the Authorization header with Bearer token."""
    return {"Authorization": f"Bearer {BEARER_TOKEN}"}

def post_to_x(text):
    """
    Post a tweet to X using the v2 API.
    
    Args:
        text (str): The tweet text (max 280 characters)
    
    Returns:
        dict: Response from X API
    """
    if not BEARER_TOKEN:
        print("❌ Error: X_BEARER_TOKEN environment variable not set")
        return None
    
    payload = {"text": text}
    headers = get_auth_header()
    headers["Content-Type"] = "application/json"
    
    try:
        response = requests.post(
            X_API_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            tweet_id = data.get("data", {}).get("id")
            print(f"✅ Tweet posted successfully! ID: {tweet_id}")
            print(f"   Text: {text[:50]}...")
            return data
        else:
            print(f"❌ Failed to post tweet: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None

def main():
    """Main function: Select a random promotion post and send it."""
    print(f"🌲 Evergreen Lead Gen - Daily X Promotion ({datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')})")
    print("=" * 60)
    
    if not BEARER_TOKEN:
        print("❌ Error: X_BEARER_TOKEN not configured in Railway environment variables")
        return False
    
    # Select a random post from the pool
    post = random.choice(PROMOTION_POSTS)
    
    # Handle any niche placeholder (though our posts don't use it currently)
    if "{niche}" in post:
        post = post.format(niche="your industry")
    
    # Ensure post is within 280 character limit
    if len(post) > 280:
        print(f"⚠️  Warning: Post is {len(post)} characters (limit: 280)")
        print(f"   Truncating...")
        post = post[:277] + "..."
    
    print(f"📝 Posting: {post}")
    print()
    
    # Post to X
    result = post_to_x(post)
    
    if result:
        print("✅ Promotion routine complete")
        return True
    else:
        print("❌ Promotion routine failed")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
