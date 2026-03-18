from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import os
import stripe
from groq import Groq
import psycopg2
from datetime import datetime
import uuid
import urllib.parse

app = FastAPI()

GROQ_CLIENT = Groq(api_key=os.getenv("GROQ_API_KEY"))
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# YOUR x402 ADDRESSES (Master Plan baseline)
PAY_TO_XRPL = "twJqGeY3wfmMYm9gBfNVqn3T6nuxrpwGv2"
PAY_TO_XRPL_TAG = 1986572456
PAY_TO_SOLANA = "APwNRVQsiWE9L2KDJDdpuEbtqoVCvZ43BAw2AzQWNz8A"
PAY_TO_RLUSD = "rMdG3ju8pgyVh29ELPWaDUA74CpWW6Fxns"
PAY_TO_RLUSD_TAG = 142654817
PAY_TO_USDC_SOL = "J6MrNdBPe8WrTNh19hX51PQfGS3BQi4KxkH6vHzoBJw5"
DEFAULT_MODEL = "llama-3.1-8b-instant"

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

@app.on_event("startup")
async def startup_event():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                access_key TEXT UNIQUE NOT NULL,
                payment_type TEXT,
                amount_paid DECIMAL,
                paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expiry_date TIMESTAMP,
                active BOOLEAN DEFAULT TRUE
            )
        """)
        for col in ["access_key TEXT UNIQUE", "expiry_date TIMESTAMP", "active BOOLEAN DEFAULT TRUE"]:
            try: cur.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col}")
            except: pass
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB startup error: {e}")

# (Home, create-checkout, success, agent-pay endpoints stay exactly the same as the last version you have — only /generate is updated below)

@app.get("/generate")
async def generate(request: Request, industry: str = Query(None), key: str = Query(None), format: str = Query(None)):
    if not key:
        return JSONResponse(status_code=401, content={"error": "Access key required. Use ?key=YOUR_KEY"})

    # Stripe user check (bypass x402 for valid DB keys)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT active, expiry_date FROM users WHERE access_key = %s", (key,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if not result or not result[0] or (result[1] and result[1] < datetime.now()):
            return JSONResponse(status_code=403, content={"error": "Invalid or expired key"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    if not industry:
        return JSONResponse(status_code=400, content={"error": "Add &industry=Your Niche to the URL"})

    try:
        response = GROQ_CLIENT.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": f"Generate 50 high-quality leads for {industry} business. Output ONLY clean CSV with columns: Company,Website,LinkedIn,Location. No extra text, no markdown."}],
            temperature=0.7
        )
        leads = response.choices[0].message.content.strip()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    # AGENT MODE — pure JSON
    if format == "json":
        return {"status": "success", "leads": leads, "note": "Weekly self-update runs Sundays"}

    # HUMAN MODE — clean HTML page with preview + CSV download
    base_url = os.getenv("BASE_URL") or "https://lead-gen-app-production-d067.up.railway.app"
    encoded_csv = urllib.parse.quote(leads)
    download_link = f"data:text/csv;charset=utf-8,{encoded_csv}"

    html = f"""
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
<meta charset="UTF-8">
<title>Your Leads - Evergreen Lead Gen</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>body {{ font-family: 'Inter', sans-serif; background: linear-gradient(to bottom right, #0f172a, #1e293b); }}</style>
</head>
<body class="min-h-screen text-white p-8">
<div class="max-w-5xl mx-auto bg-slate-900/70 backdrop-blur rounded-3xl p-10">
<h1 class="text-4xl font-bold gradient-text text-center mb-8">Your 50 Leads for {industry}</h1>
<div class="bg-slate-800 p-6 rounded-2xl overflow-auto max-h-[500px] mb-8">
<pre class="text-sm text-gray-300 whitespace-pre-wrap">{leads}</pre>
</div>
<div class="flex gap-4 justify-center">
<a href="{download_link}" download="leads-{industry.replace(' ', '-')}.csv" 
class="bg-green-600 hover:bg-green-700 text-white font-semibold py-4 px-10 rounded-2xl transition text-lg">📥 Download CSV File</a>
<button onclick="navigator.clipboard.writeText(`{leads.replace('`','\\`')}`);alert('Copied to clipboard!')" 
class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-4 px-10 rounded-2xl transition text-lg">📋 Copy to Clipboard</button>
</div>
<p class="text-center mt-10 text-gray-400 text-sm">Weekly auto-updates available with $19/mo subscription (x402). Questions? DM @theryancameron</p>
</div>
</body>
</html>
    """
    return HTMLResponse(content=html)

@app.get("/health")
async def health():
    return {"status": "ok", "model": DEFAULT_MODEL}