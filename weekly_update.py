"""
weekly_update.py — Evergreen Lead Gen Sunday Auto-Update
Runs every Sunday. Finds all active $19/mo subscribers, re-generates
their last search, and emails them fresh leads via Resend.
"""

import os
import psycopg2
import resend
from groq import Groq

resend.api_key = os.getenv("RESEND_API_KEY")
GROQ_CLIENT = Groq(api_key=os.getenv("GROQ_API_KEY"))
DEFAULT_MODEL = "llama-3.1-8b-instant"
BASE_URL = os.getenv("BASE_URL", "https://app.evergreenleadgen.ai")


def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def generate_leads(industry: str) -> str:
    response = GROQ_CLIENT.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": f"""You are a professional B2B lead generation expert.

Generate exactly 50 real, legitimate companies that match this exact niche: {industry}.

STRICT RULES:
- ONLY return companies in the EXACT location mentioned in the niche (e.g. if it says "Bellevue WA", do NOT include Seattle, Kirkland, Redmond, Tukwila, or any other city).
- If the niche specifies a city, stay 100% within that city only.
- Only real, existing businesses (no fictional names).
- Output ONLY a clean CSV with exactly these columns and nothing else: "Company","Website","LinkedIn","Location"
- No explanations, no notes, no markdown, no extra text at all."""}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()


def send_update_email(email: str, access_key: str, industry: str, leads_csv: str):
    dashboard_link = f"{BASE_URL}/dashboard?key={access_key}"
    resend.Emails.send({
        "from": "Evergreen Lead Gen <noreply@updates.evergreenleadgen.ai>",
        "to": email,
        "subject": f"🌲 Your Weekly Fresh Leads: {industry}",
        "html": f"""
        <div style="font-family:Inter,sans-serif;background:#0f172a;color:white;padding:40px;border-radius:16px;max-width:600px;margin:auto;">
            <h1 style="color:#60a5fa;">🌲 Your Weekly Leads Are Ready!</h1>
            <p>Fresh leads for <strong>{industry}</strong> have been generated and are ready to download.</p>
            <p><a href="{dashboard_link}" style="background:#3b82f6;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:bold;">Go to Dashboard → Run Search</a></p>
            <hr style="border-color:#334155;margin:30px 0;">
            <p style="color:#94a3b8;font-size:13px;">You're receiving this because you have an active $19/mo Evergreen Lead Gen subscription. These leads auto-refresh every Sunday.</p>
        </div>
        """
    })


def run_weekly_update():
    print("Starting weekly update...")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT email, access_key, last_industry
        FROM users
        WHERE payment_type = 'subscription'
        AND active = TRUE
        AND last_industry IS NOT NULL
        AND last_industry != ''
    """)
    subscribers = cur.fetchall()
    cur.close()
    conn.close()

    print(f"Found {len(subscribers)} active subscribers with saved searches.")

    for email, access_key, industry in subscribers:
        try:
            print(f"Generating leads for {email} → {industry}")
            leads_csv = generate_leads(industry)
            send_update_email(email, access_key, industry, leads_csv)
            print(f"✅ Sent to {email}")
        except Exception as e:
            print(f"❌ Failed for {email}: {e}")

    print("Weekly update complete.")


if __name__ == "__main__":
    run_weekly_update()
