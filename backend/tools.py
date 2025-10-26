import ollama
from twilio.rest import Client
# We rely on these being defined in a config.py file
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER

def query_medgemma(prompt: str) -> str:
    """
    Calls medgemma model with a therapist personality profile.
    Returns responses as an empathic mental health therapist.
    """
    system_prompt = """
        You are Dr Julie Stark, a warm and experienced clinical pschologist.
        Respond to patients with:
        
        1. Emotional attunement (""I can see that you're feeling...")
        2. Gental normalization ("Many people feel this way...")
        3. Practical guidance ("What sometimes helps is...")
        4. Strengths-focused support ("I Notice how you're...")
        
        key principles: 
        - Never use brackets or labels
        - Blend elements seamlessly
        - vary sentence structure
        - use natural transitions
        - Mirror the users language and tone
        - Use a warm, empathetic tone
        - Always keep the conversation going by asking open ended questions to dive into root causes of patients problems
    """
    
    try:
        # print("called MedGemma therapist")
        response = ollama.chat(
            model='alibayram/medgemma:4b',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            options={
                'num_predict': 350,
                'temperature': 0.7,
                'top_p': 0.9,
            }
        )
        # Assuming response structure is correct for Ollama
        return response['message']['content'].strip()
    except Exception as e:
        print(f"Error querying MedGemma: {e}")
        return "I'm having technical difficulties right now, but I want you to know your feelings matter. Please try again later."
    
def call_emergency_contact(phone: str) -> str:
    """
    Calls the provided phone number using Twilio.
    Returns a string indicating the result of the tool action.
    """
    try:
        client = Client(
            TWILIO_ACCOUNT_SID,
            TWILIO_AUTH_TOKEN
        )
        call = client.calls.create(
            to=phone,
            from_=TWILIO_FROM_NUMBER,
            url="http://demo.twilio.com/docs/voice.xml"  # Replace with your TwiML URL
        )
        # Important: Return a string for the agent to use
        return f"A critical situation alert has been successfully triggered. The emergency helpline is now calling the number: {phone}. The call SID is {call.sid}. Please wait a moment."
    except Exception as e:
        # Important: Return a string for the agent to use in case of failure
        error_message = f"Emergency call attempt failed. Error: {e}. Please contact a local emergency service immediately by dialing 911 (or your local equivalent)."
        print(error_message)
        return error_message
