from langchain.agents import tool
from tools import query_medgemma, call_emergency_contact
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
# Import necessary LangChain message classes for robust stream parsing
from langchain_core.messages import AIMessage, ToolMessage, BaseMessage 

import os
from dotenv import load_dotenv
load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

# ---- Tools ----
@tool
def ask_mental_health_specialist(prompt: str) -> str:
    """
    Generate a therapeutic response using the MedGemma model.
    Use this ONLY for emotional, mental health, or personal well-being related queries.
    Respond with empathy, evidence-based guidance, and supportive tone.
    """
    return query_medgemma(prompt)

@tool
def call_emergency_services(phone: str) -> str:
    """
    Place an emergency call to the safety helpline's phone number via Twilio.
    Use this ONLY if the user expresses suicidal thoughts, self-harm, immediate danger, or a mental health crisis.
    """
    return call_emergency_contact(phone)

tools = [ask_mental_health_specialist, call_emergency_services]

# ---- LLM Setup ----
llm = ChatGroq(model="openai/gpt-oss-20b", groq_api_key=groq_api_key, temperature=0.7, top_p=0.9)

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

# ---- Agent Graph ----
graph = create_react_agent(llm, tools=tools)

# ---- UPDATED PARSING FUNCTION FOR LANGGRAPH REACT AGENT STREAM ----
def parse_response(stream):
    """
    Parses the stream output from a langgraph ReAct agent to extract the tool called and the final response text.
    
    The stream contains state updates (dictionaries). We accumulate the content 
    and look for tool_calls within the AIMessage objects.
    """
    tool_called_name = "None"
    final_response = ""

    # Iterate through the stream of state updates
    for step in stream:
        messages_to_process = []
        
        # Langgraph streams output can be nested under '__root__' or 'agent'
        # Get messages from the current step
        if '__root__' in step and isinstance(step['__root__'], dict) and 'messages' in step['__root__']:
             # Use the latest messages from the root state
             messages_to_process.extend(step['__root__']['messages'])
        elif 'agent' in step and isinstance(step['agent'], dict) and 'messages' in step['agent']:
             # Messages from the specific agent step
             messages_to_process.extend(step['agent']['messages'])

        # Process all extracted messages in this step
        for msg in messages_to_process:
            # Check if the message is a BaseMessage
            if isinstance(msg, BaseMessage):
                # 1. Check for tool calls (these are usually in the AIMessage just before the tool is executed)
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # We assume only one tool is called at a time
                    if msg.tool_calls[0].get('name'):
                        tool_called_name = msg.tool_calls[0]['name']
                
                # 2. Accumulate content
                # This accumulates the text being streamed (including the final answer)
                if isinstance(msg.content, str):
                    final_response += msg.content
                
    # Use strip() to clean up any leading/trailing whitespace from streaming
    return tool_called_name, final_response.strip()

# if __name__ == "__main__":
#     while True:
#         user_input = input("User: ")
#         print(f"Received user input: {user_input[:200]}...")
#         inputs = {"messages": [("system", SYSTEM_PROMPT), ("user", user_input)]}
#         stream = graph.stream(inputs, stream_mode="updates")
#         tool_called_name, final_response = parse_response(stream)
#         print("TOOL CALLED: ", tool_called_name)
#         print("ANSWER: ", final_response)
