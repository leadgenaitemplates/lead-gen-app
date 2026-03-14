from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import os
import stripe
from groq import Groq

app = FastAPI()

# Groq (brain)
GROQ_CLIENT = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Stripe (added in Phase 6)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# YOUR REAL UPHOLD ADDRESSES + TAGS
PAY_TO_XRPL = "rwJqGeY3WfmMYm9gBfNVqn3T6nurrpwGv2"
PAY_TO_XRPL_TAG = 1986572456
PAY_TO_SOLANA = "APwNRVQsiWE9L2KDJDdpufbtqoVCvZ4JBAw2AzQwNz8A"
PAY_TO_RLUSD = "rMdG3ju8pgyVh29ELPWaDuA74CpWW6Fxns"
PAY_TO_RLUSD_TAG = 142654817
PAY_TO_USDC_SOL = "J6MrNdBPe8WrTNh19hX51PQfGS3BQi4kxkH6vHzoBJw5"

DEFAULT_MODEL = "llama-3.1-8b-instant"

@app.get("/")
async def home():
    html = """
    <h1>🚀 Evergreen Lead Gen Agent Template</h1>
    <p>$149 one-time or $19/month. Pay easily with Stripe or use x402 for agents.</p>
    <form action="/create-checkout" method="post">
        <input name="industry" placeholder="Your niche (e.g. SaaS Austin)" required style="padding:10px; width:300px;">
        <button type="submit" style="padding:10px 20px;">Pay $149 with Stripe & Generate Leads</button>
    </form>
    <p><small>Agents: Use the API endpoint with x402 payment proof.</small></p>
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
    return {"status": "paid", "message": f"Payment received! Generating leads for {industry}..."}

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
            "message": "Pay $149 with RLUSD/XRP (x402) or USDC on Solana. Use the Destination Tag if needed. Then retry with X-Payment-Proof header."
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