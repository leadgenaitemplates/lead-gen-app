from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import os
import stripe
from groq import Groq
import psycopg2
from datetime import datetime
import uuid

app = FastAPI()

GROQ_CLIENT = Groq(api_key=os.getenv("GROQ_API_KEY"))
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# YOUR x402 ADDRESSES + TAGS (Master Plan baseline)
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
<script>
  tailwind.config = { darkMode: 'class', theme: { extend: { colors: { primary: '#3b82f6', indigo: '#6366f1', slate900: '#0f172a', slate800: '#1e293b', cardbg: 'rgba(30,41,59,0.7)', borderlight: 'rgba(255,255,255,0.1)' } } } }
</script>
<style>
  body { font-family: 'Inter', sans-serif; background: linear-gradient(to bottom right, #0f172a, #1e293b); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 2rem 1rem; margin: 0; }
  .glass { background: rgba(30,41,59,0.7); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); border-radius: 1.5rem; padding: 3.5rem 2.5rem; max-width: 36rem; width: 100%; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }
  .gradient-text { background: linear-gradient(to right, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .btn-gradient { background: linear-gradient(to right, #3b82f6, #6366f1); }
  .btn-gradient:hover { background: linear-gradient(to right, #2563eb, #4f46e5); }
</style>
</head>
<body>
<div class="glass">
  <h1 class="font-bold text-center text-5xl md:text-7xl gradient-text mb-6">Evergreen Lead Gen</h1>
  <p class="text-center text-gray-300 mb-8 text-lg">
    Self-updating agents for Apollo, Lusha, ZoomInfo & more.<br>
    $149 one-time for basic access or $19/mo for weekly auto-updates + priority support.
  </p>
  <form action="/create-checkout" method="post" class="space-y-6">
    <input name="email" type="email" placeholder="Your email" required class="w-full px-5 py-4 bg-gray-800/70 border border-gray-600 rounded-2xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary transition">
    <input name="industry" type="text" placeholder="Your niche (e.g. Plumbing companies Seattle WA)" required class="w-full px-5 py-4 bg-gray-800/70 border border-gray-600 rounded-2xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary transition">
    <button type="submit" class="w-full btn-gradient text-white font-semibold py-4 rounded-2xl text-lg transition transform hover:scale-[1.02]">Pay $149 with Stripe & Get Access</button>
  </form>
  <p class="text-center mt-8 text-sm text-gray-400">
    Humans: Use Stripe above.<br>
    <strong>Agents:</strong> Use x402 for autonomous payments → <a href="/agent-pay" class="text-indigo-400 hover:underline">see details here</a>.
  </p>
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
    if not session_id: return HTMLResponse("<h1>Error: No session ID</h1>")
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
        
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html><body style="font-family:Arial;text-align:center;padding:50px;background:#0f172a;color:white;">
        <h1>✅ Payment Successful! Welcome to Evergreen Lead Gen 🎉</h1>
        <p>Your access key: <strong>{access_key}</strong></p>
        <p>Click here to generate leads now: <a href="{base_url}/generate?key={access_key}&industry={industry}" style="color:#60a5fa;">{base_url}/generate?key={access_key}&industry={industry}</a></p>
        <p class="mt-8 text-sm text-gray-400">
          Humans: Lifetime access granted.<br>
          <strong>Agents:</strong> Want $19/mo weekly auto-updates? Use x402 to the same addresses.
        </p>
        </body></html>
        """)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/agent-pay")
async def agent_pay():
    return JSONResponse(content={
        "message": "Agents: Pay with x402 (RLUSD/XRP or USDC/SOL). Send $149 one-time or $19 monthly, then retry /generate with X-Payment-Proof header.",
        "xrpl_address": PAY_TO_XRPL, "xrpl_tag": PAY_TO_XRPL_TAG,
        "solana_address": PAY_TO_SOLANA,
        "rlusd_address": PAY_TO_RLUSD, "rlusd_tag": PAY_TO_RLUSD_TAG,
        "usdc_sol_address": PAY_TO_USDC_SOL,
        "note": "Built for autonomous agents — perfect for the agentic AI economy."
    })

@app.get("/generate")
async def generate(request: Request, industry: str = Query(None), key: str = Query(None)):
    if not key:
        key = request.query_params.get("key") or request.headers.get("Authorization", "").replace("Bearer ", "")
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
    
    proof = request.headers.get("X-Payment-Proof")
    if not proof:
        return JSONResponse(status_code=402, content={
            "error": "Payment Required (x402 path)",
            "xrpl_address": PAY_TO_XRPL, "xrpl_tag": PAY_TO_XRPL_TAG,
            "solana_address": PAY_TO_SOLANA,
            "rlusd_address": PAY_TO_RLUSD, "rlusd_tag": PAY_TO_RLUSD_TAG,
            "usdc_sol_address": PAY_TO_USDC_SOL,
            "message": "Pay via x402 then retry with X-Payment-Proof header."
        })
    
    try:
        response = GROQ_CLIENT.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": f"Generate 50 high-quality leads for {industry} business. Output as CSV with columns: Company, Website, LinkedIn, Location."}],
            temperature=0.7
        )
        leads = response.choices[0].message.content
        return {"status": "success", "leads": leads, "note": "Weekly self-update runs Sundays"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/health")
async def health():
    return {"status": "ok", "model": DEFAULT_MODEL}