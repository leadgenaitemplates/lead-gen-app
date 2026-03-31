#!/usr/bin/env python3
"""
Revenue Tracker for Evergreen Lead Gen

Pulls data from Stripe API to track daily/weekly revenue.
Displays:
- Total revenue (all time)
- Today's revenue
- This week's revenue
- Average daily revenue
- Upcoming subscriptions

Stores summary in PostgreSQL for historical tracking.
"""

import os
import json
from datetime import datetime, timedelta
import stripe
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Initialize Stripe
stripe.api_key = STRIPE_SECRET_KEY

def get_db_connection():
    """Get PostgreSQL connection."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def create_revenue_table():
    """Create revenue tracking table if it doesn't exist."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS revenue_daily (
                id SERIAL PRIMARY KEY,
                date DATE UNIQUE NOT NULL,
                total_revenue DECIMAL(10, 2) NOT NULL,
                one_time_sales INT DEFAULT 0,
                subscription_revenue DECIMAL(10, 2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return False

def get_stripe_revenue(start_date, end_date):
    """
    Pull revenue from Stripe for a date range.
    
    Args:
        start_date: datetime or string (YYYY-MM-DD)
        end_date: datetime or string (YYYY-MM-DD)
    
    Returns:
        dict: {one_time: float, subscriptions: float, total: float}
    """
    if not STRIPE_SECRET_KEY:
        print("❌ Error: STRIPE_SECRET_KEY not set")
        return {"one_time": 0, "subscriptions": 0, "total": 0}
    
    try:
        # Convert to timestamps if needed
        if isinstance(start_date, str):
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        else:
            start_ts = int(start_date.timestamp())
        
        if isinstance(end_date, str):
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
        else:
            end_ts = int(end_date.timestamp())
        
        # Get charges (one-time payments)
        charges = stripe.Charge.list(
            created={"gte": start_ts, "lte": end_ts},
            limit=100
        )
        
        one_time_total = sum(
            c.amount / 100 for c in charges.data if c.paid and not c.refunded
        )
        
        # Get invoices (subscriptions)
        invoices = stripe.Invoice.list(
            created={"gte": start_ts, "lte": end_ts},
            status="paid",
            limit=100
        )
        
        subscription_total = sum(
            inv.total / 100 for inv in invoices.data
        )
        
        return {
            "one_time": round(one_time_total, 2),
            "subscriptions": round(subscription_total, 2),
            "total": round(one_time_total + subscription_total, 2)
        }
    
    except Exception as e:
        print(f"❌ Stripe API error: {e}")
        return {"one_time": 0, "subscriptions": 0, "total": 0}

def get_all_time_revenue():
    """Get total revenue across all time."""
    try:
        # Get all charges
        charges = stripe.Charge.list(limit=100, expand=['data.balance_transaction'])
        one_time = sum(
            c.amount / 100 for c in charges.data if c.paid and not c.refunded
        )
        
        # Get all paid invoices (subscriptions)
        invoices = stripe.Invoice.list(status="paid", limit=100, expand=['data.lines.data'])
        subscriptions = sum(inv.total / 100 for inv in invoices.data)
        
        return {
            "one_time": round(one_time, 2),
            "subscriptions": round(subscriptions, 2),
            "total": round(one_time + subscriptions, 2)
        }
    except Exception as e:
        print(f"❌ Stripe API error: {e}")
        return {"one_time": 0, "subscriptions": 0, "total": 0}

def get_upcoming_subscriptions():
    """Get count of active subscriptions."""
    try:
        subs = stripe.Subscription.list(status="active", limit=100)
        return len(subs.data)
    except Exception as e:
        print(f"❌ Stripe API error: {e}")
        return 0

def store_daily_revenue(date, revenue_data):
    """Store daily revenue in database."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO revenue_daily (date, total_revenue, one_time_sales, subscription_revenue)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
                total_revenue = EXCLUDED.total_revenue,
                one_time_sales = EXCLUDED.one_time_sales,
                subscription_revenue = EXCLUDED.subscription_revenue
        """, (
            date,
            revenue_data["total"],
            revenue_data["one_time"],
            revenue_data["subscriptions"]
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database insert failed: {e}")
        return False

def print_revenue_report():
    """Print a formatted revenue report."""
    print("\n" + "="*60)
    print("🌲 EVERGREEN LEAD GEN - REVENUE TRACKER")
    print("="*60)
    
    # Today's revenue
    today = datetime.now().date()
    today_revenue = get_stripe_revenue(today, today)
    
    print(f"\n📅 TODAY ({today}):")
    print(f"   One-time sales: ${today_revenue['one_time']:.2f}")
    print(f"   Subscription revenue: ${today_revenue['subscriptions']:.2f}")
    print(f"   Total: ${today_revenue['total']:.2f}")
    
    # This week's revenue
    start_of_week = today - timedelta(days=today.weekday())
    week_revenue = get_stripe_revenue(start_of_week, today)
    
    print(f"\n📊 THIS WEEK (since {start_of_week}):")
    print(f"   One-time sales: ${week_revenue['one_time']:.2f}")
    print(f"   Subscription revenue: ${week_revenue['subscriptions']:.2f}")
    print(f"   Total: ${week_revenue['total']:.2f}")
    
    # All-time revenue
    all_time = get_all_time_revenue()
    
    print(f"\n💰 ALL TIME:")
    print(f"   One-time sales: ${all_time['one_time']:.2f}")
    print(f"   Subscription revenue: ${all_time['subscriptions']:.2f}")
    print(f"   Total: ${all_time['total']:.2f}")
    
    # Active subscriptions
    active_subs = get_upcoming_subscriptions()
    
    print(f"\n📈 METRICS:")
    print(f"   Active subscriptions: {active_subs}")
    print(f"   Monthly recurring (est.): ${active_subs * 19:.2f}")
    
    # Progress to goal
    daily_goal = 500  # $500/day goal
    if all_time["total"] > 0:
        days_running = (datetime.now() - datetime(2026, 3, 29)).days
        if days_running > 0:
            avg_daily = all_time["total"] / days_running
            progress_pct = (avg_daily / daily_goal) * 100
            print(f"   Avg daily revenue: ${avg_daily:.2f}")
            print(f"   Progress to $500/day goal: {progress_pct:.1f}%")
    
    print("\n" + "="*60 + "\n")
    
    # Store today's revenue
    store_daily_revenue(today, today_revenue)

def main():
    """Main function."""
    print(f"🌲 Revenue Tracker - {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    if not STRIPE_SECRET_KEY:
        print("❌ Error: STRIPE_SECRET_KEY not configured")
        return False
    
    # Ensure table exists
    create_revenue_table()
    
    # Print report
    print_revenue_report()
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
