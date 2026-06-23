import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add workspace path to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_service import parse_command_gemini

def test_assistant_fallback():
    print("Testing Assistant Fallback to Groq...")
    
    # Temporarily rename .env so load_dotenv() doesn't load it
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env'))
    tmp_env_path = env_path + '.tmp'
    
    env_renamed = False
    if os.path.exists(env_path):
        os.rename(env_path, tmp_env_path)
        env_renamed = True
        
    original_key = os.environ.get("GEMINI_API_KEY")
    original_key_2 = os.environ.get("GEMINI_API_KEY_2")
    original_google_key = os.environ.get("GOOGLE_API_KEY")
    original_groq_key = os.environ.get("GROQ_API_KEY")
    
    # Set them to invalid values to trigger Gemini failures
    os.environ["GEMINI_API_KEY"] = "invalid_key"
    os.environ["GEMINI_API_KEY_2"] = "invalid_key"
    os.environ["GOOGLE_API_KEY"] = "invalid_key"
    if original_groq_key:
        os.environ["GROQ_API_KEY"] = original_groq_key
    
    from ai_service import get_gemini_api_keys
    print("Keys in pool:", get_gemini_api_keys())
    
    context = {
        "customers": [{"id": "C001", "name": "Arjun Mehta", "balance": 5000}],
        "products": [],
        "invoices": []
    }
    history = []
    
    try:
        # This will fail on Gemini and fall back to Groq
        result = parse_command_gemini(
            user_text="Mark INV-001 as paid",
            context=context,
            history=history,
            api_key="invalid_key",
            language="en-IN"
        )
        print("Success! Fallback response received:")
        print(result)
    except Exception as e:
        print("Test failed with exception:", e)
    finally:
        # Restore environment
        if original_key:
            os.environ["GEMINI_API_KEY"] = original_key
        else:
            os.environ.pop("GEMINI_API_KEY", None)
            
        if original_key_2:
            os.environ["GEMINI_API_KEY_2"] = original_key_2
        else:
            os.environ.pop("GEMINI_API_KEY_2", None)
            
        if original_google_key:
            os.environ["GOOGLE_API_KEY"] = original_google_key
        else:
            os.environ.pop("GOOGLE_API_KEY", None)
            
        if env_renamed:
            os.rename(tmp_env_path, env_path)

if __name__ == "__main__":
    test_assistant_fallback()
