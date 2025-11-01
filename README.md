# SafeSpace · Friday (Mental Health Chat) 
🔗 Live App: https://safespace-ai.streamlit.app/

A confidential, chat-only mental health support app built with Streamlit. It runs as a single-file app (`app.py`) and uses a ReAct-style agent powered by Groq via LangChain / LangGraph. The assistant “Friday” can:

- Provide empathetic, therapist‑style responses.
- Detect high‑risk statements and optionally trigger an emergency call via Twilio (if configured).
- Maintain session context (name and phone) to personalize and pass the correct number to the emergency tool.

## Features

- Single-file Streamlit app: Frontend and backend unified in `app.py` for easy local runs and Streamlit Cloud hosting.
- Chat-only UI: Voice features intentionally removed for deployment simplicity.
- ReAct agent: Built with LangGraph and `langchain_groq` LLMs.
- Two tools:
  - `ask_mental_health_specialist(prompt)` – produces supportive, therapist-like responses.
  - `call_emergency_services(phone)` – optional Twilio call-out for emergencies (safe fallback if not configured).
- Session context injection: Ensures the agent uses the correct phone number when invoking the emergency tool.
- Cloud-friendly: Works with environment variables; no separate FastAPI server needed.

## Architecture

- LLM: Groq via `langchain_groq` using the `openai/gpt-oss-20b` model.
- Agent: ReAct agent created with `langgraph.prebuilt.create_react_agent`.
- Tools: Implemented via `@tool` from `langchain_core.tools`.
- UI: Streamlit. Sidebar manages session (name/phone/start/clear). Main area displays chat.
- Emergency call: Twilio (optional). If not configured, the tool returns a safe text fallback.
- Legacy backend: The `backend/` folder (FastAPI, tools) remains, but is not required for Streamlit deployment.

## Project Structure

```
.
├─ app.py                 # Single-file Streamlit app (frontend + agent + tools)
├─ backend/
│  ├─ main.py             # Legacy FastAPI (not required for Streamlit)
│  ├─ ai_agent.py         # Legacy agent setup
│  ├─ tools.py            # Legacy tools (Ollama/Twilio)
│  └─ config.py           # Legacy config (do not commit real secrets)
└─ README.md
```

## Requirements

- Python 3.10+ recommended
- `streamlit`
- `langchain`, `langgraph`, `langchain-groq`
- `pydantic`, `python-dotenv`
- `twilio` (optional; only if you enable the emergency call tool)

Example `requirements.txt`:

```
streamlit
langchain
langgraph
langchain-groq
pydantic
python-dotenv
# Optional for emergency calling
twilio
```

## Configuration

The app reads configuration from environment variables. A `.env` at repo root is supported via `python-dotenv`.

Required:
- `GROQ_API_KEY`

Optional (only if using emergency call tool):
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`

Example `.env`:

```
GROQ_API_KEY=your_groq_api_key
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=+1234567890
```

## Run Locally

1. Install dependencies (venv recommended):
   ```bash
   pip install -r requirements.txt
   # or install the packages listed above manually
   ```
2. Provide environment variables (either via `.env` or your shell):
   ```bash
   # PowerShell (Windows, current session)
   $env:GROQ_API_KEY = "<your_key>"
   ```
3. Start the app:
   ```bash
   streamlit run app.py
   ```
4. Open the provided local URL in your browser.

## Deploy to Streamlit Cloud

1. Push this repo to GitHub.
2. Create a Streamlit Cloud app pointing to `app.py`.
3. In the app’s settings, set environment variables (or Secrets):
   - `GROQ_API_KEY`
   - Optionally: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
4. Deploy; the app should come up with the chat UI. If `GROQ_API_KEY` is missing, the UI will display a config error and avoid creating the LLM/agent.

## Usage

- Use the sidebar to enter your name and phone and click “Start session”.
- Chat in the main panel. Friday may use the therapeutic tool for emotional concerns, and trigger the emergency tool if a crisis is detected.
- If Twilio is not configured, emergency calls will not be placed; the app will respond with safety guidance.

## Troubleshooting

- ImportError: cannot import name `tool` from `langchain.agents`
  - We import `tool` from `langchain_core.tools` for compatibility with current releases.
- Pydantic warning: `top_p is not default parameter`
  - This is a harmless warning; `top_p` is correctly forwarded to the model.
- StreamlitSecretNotFoundError
  - We use environment variables. If using Streamlit Secrets, add them in Cloud settings.
- “Server not configured. Please set GROQ_API_KEY”
  - Set `GROQ_API_KEY` and restart.
- Emergency tool disabled
  - Ensure `TWILIO_*` env vars are set and reachable from your environment.

## Security & Privacy

- Do not commit real API keys or phone numbers to version control.
- This app is not a substitute for professional care. In emergencies, always call local emergency services directly.

## License

This project is provided under your preferred license. If not yet specified, consider adding a license file (e.g., MIT).

## Acknowledgements

- Built on Streamlit, LangChain, LangGraph, and Groq.
- Emergency call integration powered by Twilio (optional).
