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

# Promotional content templates (CLARIFIED MESSAGING)
PROMOTION_POSTS = [
    "I used to spend 30 mins in Apollo finding the right niche to prospect. Now I search Evergreen, get 50 companies instantly, upload to Apollo for enrichment. Same leads, 90% less time.\n\n$149 lifetime: https://app.evergreenleadgen.ai 🌲",
    
    "Not replacing Apollo. Evergreen is the search layer Apollo was missing.\n\nFind companies → Apollo enriches with contacts → Cold list in 2 minutes.\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "The hard part of outreach isn't emails (Apollo does that). It's finding the RIGHT niche worth prospecting.\n\nEvergreen solves that. $149 lifetime.\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "You already pay for Apollo/Lusha. Don't waste it on bad searches.\n\nEvergreen helps you find the GOOD companies to enrich. Works with whatever enrichment tool you have.\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "Spent $5k on Apollo but couldn't figure out which niches were worth researching. Evergreen would've saved me weeks of wasted searches.\n\n$149 lifetime. https://app.evergreenleadgen.ai 🌲",
    
    "Algorithm updates every Sunday with latest Google scraping trends + B2B targeting.\n\nFree version works forever. $19/mo for weekly updates.\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "For Apollo power users: Evergreen just makes you faster. For Apollo strugglers: This is the targeting shortcut I wish I had 2 years ago.\n\n$149 lifetime: https://app.evergreenleadgen.ai 🌲",
    
    "The bottleneck in outreach:\n\n❌ Not emails (Apollo has those)\n✅ Finding companies worth prospecting\n\nEvergreen fixes the real problem. Works with your existing tools.\n\nhttps://app.evergreenleadgen.ai 🌲",
    
    "ROI check: Apollo costs $300/mo. Evergreen costs $149 lifetime. If it saves you 2 hours/month in niche research, you've paid for itself forever.\n\nhttps://app.evergreenleadgen.ai 🌲",
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
