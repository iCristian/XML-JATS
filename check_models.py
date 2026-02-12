import os
import google.generativeai as genai

# Try to get key from env, otherwise fail gracefully
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    # Try to grab it from the Streamlit config if possible, but that's hard from a standalone script without context.
    # We will rely on the user having set it in the terminal or .env for this debug script.
    print("WARNING: GEMINI_API_KEY is not set in environment.")
    print("Please run: export GEMINI_API_KEY='your_key' && python3 check_models.py")
else:
    print(f"Using API Key: {api_key[:5]}...{api_key[-5:]}")
    genai.configure(api_key=api_key.strip())
    try:
        print("\n--- Available GEMINI Models ---")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"Name: {m.name}")
                print(f"Display Name: {m.display_name}")
                print(f"Version: {m.version}")
                print("-" * 20)
    except Exception as e:
        print(f"Error calling list_models: {e}")
