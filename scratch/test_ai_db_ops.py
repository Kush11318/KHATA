import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add workspace path to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_service import parse_command_gemini

def run_tests():
    context = {
        "customers": [
            {"id": "C001", "name": "Arjun Mehta", "balance": 5000, "phone": "1234567890", "address": "Mumbai"}
        ],
        "products": [
            {"id": "P001", "name": "Keyboard", "price": 199.99, "stock": 45},
            {"id": "P002", "name": "Mouse", "price": 99.99, "stock": 12}
        ],
        "invoices": []
    }
    history = []
    
    # We will use the primary Gemini API key from environment to perform a real call
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not configured. Skipping live API test.")
        return
        
    print("Testing Price Update...")
    r1 = parse_command_gemini(
        user_text="update price of Keyboard to 250",
        context=context,
        history=history,
        api_key=api_key,
        language="en-IN"
    )
    print("Result 1 (Price Update):")
    print(r1)
    
    print("\nTesting Stock Update (Hinglish):")
    r2 = parse_command_gemini(
        user_text="Mouse ka stock 50 kar do",
        context=context,
        history=history,
        api_key=api_key,
        language="en-IN"
    )
    print("Result 2 (Stock Update):")
    print(r2)
    
    print("\nTesting Customer Address Update:")
    r3 = parse_command_gemini(
        user_text="Arjun Mehta ka address Delhi set kar do",
        context=context,
        history=history,
        api_key=api_key,
        language="en-IN"
    )
    print("Result 3 (Customer Details Update):")
    print(r3)

if __name__ == "__main__":
    run_tests()
