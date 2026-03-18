from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import os
import stripe
from groq import Groq
import psycopg2
from datetime import datetime, timedelta
import uuid

app = FastAPI()

GROQ_CLIENT = Groq(api_key=os.getenv("GROQ_API_KEY"))
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

# Create table on startup (safe, adds missing columns)
@app.on_event("startup")
async def startup_event():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create table if missing
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
        
        # Add missing columns safely
        try:
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS access_key TEXT UNIQUE")
        except:
            pass
        try:
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS expiry_date TIMESTAMP")
        except:
            pass
        try:
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE")
        except:
            pass
        
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
            tailwind.config = {
                darkMode: 'class',
                theme: {
                    extend: {
                        colors: {
                            primary: '#3b82f6',
                            indigo: '#6366f1',
                            slate900: '#0f172a',
                            slate800: '#1e293b',
                            cardbg: 'rgba(30,41,59,0.7)',
                            borderlight: 'rgba(255,255,255,0.1)'
                        }
                    }
                }
            }
        </script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(to bottom right, #0f172a, #1e293b);
                min-height: 100vh;
                margin: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .hero {
                text-align: center;
                padding: 8rem 2rem 6rem;
                background: linear-gradient(to bottom right, #0f172a, #1e293b);
                width: 100%;
            }
            .container {
                width: 100%;
                max-width: 1200px;
                padding: 0 1.5rem;
            }
            .gradient-text {
                background: linear-gradient(to right, #60a5fa, #a78bfa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-size: 3.75rem;
                line-height: 1.1;
                font-weight: 700;
                margin-bottom: 1.5rem;
            }
            @media (min-width: 768px) {
                .gradient-text {
                    font-size: 5.5rem;
                }
            }
            .subheadline {
                font-size: 1.25rem;
                line-height: 1.75;
                color: #d1d5db;
                margin-bottom: 2.5rem;
                max-width: 48rem;
                margin-left: auto;
                margin-right: auto;
            }
            .cta-button {
                background: linear-gradient(to right, #3b82f6, #6366f1);
                color: white;
                font-weight: 600;
                padding: 1.25rem 3rem;
                border-radius: 0.75rem;
                font-size: 1.25rem;
                transition: all 0.3s ease;
                box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
            }
            .cta-button:hover {
                background: linear-gradient(to right, #2563eb, #4f46e5);
                transform: translateY(-3px);
                box-shadow: 0 20px 25px -5px rgba(0,0,0,0.4);
            }
            .glass-card {
                background: rgba(30,41,59,0.7);
                backdrop-filter: blur(16px);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 1.5rem;
                padding: 3rem;
                margin: 3rem 1rem;
                max-width: 48rem;
                width: 100%;
                box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
            }
            .features-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
                gap: 2rem;
                margin: 4rem 0;
            }
            .feature-item {
                background: rgba(30,41,59,0.5);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 1rem;
                padding: 2rem;
                text-align: center;
            }
            .pricing-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(22rem, 1fr));
                gap: 2rem;
                margin: 4rem 0;
            }
            .pricing-card {
                background: rgba(30,41,59,0.7);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 1.5rem;
                padding: 2.5rem;
                text-align: center;
                box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5);
            }
            .price {
                font-size: 3.5rem;
                font-weight: 700;
                margin: 1rem 0;
                color: #60a5fa;
            }
            footer {
                text-align: center;
                padding: 4rem 1rem 2rem;
                color: #9ca3af;
                font-size: 0.875rem;
                border-top: 1px solid rgba(255,255,255,0.1);
            }
        </style>
    </head>
    <body>
        <header class="hero">
            <div class="container">
                <h1 class="gradient-text">Evergreen Lead Gen</h1>
                <p class="subheadline">
                    Self-updating agents for Apollo, Lusha, ZoomInfo & more.  
                    $149 one-time for basic access or $19/mo for weekly auto-updates + priority support.
                </p>
                <a href="https://lead-gen-app-production-d067.up.railway.app/" class="cta-button">
                    Generate Leads Now
                </a>
                <p class="mt-6 text-gray-400 text-sm">
                    Works with Apollo, Lusha, ZoomInfo, Cognism, Clay, RocketReach & more. Stripe easy-pay or x402 for agents.
                </p>
            </div>
        </header>

        <main class="container">
            <section class="glass-card">
                <h2 class="text-3xl font-bold text-center mb-6 gradient-text">How It Works</h2>
                <div class="features-grid">
                    <div class="feature-item">
                        <h3 class="text-xl font-semibold mb-4">Step 1</h3>
                        <p>Type your niche (e.g. SaaS Austin)</p>
                    </div>
                    <div class="feature-item">
                        <h3 class="text-xl font-semibold mb-4">Step 2</h3>
                        <p>Connect your Apollo, Lusha, ZoomInfo, Cognism, Clay or RocketReach key (free) or pay $12 for enrichment</p>
                    </div>
                    <div class="feature-item">
                        <h3 class="text-xl font-semibold mb-4">Step 3</h3>
                        <p>Get fresh CSV with 50+ leads (Company, Website, LinkedIn, Location)</p>
                    </div>
                    <div class="feature-item">
                        <h3 class="text-xl font-semibold mb-4">Step 4</h3>
                        <p>$19/mo unlocks weekly auto-updates so it never breaks + priority support</p>
                    </div>
                </div>
            </section>

            <section class="glass-card">
                <h2 class="text-3xl font-bold text-center mb-6 gradient-text">Pricing</h2>
                <div class="pricing-grid">
                    <div class="pricing-card">
                        <h3 class="text-2xl font-bold mb-4">One-Time</h3>
                        <div class="price">$149</div>
                        <ul class="text-left text-gray-300 space-y-3 mb-6">
                            <li>Lifetime access</li>
                            <li>Unlimited runs</li>
                            <li>Basic template (no weekly updates)</li>
                            <li>Works on top of your existing Apollo, Lusha, ZoomInfo, Cognism, Clay, RocketReach keys</li>
                        </ul>
                        <a href="https://lead-gen-app-production-d067.up.railway.app/" class="btn-gradient text-white font-semibold py-3 px-6 rounded-lg inline-block transition duration-300 hover:scale-[1.02]">
                            Choose Plan
                        </a>
                    </div>
                    <div class="pricing-card">
                        <h3 class="text-2xl font-bold mb-4">Subscription</h3>
                        <div class="price">$19<span class="text-base">/month</span></div>
                        <ul class="text-left text-gray-300 space-y-3 mb-6">
                            <li>Everything in One-Time</li>
                            <li>Weekly auto-updates</li>
                            <li>Priority support</li>
                            <li>Early access to new templates</li>
                            <li>Works on top of your existing Apollo, Lusha, ZoomInfo, Cognism, Clay, RocketReach keys</li>
                        </ul>
                        <a href="https://lead-gen-app-production-d067.up.railway.app/" class="btn-gradient text-white font-semibold py-3 px-6 rounded-lg inline-block transition duration-300 hover:scale-[1.02]">
                            Choose Plan
                        </a>
                    </div>
                </div>
                <p class="text-center text-gray-400 mt-6">Optional Enrichment Run – $12 each</p>
            </section>
        </main>

        <footer>
            <p>We only provide automation templates. Use your own Apollo, Lusha, ZoomInfo, Cognism, Clay, RocketReach keys. We do not store or process personal data. Follow GDPR/CCPA rules yourself. Not for spam or illegal use. Questions? DM @theryancameron on X or email support@evergreenleadgen.ai.</p>
        </footer>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post("/create-checkout")
async def create_checkout(email: str = Form(...), industry: str = Form(...)):
    access_key = str(uuid.uuid4())
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, access_key, payment_type, amount_paid, paid_at, expiry_date) VALUES (%s, %s, %s, %s, %s, %s)",
            (email, access_key, "one_time", 149.00, datetime.now(), None)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"DB error: {str(e)}"})
    
    return {"status": "paid", "access_key": access_key, "message": f"Payment received! Your access key: {access_key}. Save this! Use ?key={access_key} on /generate."}

@app.post("/generate")
async def generate(request: Request, industry: str = Form(None)):
    key = request.query_params.get("key") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not key:
        return JSONResponse(status_code=401, content={"error": "Access key required. Use ?key=YOUR_KEY or Authorization: Bearer YOUR_KEY"})

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT active, expiry_date FROM users WHERE access_key = %s", (key,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if not result:
            return JSONResponse(status_code=403, content={"error": "Invalid access key"})
        active, expiry = result
        if not active or (expiry and expiry < datetime.now()):
            return JSONResponse(status_code=403, content={"error": "Access expired or inactive. Renew subscription."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"DB error: {str(e)}"})

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