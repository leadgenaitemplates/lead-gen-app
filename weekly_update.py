"""
weekly_update.py — Evergreen Lead Gen Sunday Auto-Update
Runs every Sunday at 9am UTC.
Uses Groq to research the latest B2B lead gen best practices and Google trends,
then updates the prompt_config table so all future searches use the freshest logic.
"""

import os
import psycopg2
from groq import Groq
from datetime import datetime

GROQ_CLIENT = Groq(api_key=os.getenv("GROQ_API_KEY"))
DEFAULT_MODEL = "llama-3.1-8b-instant"


def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def research_and_generate_new_prompt() -> str:
    """Ask Groq to produce an updated lead gen prompt based on current best practices."""
    today = datetime.utcnow().strftime("%B %d, %Y")

    research_response = GROQ_CLIENT.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": f"""Today is {today}.

You are an expert in B2B lead generation, Google search trends, and modern outreach strategies.

Your job is to write an updated, highly effective system prompt for an AI lead generation tool.
The prompt will be used to generate 50 real B2B leads in CSV format for any niche a user enters.

The prompt you write should:
- Reflect the latest Google search trends and what businesses are currently active and growing
- Incorporate current best practices in B2B lead gen (quality over quantity, verified contacts, location accuracy)
- Instruct the AI to focus on businesses most likely to be actively seeking services right now
- Maintain strict location accuracy (only return businesses in the exact city/region specified)
- Output only clean CSV with columns: Company, Website, LinkedIn, Location
- Produce exactly 50 real, existing businesses — no fictional names

Write ONLY the system prompt text. No explanation, no preamble. The prompt must include the placeholder {{industry}} where the user's niche will be inserted.

Make it better than last week's version. Be specific about quality signals and current trends."""}],
        temperature=0.8
    )

    new_prompt = research_response.choices[0].message.content.strip()
    return new_prompt


def update_prompt_in_db(new_prompt: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO prompt_config (prompt, updated_at) VALUES (%s, %s)",
        (new_prompt, datetime.utcnow())
    )
    conn.commit()
    cur.close()
    conn.close()


def run_weekly_update():
    print(f"[{datetime.utcnow().isoformat()}] Starting weekly prompt update...")

    try:
        new_prompt = research_and_generate_new_prompt()
        print(f"Generated new prompt ({len(new_prompt)} chars)")

        update_prompt_in_db(new_prompt)
        print("✅ Prompt updated in DB. All future searches will use the latest version.")

    except Exception as e:
        print(f"❌ Weekly update failed: {e}")
        raise


if __name__ == "__main__":
    run_weekly_update()
