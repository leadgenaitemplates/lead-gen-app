#!/usr/bin/env python3
"""
Post Approved X Tweet

Called after Ryan approves a pending X promotion tweet.
Reads the pending tweet from /tmp/pending_x_tweet.json and posts to @theryancameron.
"""

import os
import json
import requests
from datetime import datetime

X_API_ENDPOINT = "https://api.x.com/2/tweets"
PENDING_FILE = "/tmp/pending_x_tweet.json"

def get_pending_tweet():
    """Read pending tweet from file."""
    try:
        with open(PENDING_FILE, 'r') as f:
            data = json.load(f)
            return data.get("message")
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

def post_to_x(text, bearer_token):
    """
    Post a tweet to X using v2 API.
    
    Args:
        text (str): Tweet text
        bearer_token (str): X API Bearer token
    
    Returns:
        dict: X API response
    """
    payload = {"text": text}
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
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
            print(f"✅ Tweet posted to @theryancameron!")
            print(f"   Tweet ID: {tweet_id}")
            print(f"   Text: {text[:60]}...")
            return data
        else:
            print(f"❌ Failed to post: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None

def main():
    """Post the approved tweet."""
    print(f"🌲 X Post Approved - {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)
    
    bearer_token = os.getenv("X_BEARER_TOKEN")
    
    if not bearer_token:
        print("❌ Error: X_BEARER_TOKEN not configured")
        return False
    
    # Get pending tweet
    post_text = get_pending_tweet()
    
    if not post_text:
        print("❌ No pending tweet found. Run x_promotion.py first to generate approval request.")
        return False
    
    print(f"\n📝 Posting approved tweet:\n")
    print(post_text)
    print("\n")
    
    # Post to X
    result = post_to_x(post_text, bearer_token)
    
    if result:
        # Clean up pending file
        try:
            os.remove(PENDING_FILE)
        except:
            pass
        
        print("\n✅ Done!")
        return True
    else:
        print("\n❌ Failed to post tweet")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
