from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from groq import Groq
import os

app = FastAPI()

GROQ_CLIENT = Groq(api_key=os.getenv("GROQ_API_KEY"))

@app.get("/")
async def home():
    html = """
    <h1>Evergreen Lead Gen Template – Test Deploy Live!</h1>
    <p>Enter a niche to generate sample leads (full payments soon).</p>
    <form action="/generate" method="post">
        <input name="industry" placeholder="e.g. SaaS Austin" required style="padding:10px; width:300px;">
        <button type="submit" style="padding:10px 20px;">Generate Sample Leads</button>
    </form>
    <p><small>Test mode – Groq 8B model. Full version after Phase 3.</small></p>
    """
    return HTMLResponse(html)

@app.post("/generate")
async def generate(industry: str = Form(None)):
    if not industry:
        return JSONResponse(status_code=400, content={"error": "Industry required"})

    response = GROQ_CLIENT.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": f"Generate 5 sample leads for {industry} as CSV: Company,Website,Location"}],
        temperature=0.7
    )
    leads = response.choices[0].message.content

    return {"status": "success", "leads": leads}

@app.get("/health")
async def health():
    return {"status": "ok", "note": "Phase 2 test successful!"}