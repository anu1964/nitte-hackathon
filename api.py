
# Swagger UI at: http://127.0.0.1:8000/docs

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from classifier import analyze_prompt
import csv
import os
from datetime import datetime
import uvicorn

# ── App Setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Safe Prompt Guardian",
    description="Middleware API to detect and block malicious LLM prompts before they reach your AI.",
    version="1.0.0"
)

# Allow all origins (needed if frontend calls this API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LOG_FILE = "log.csv"

# ── Models ────────────────────────────────────────────────────────────────────
class PromptRequest(BaseModel):
    prompt: str
    rephrase: bool = True  # set False for faster response without Groq

class PromptResponse(BaseModel):
    label: str
    confidence: float
    category: str | None
    severity: str | None
    safe_rephrasing: str | None
    blocked: bool

class StatsResponse(BaseModel):
    total_analyzed: int
    attacks_blocked: int
    safe_prompts: int
    attack_rate: str
    top_category: str | None

# ── Logging ───────────────────────────────────────────────────────────────────
def log_to_csv(prompt: str, result: dict):
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "prompt", "label",
            "confidence", "category", "severity"
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt[:300],  # truncate long prompts
            "label": result["label"],
            "confidence": result["confidence"],
            "category": result["category"] or "",
            "severity": result["severity"] or ""
        })

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "🛡️ Safe Prompt Guardian is running",
        "version": "1.0.0",
        "docs": "http://127.0.0.1:8000/docs",
        "endpoints": ["/analyze", "/stats", "/logs", "/health"]
    }

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.post("/analyze", response_model=PromptResponse)
def analyze(req: PromptRequest):
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    result = analyze_prompt(req.prompt, rephrase=req.rephrase)
    log_to_csv(req.prompt, result)

    return PromptResponse(
        label=result["label"],
        confidence=result["confidence"],
        category=result["category"],
        severity=result["severity"],
        safe_rephrasing=result["safe_rephrasing"],
        blocked=result["label"] == "attack"
    )

@app.get("/stats", response_model=StatsResponse)
def stats():
    if not os.path.exists(LOG_FILE):
        return StatsResponse(
            total_analyzed=0,
            attacks_blocked=0,
            safe_prompts=0,
            attack_rate="0%",
            top_category=None
        )

    with open(LOG_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    attacks = [r for r in rows if r["label"] == "attack"]
    attack_count = len(attacks)

    # Find most common attack category
    categories = [r["category"] for r in attacks if r["category"]]
    top_category = max(set(categories), key=categories.count) if categories else None

    return StatsResponse(
        total_analyzed=total,
        attacks_blocked=attack_count,
        safe_prompts=total - attack_count,
        attack_rate=f"{(attack_count/total*100):.1f}%" if total else "0%",
        top_category=top_category
    )

@app.get("/logs")
def get_logs(limit: int = 20):
    if not os.path.exists(LOG_FILE):
        return {"logs": []}

    with open(LOG_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Return most recent first
    return {"logs": rows[-limit:][::-1]}

@app.delete("/logs")
def clear_logs():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    return {"status": "logs cleared"}


# ── LLM Proxy Endpoint ────────────────────────────────────────────────────────
from groq import Groq

from dotenv import load_dotenv
load_dotenv()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

class ChatRequest(BaseModel):
    prompt: str
    system_prompt: str = "You are a helpful assistant."

class ChatResponse(BaseModel):
    status: str        # "blocked" or "allowed"
    verdict: str       # "ATTACK" or "SAFE"
    confidence: float
    message: str       # LLM reply if safe, block message if attack

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # Step 1 — classify
    result = analyze_prompt(req.prompt, rephrase=False)
    log_to_csv(req.prompt, result)

    # Step 2 — block if attack
    if result["label"] == "attack":
        return ChatResponse(
            status="blocked",
            verdict="ATTACK",
            confidence=result["confidence"],
            message="🚨 Prompt injection detected. This prompt was blocked and never reached the LLM."
        )

    # Step 3 — forward to Groq if safe
    groq_response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": req.system_prompt},
            {"role": "user",   "content": req.prompt}
        ]
    )

    return ChatResponse(
        status="allowed",
        verdict="SAFE",
        confidence=result["confidence"],
        message=groq_response.choices[0].message.content
    )

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)