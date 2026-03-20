from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import os
import stripe
from groq import Groq
import psycopg2
from datetime import datetime
import uuid
import urllib.parse
import resend

app = FastAPI()

GROQ_CLIENT = Groq(api_key=os.getenv("GROQ_API_KEY"))
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
resend.api_key = os.getenv("RESEND_API_KEY")

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

# NEW: Weekly auto-update job (runs every Sunday)
@app.get("/weekly-update")
async def weekly_update():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET expiry_date = NULL WHERE payment_type = 'subscription'")
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "weekly updates applied to all subscribers"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# (The rest of the file — home, create-checkout, success, create-subscription, dashboard, generate, agent-pay, health — is the same as the last version you tested. Keep your existing blocks for those.)

@app.get("/health")
async def health():
    return {"status": "ok", "model": DEFAULT_MODEL}