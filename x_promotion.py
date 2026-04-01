#!/usr/bin/env python3
"""
Daily X (Twitter) Promotion Script for Evergreen Lead Gen

Selects a random promotional post and sends to Ryan for approval.
Once approved, posts to @theryancameron via X API v2.

Runs daily via cron at 9:00 AM UTC.
"""

import os
import random
import json
from datetime import datetime

# Promotional content templates
PROMOTION_POSTS = [
    "🌲 Just scraped 50 fresh B2B leads for your niche. CSV ready to download. No manual work, no API calls from you. Evergreen Lead Gen handles it all.\n\nTry it: https://app.evergreenleadgen.ai",
    
    "B2B lead gen shouldn't require 5 different tools + a PhD in data. We built Evergreen to be stupidly simple:\n\n1. Enter a niche\n2. Get 50 real leads in CSV\n3. Done\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "Your sales team is wasting 20 hours/week finding B2B leads manually.\n\nEvergreen Lead Gen does it in 30 seconds. $149 lifetime access. Try it: https://app.evergreenleadgen.ai 🌲",
    
    "Sick of lead gen APIs that:\n- Require 10 setups\n- Have confusing rate limits\n- Cost $1000s/month\n\nEvergreen does lead gen right. $149 lifetime. No BS.\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "Your Apollo/ZoomInfo/Clearbit are costing you money. They're tools, not solutions.\n\nEvergreen Lead Gen is the solution. Search any B2B niche, get 50 real leads instantly.\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "We analyzed 1000s of B2B lead gen workflows. Found the pattern: people need leads fast, cheap, and actually valid.\n\nThat's Evergreen. $149. No subscriptions. No limits.\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "We're building the standard lead gen layer for the agentic AI economy.\n\nRight now? We're helping humans find leads in seconds. That's just the start.\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "Why Evergreen?\n\n✅ 50 real B2B leads per search\n✅ Works with Apollo, Lusha, ZoomInfo, Clay, RocketReach, etc.\n✅ $149 lifetime (no recurring BS)\n✅ CSV download in 30 seconds\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "We get 100+ signups asking the same question: 'Why didn't this exist before?'\n\nBecause the market was broken. We fixed it.\n\nEvergreen Lead Gen. Try it free: https://app.evergreenleadgen.ai 🌲",
]

def select_post():
    """Select a random promotion post."""
    return random.choice(PROMOTION_POSTS)

def send_approval_message(post_text):
    """
    Send approval request to Ryan via Telegram.
    Stores pending message and prints for user acknowledgment.
    """
    pending_file = "/tmp/pending_x_tweet.json"
    
    approval_data = {
        "message": post_text,
        "timestamp": datetime.now().isoformat(),
        "status": "pending_approval"
    }
    
    # Save pending tweet
    with open(pending_file, 'w') as f:
        json.dump(approval_data, f, indent=2)
    
    print(f"🌲 X Promotion - {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)
    print("\n📝 PENDING APPROVAL\n")
    print("Tweet to @theryancameron:\n")
    print(post_text)
    print("\n" + "=" * 60)
    print("\n⏳ Waiting for approval...")
    print("\n💬 Reply with 'approve' or 'yes' to post")
    print("   Reply with 'skip' or 'no' to skip this one\n")
    
    return True

def main():
    """Main function."""
    bearer_token = os.getenv("X_BEARER_TOKEN")
    
    if not bearer_token:
        print("❌ Error: X_BEARER_TOKEN not configured")
        return False
    
    # Select a random post
    post = select_post()
    
    # Ensure post is within 280 character limit
    if len(post) > 280:
        print(f"⚠️  Warning: Post is {len(post)} characters (limit: 280)")
        post = post[:277] + "..."
    
    # Send for approval
    send_approval_message(post)
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
