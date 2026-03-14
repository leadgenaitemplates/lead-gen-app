from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import os
import stripe
from groq import Groq
import psycopg2
from datetime import datetime

app = FastAPI()

# Groq client
GROQ_CLIENT = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Stripe (added in Phase 6)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# YOUR UPHOLD ADDRESSES + TAGS
PAY_TO_XRPL = "rwJqGeY3WfmMYm9gBfNVqn3T6nurrpwGv2"
PAY_TO_XRPL_TAG = 1986572456
PAY_TO_SOLANA = "APwNRVQsiWE9L2KDJDdpufbtqoVCvZ4JBAw2AzQwNz8A"
PAY_TO_RLUSD = "rMdG3ju8pgyVh29ELPWaDuA74CpWW6Fxns"
PAY_TO_RLUSD_TAG = 142654817
PAY_TO_USDC_SOL = "J6MrNdBPe8WrTNh19hX51PQfGS3BQi4kxkH6vHzoBJw5"

DEFAULT_MODEL = "llama-3.1-8b-instant"

# DB connection helper
def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# Create table on startup (runs once when app starts)
@app.on_event("startup")
async def startup_event():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                stripe_customer_id TEXT UNIQUE,
                email TEXT,
                payment_type TEXT,  -- 'one_time' or 'subscription'
                amount_paid DECIMAL,
                paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expiry_date TIMESTAMP,  -- null for one-time, date+30d for monthly
                active BOOLEAN DEFAULT TRUE
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB startup error: {e}")

@app.get("/")
async def home():
    html = """
    <!DOCTYPE html>
    <html lang="en" class="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Evergreen Lead Gen Templates</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            tailwind.config = {
                darkMode: 'class',
                theme: { extend: { colors: { primary: '#3b82f6', darkbg: '#0f172a', cardbg: 'rgba(30,41,59,0.8)' } } }
            }
        </script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; background: linear-gradient(to bottom right, #0f172a, #1e293b); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 1.5rem; }
            .glass { background: rgba(30,41,59,0.7); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); border-radius: 1.5rem; padding: 2.5rem; max-width: 28rem; width: 100%; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }
            .gradient-text { background: linear-gradient(to right, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        </style>
    </head>
    <body>
        <div class="glass">
            <h1 class="text-4xl md:text-5xl font-bold text-center mb-6 gradient-text">
                Evergreen Lead Gen
            </h1>
            <p class="text-center text-gray-300 mb-8 text-lg">
                Self-updating agents for Apollo, Lusha, ZoomInfo & more.  
                $149 one-time for basic access or $19/mo for weekly auto-updates + priority support.
            </p>
            <form action="/create-checkout" method="post" class="space-y-6">
                <input name="industry" placeholder="Your niche (e.g. SaaS Austin)" required class="w-full px-5 py-4 bg-gray-800/70 border border-gray-600 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition" />
                <button type="submit" class="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold py-4 px-6 rounded-xl transition duration-300 shadow-lg transform hover:scale-[1.02]">
                    Pay $149 with Stripe & Generate Leads
                </button>
            </form>
            <p class="text-center mt-8 text-sm text-gray-400">
                Agents? Use x402 for autonomous payments (RLUSD/XRP or USDC/SOL).
            </p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post("/create-checkout")
async def create_checkout(industry: str = Form(...)):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"Lead Gen Template - {industry}"},
                    "unit_amount": 14900,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url="https://lead-gen-app-production-d067.up.railway.app/success?industry=" + industry,
            cancel_url="https://lead-gen-app-production-d067.up.railway.app/",
        )
        return RedirectResponse(session.url, status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/success")
async def success(industry: str):
    # Record one-time payment (expand in Phase 6 with real Stripe data)
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (payment_type, amount_paid, paid_at, expiry_date) VALUES (%s, %s, %s, %s)",
            ("one_time", 149.00, datetime.now(), None)  # lifetime = no expiry
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB error on success: {e}")
    return {"status": "paid", "message": f"Payment received! Generating leads for {industry}... (recorded in DB)"}

@app.post("/generate")
async def generate(request: Request, industry: str = Form(None)):
    proof = request.headers.get("X-Payment-Proof")
    if not proof:
        return JSONResponse(status_code=402, content={
            "error": "Payment Required",
            "xrpl_address": PAY_TO_XRPL,
            "xrpl_tag": PAY_TO_XRPL_TAG,
            "solana_address": PAY_TO_SOLANA,
            "rlusd_address": PAY_TO_RLUSD,
            "rlusd_tag": PAY_TO_RLUSD_TAG,
            "usdc_sol_address": PAY_TO_USDC_SOL,
            "message": "Pay $149 one-time with RLUSD/XRP (x402) or USDC on Solana for basic access. For $19/mo subscription (weekly auto-updates + priority support), send $19 monthly to the same address + tag. Use Destination Tag if needed. Then retry with X-Payment-Proof header containing tx hash."
        })

    try:
        response = GROQ_CLIENT.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": f"Generate 50 high-quality leads for {industry} business. Output as CSV with columns: Company,Website,LinkedIn,Location."}],
            temperature=0.7
        )
        leads = response.choices[0].message.content
        return {"status": "success", "leads": leads, "note": "Weekly self-update runs Sundays"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/health")
async def health():
    return {"status": "ok", "model": DEFAULT_MODEL}