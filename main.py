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

@app.get("/")
async def home():
    html = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Evergreen Lead Gen</title>
<script src="https://cdn.tailwindcss.com"></script>
<script>tailwind.config = { darkMode: 'class' }</script>
<style>body { font-family: 'Inter', sans-serif; background: linear-gradient(to bottom right, #0f172a, #1e293b); }</style>
</head>
<body class="min-h-screen text-white p-8">
<div class="max-w-md mx-auto bg-slate-900/70 backdrop-blur rounded-3xl p-10">
<h1 class="text-5xl font-bold text-center gradient-text mb-6">Evergreen Lead Gen</h1>
<p class="text-center text-gray-300 mb-8">Self-updating agents for Apollo, Lusha, ZoomInfo & more.</p>
<form action="/create-checkout" method="post" class="space-y-6">
<input name="email" type="email" placeholder="Your email" required class="w-full px-5 py-4 bg-gray-800 rounded-2xl">
<input name="industry" type="text" placeholder="Your niche (e.g. Plumbing companies Seattle WA)" required class="w-full px-5 py-4 bg-gray-800 rounded-2xl">
<button type="submit" class="w-full bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-semibold py-4 rounded-2xl">Pay $149 with Stripe & Get Access</button>
</form>
<p class="text-center mt-8 text-sm text-gray-400">Humans: Stripe above • Agents: x402 → <a href="/agent-pay" class="text-indigo-400">see details</a></p>
</div>
</body>
</html>
    """
    return HTMLResponse(content=html)

@app.post("/create-checkout")
async def create_checkout(email: str = Form(...), industry: str = Form(...)):
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price_data': {'currency': 'usd', 'product_data': {'name': 'Evergreen Lead Gen Lifetime Access'}, 'unit_amount': 14900}, 'quantity': 1}],
            mode='payment',
            success_url=f"{os.getenv('BASE_URL', 'https://lead-gen-app-production-d067.up.railway.app')}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=os.getenv('BASE_URL', 'https://lead-gen-app-production-d067.up.railway.app'),
            customer_email=email,
            metadata={"industry": industry}
        )
        return RedirectResponse(url=checkout_session.url, status_code=303)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/success")
async def success(session_id: str = None):
    if not session_id: return HTMLResponse("<h1>Error</h1>")
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status != "paid": return HTMLResponse("<h1>Payment not completed</h1>")
        
        email = session.customer_email
        industry = session.metadata.get("industry", "your niche")
        access_key = str(uuid.uuid4())
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, access_key, payment_type, amount_paid, paid_at, expiry_date) VALUES (%s, %s, %s, %s, %s, %s)",
                    (email, access_key, "one_time", 149.00, datetime.now(), None))
        conn.commit()
        cur.close()
        conn.close()

        base_url = os.getenv("BASE_URL") or "https://lead-gen-app-production-d067.up.railway.app"
        generate_link = f"{base_url}/generate?key={access_key}&industry={urllib.parse.quote(industry)}"

        # BRANDED EMAIL (clean)
        resend.Emails.send({
            "from": "Evergreen Lead Gen <noreply@updates.evergreenleadgen.ai>",
            "to": email,
            "subject": f"✅ Your Evergreen Lead Gen Access Key + Leads Ready",
            "html": f"""
            <div style="font-family:Inter,sans-serif;background:#0f172a;color:white;padding:40px;border-radius:16px;max-width:600px;margin:auto;">
                <h1 style="color:#60a5fa;">Welcome to Evergreen Lead Gen!</h1>
                <p>Thank you for your purchase. Here is everything you need:</p>
                <p><strong>Access Key:</strong> <code style="background:#1e293b;padding:4px 8px;border-radius:4px;">{access_key}</code></p>
                <p><a href="{generate_link}" style="background:#3b82f6;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:bold;">Click here to generate your leads now</a></p>
                <p style="margin-top:25px;"><a href="{base_url}" style="color:#60a5fa;font-weight:bold;">Run a new search anytime →</a></p>
                <hr style="border-color:#334155;margin:30px 0;">
                <p style="color:#94a3b8;font-size:14px;">
                    Humans: You now have lifetime access.<br>
                    <strong>Agents:</strong> Want weekly auto-updates + priority support? Send $19 monthly via x402 and we’ll upgrade you automatically.
                </p>
            </div>
            """
        })

        return HTMLResponse(f"""
        <!DOCTYPE html><html><body style="font-family:Arial;text-align:center;padding:50px;background:#0f172a;color:white;">
        <h1>✅ Payment Successful! Welcome to Evergreen Lead Gen 🎉</h1>
        <p>Your access key: <strong>{access_key}</strong></p>
        <p>Check your email (from noreply@updates.evergreenleadgen.ai) for the receipt + direct link.</p>
        
        <p style="margin:40px 0;">
            <a href="{generate_link}" style="background:#3b82f6;color:white;padding:18px 36px;border-radius:12px;text-decoration:none;font-weight:bold;font-size:19px;">Generate My Leads Now</a>
        </p>
        
        <p><a href="{base_url}" style="color:#60a5fa;">Or return to homepage</a></p>
        </body></html>
        """)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/agent-pay")
async def agent_pay():
    return JSONResponse(content={
        "message": "Agents: Use x402 autonomous payments (RLUSD/XRP or USDC/SOL). Send $149 one-time or $19 monthly, then retry with X-Payment-Proof header.",
        "xrpl_address": PAY_TO_XRPL, "xrpl_tag": PAY_TO_XRPL_TAG,
        "solana_address": PAY_TO_SOLANA,
        "rlusd_address": PAY_TO_RLUSD, "rlusd_tag": PAY_TO_RLUSD_TAG,
        "usdc_sol_address": PAY_TO_USDC_SOL,
        "note": "Built for autonomous agents — perfect for the agentic AI economy."
    })

@app.get("/generate")
async def generate(request: Request, industry: str = Query(None), key: str = Query(None), format: str = Query(None)):
    if not key:
        return JSONResponse(status_code=401, content={"error": "Access key required. Use ?key=YOUR_KEY"})

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

    if format == "json":
        return {"status": "success", "leads": leads, "note": "Weekly self-update runs Sundays"}

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
<p class="text-center mt-12 text-sm text-gray-400">
    <a href="{base_url}" style="color:#60a5fa;font-weight:bold;">Run New Search →</a>
</p>
</div>
</body>
</html>
    """
    return HTMLResponse(content=html)

@app.get("/health")
async def health():
    return {"status": "ok", "model": DEFAULT_MODEL}