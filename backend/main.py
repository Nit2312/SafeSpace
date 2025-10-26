from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from ai_agent import graph, SYSTEM_PROMPT, parse_response
from typing import Optional, Literal
import uuid

app = FastAPI()

# receive and validate requests from the frontend
class Query(BaseModel):
    message: str
    session_id: str
    # input_mode and response_mode are critical for the voice feature
    input_mode: Literal["chat", "voice"]
    response_mode: Optional[Literal["chat", "voice"]] = None

class StartSessionRequest(BaseModel):
    name: str
    phone: str

class StartSessionResponse(BaseModel):
    session_id: str
    greeting: str

# In-memory session store
SESSIONS = {}

@app.get("/")
def root():  
    return {"message": "Hello, World!"}

@app.post("/start_session", response_model=StartSessionResponse)
def start_session(req: StartSessionRequest):
    session_id = str(uuid.uuid4())
    # Store user data in the session
    SESSIONS[session_id] = {"name": req.name, "phone": req.phone}
    greeting = (
        f"Hello {req.name}, I'm Friday. We can communicate in two modes: chat or voice. "
        f"You can send messages by typing or speaking, and choose how you'd like me to respond."
    )
    return StartSessionResponse(session_id=session_id, greeting=greeting)

@app.post("/ask")
def ask_question(query: Query):
    session = SESSIONS.get(query.session_id)
    name = session.get("name") if session else "there"
    phone = session.get("phone") if session else ""

    # Choose response mode: explicit override or mirror input mode
    chosen_mode = query.response_mode or query.input_mode

    # Inject session context so the agent passes the correct phone number to emergency tool
    session_context = (
        f"User name: {name}. User phone: {phone}. "
        f"When using call_emergency_services(phone), always pass this exact phone number: {phone}. "
        f"Agent name is Friday."
    )

    inputs = {
        "messages": [
            ("system", SYSTEM_PROMPT),
            ("system", session_context),
            ("user", query.message),
        ]
    }
    # Stream the response from the mock agent (or real agent)
    tool_called_name, final_response = parse_response(graph.stream(inputs, stream_mode="updates"))

    # Crucial: The key is 'response', which is what the frontend expects.
    return {
        "response": final_response,
        "tool_called": tool_called_name,
        "response_mode": chosen_mode,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
