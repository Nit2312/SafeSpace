import os
import uuid
import streamlit as st
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

# LangChain / LangGraph
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

# Optional Twilio (only if secrets are provided)
try:
    from twilio.rest import Client as TwilioClient
except Exception:
    TwilioClient = None

# ---- Environment only (avoid st.secrets when not configured) ----
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")

# ---- LLMs ----
if GROQ_API_KEY:
    main_llm = ChatGroq(model="openai/gpt-oss-20b", groq_api_key=GROQ_API_KEY, temperature=0.7, top_p=0.9)
    therapist_llm = ChatGroq(model="openai/gpt-oss-20b", groq_api_key=GROQ_API_KEY, temperature=0.7, top_p=0.9)
else:
    main_llm = None
    therapist_llm = None

# ---- System Prompt ----
SYSTEM_PROMPT = """
You are "Friday", an AI mental health assistant with three modes of operation:
1. **General Q&A Mode**: If the user is asking a factual, casual, or non-emotional question, respond directly without using any tools.
2. **Therapeutic Mode**: If the user shares emotional concerns, mental health struggles, or seeks personal guidance, use the `ask_mental_health_specialist` tool.
3. **Emergency Mode**: If the user mentions suicidal thoughts, self-harm, or being in immediate danger, IMMEDIATELY call the `call_emergency_services` tool.

Rules for Decision Making:
- Always first assess the emotional and safety level of the user's message.
- If the situation involves emotional distress but not immediate danger → Use `ask_mental_health_specialist`.
- If there are any indicators of self-harm, suicide, or danger to self/others → Use `call_emergency_services` without hesitation.
- Otherwise, answer directly as a friendly and helpful AI.

Tone Guidelines:
- Empathetic, warm, and understanding for all emotional interactions.
- Concise and clear for general queries.
- Urgent and safety-focused for emergencies.

You have access to:
- ask_mental_health_specialist(prompt: str)
- call_emergency_services(phone: str)
"""

# ---- Tools ----
@tool
def ask_mental_health_specialist(prompt: str) -> str:
    """
    Generate a therapeutic response using the primary LLM with a therapist persona.
    Use this ONLY for emotional, mental health, or personal well-being related queries.
    Respond with empathy, evidence-based guidance, and a supportive tone.
    """
    system_prompt = (
        "You are Dr Julie Stark, a warm and experienced clinical psychologist.\n"
        "Respond to patients with:\n\n"
        "1. Emotional attunement (\"I can see that you're feeling...\")\n"
        "2. Gentle normalization (\"Many people feel this way...\")\n"
        "3. Practical guidance (\"What sometimes helps is...\")\n"
        "4. Strengths-focused support (\"I notice how you're...\")\n\n"
        "Key principles:\n"
        "- Never use brackets or labels\n"
        "- Blend elements seamlessly\n"
        "- Vary sentence structure\n"
        "- Use natural transitions\n"
        "- Mirror the user's language and tone\n"
        "- Use a warm, empathetic tone\n"
        "- Always keep the conversation going by asking open-ended questions to explore root causes"
    )
    if therapist_llm is None:
        return (
            "The assistant is not fully configured (missing GROQ_API_KEY). "
            "Please try again after the server is configured."
        )
    try:
        resp = therapist_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ])
        return (resp.content or "").strip()
    except Exception:
        return (
            "I'm having technical difficulties right now, but I want you to know your feelings matter. "
            "Please try again later."
        )

@tool
def call_emergency_services(phone: str) -> str:
    """
    Place an emergency call to the provided phone number via Twilio (if configured).
    Use this ONLY if the user expresses suicidal thoughts, self-harm, immediate danger, or a mental health crisis.
    """
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER and TwilioClient):
        return (
            "Emergency call could not be initiated because telephony is not configured. "
            "Please dial your local emergency number immediately."
        )
    try:
        client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        call = client.calls.create(
            to=phone,
            from_=TWILIO_FROM_NUMBER,
            url="http://demo.twilio.com/docs/voice.xml",
        )
        return (
            f"A critical situation alert has been triggered. The emergency helpline is now calling {phone}. "
            f"Call SID: {call.sid}. Please stay safe and on the line."
        )
    except Exception as e:
        return (
            f"Emergency call attempt failed (error: {e}). Please contact your local emergency services immediately."
        )

TOOLS = [ask_mental_health_specialist, call_emergency_services]

# ---- Agent Graph ----
graph = create_react_agent(main_llm, tools=TOOLS) if main_llm is not None else None

# ---- Stream parsing (adapted from backend) ----
def parse_response(stream):
    tool_called_name = "None"
    final_response = ""
    for step in stream:
        messages_to_process = []
        if "__root__" in step and isinstance(step["__root__"], dict) and "messages" in step["__root__"]:
            messages_to_process.extend(step["__root__"]["messages"])
        elif "agent" in step and isinstance(step["agent"], dict) and "messages" in step["agent"]:
            messages_to_process.extend(step["agent"]["messages"])
        for msg in messages_to_process:
            if isinstance(msg, BaseMessage):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    if msg.tool_calls[0].get("name"):
                        tool_called_name = msg.tool_calls[0]["name"]
                if isinstance(msg.content, str):
                    final_response += msg.content
    return tool_called_name, final_response.strip()

# ---- Streamlit UI (Chat-only) ----
st.set_page_config(page_title="SafeSpace - Friday", page_icon="🧠", layout="centered")
st.title("🧠 SafeSpace • Friday")
st.caption("Confidential mental health support. This interface provides chat only.")

# Session state
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "name" not in st.session_state:
    st.session_state.name = ""
if "phone" not in st.session_state:
    st.session_state.phone = ""
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {role: "user"|"assistant", content: str}

with st.sidebar:
    st.header("Session")
    name = st.text_input("Your name", value=st.session_state.name)
    phone = st.text_input("Your phone (for emergencies)", value=st.session_state.phone, help="Optional but recommended for safety.")
    col1, col2 = st.columns(2)
    with col1:
        start = st.button("Start session" if not st.session_state.session_id else "Restart")
    with col2:
        clear = st.button("Clear chat")

    if start:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.name = name.strip() or "there"
        st.session_state.phone = phone.strip()
        st.session_state.messages = []
        greeting = (
            f"Hello {st.session_state.name}, I'm Friday. We can chat here. "
            f"If you ever indicate an emergency, I may attempt to call the provided number for help."
        )
        st.session_state.messages.append({"role": "assistant", "content": greeting})

    if clear:
        st.session_state.messages = []

# Display current chat history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Chat input (only enabled after starting session)
user_input = st.chat_input("Type your message...", disabled=not st.session_state.session_id)
if user_input:
    # Show user's message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build session context
    name = st.session_state.name or "there"
    phone = st.session_state.phone or ""
    session_context = (
        f"User name: {name}. User phone: {phone}. "
        f"When using call_emergency_services(phone), always pass this exact phone number: {phone}. "
        f"Agent name is Friday."
    )

    # Prepare inputs and get streamed response
    inputs = {
        "messages": [
            ("system", SYSTEM_PROMPT),
            ("system", session_context),
            ("user", user_input),
        ]
    }

    with st.chat_message("assistant"):
        if graph is None:
            st.error("Server not configured. Please set GROQ_API_KEY in your environment and restart.")
            final_response = ""
        else:
            with st.spinner("Friday is thinking..."):
                tool_called_name, final_response = parse_response(
                    graph.stream(inputs, stream_mode="updates")
                )
                st.markdown(final_response or "(No response)")
                if tool_called_name and tool_called_name != "None":
                    st.caption(f"Tool used: {tool_called_name}")

    # Save assistant message
    st.session_state.messages.append({"role": "assistant", "content": final_response or ""})
