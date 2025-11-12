import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from database import db, create_document, get_documents
from schemas import Lead, Subscriber, ChatMessage

app = FastAPI(title="SPixLabs API", description="Backend for SPixLabs marketing site", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "SPixLabs API is running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from SPixLabs backend!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response: Dict[str, Any] = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = getattr(db, 'name', None) or "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# ---------- Leads ----------
@app.post("/api/leads")
def create_lead(lead: Lead):
    try:
        lead_id = create_document("lead", lead)
        return {"status": "ok", "id": lead_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/leads")
def list_leads(limit: Optional[int] = 50):
    try:
        docs = get_documents("lead", limit=limit)
        for d in docs:
            d["_id"] = str(d["_id"])  # serialize ObjectId
        return {"items": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Subscribers ----------
@app.post("/api/subscribe")
def subscribe(sub: Subscriber):
    try:
        sub_id = create_document("subscriber", sub)
        return {"status": "ok", "id": sub_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Ask SPix (demo echo with simple heuristics) ----------
class AskPayload(BaseModel):
    session_id: str
    message: str

@app.post("/api/ask")
def ask_spix(payload: AskPayload):
    """
    Simple rule-based response to simulate an AI assistant.
    Also stores chat transcript messages in the database.
    """
    try:
        # store user message
        create_document("chatmessage", ChatMessage(session_id=payload.session_id, role="user", content=payload.message))

        # naive heuristic response
        text = payload.message.lower()
        if any(k in text for k in ["price", "pricing", "cost"]):
            answer = "Our pricing is tailored to your goals and channels. Share your monthly ad spend and targets and we'll propose tiers within minutes."
        elif any(k in text for k in ["service", "offer", "solutions"]):
            answer = "We offer AI marketing automation, content intelligence, predictive ad optimization, analytics, and creative strategy."
        elif any(k in text for k in ["hello", "hi", "hey"]):
            answer = "Hi! I'm SPix. How can I help you grow with AI today?"
        else:
            answer = "Great question. A strategist will review and get back shortly. Meanwhile, tell me your goals, budget, and timeframe."

        # store assistant message
        create_document("chatmessage", ChatMessage(session_id=payload.session_id, role="assistant", content=answer))
        return {"reply": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
