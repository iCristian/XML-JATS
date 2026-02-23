import google.generativeai as genai
import os

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")
resp = model.generate_content("Escribe un poema de 10 palabras.", generation_config=genai.types.GenerationConfig(max_output_tokens=5))
print(f"Text: {resp.text}")
print(f"Finish reason: {resp.candidates[0].finish_reason}")
print(f"Type: {type(resp.candidates[0].finish_reason)}")
