"""
test_gemini.py — run this first to verify Gemini works
Command:
  $env:GEMINI_API_KEY="your-key"   (PowerShell)
  python test_gemini.py
"""
import os
import json

# Remove conflicting key before importing
if "GOOGLE_API_KEY" in os.environ:
    print("WARNING: GOOGLE_API_KEY is set — removing it to avoid conflict")
    del os.environ["GOOGLE_API_KEY"]

from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY not set")
    print('Run: $env:GEMINI_API_KEY="your-key-here"')
    exit(1)

print(f"Using GEMINI_API_KEY: {api_key[:10]}...")

client = genai.Client(api_key=api_key)

# First: list available models so we know what to use
print("\nFetching available models...")
try:
    models = client.models.list()
    flash_models = [m.name for m in models if "flash" in m.name.lower()]
    print(f"Flash models available: {flash_models}")
except Exception as e:
    print(f"Could not list models: {e}")

# Try models in order of preference
MODEL_CANDIDATES = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-2.0-flash-exp",
    "gemini-2.5-flash",
]

working_model = None
for model_name in MODEL_CANDIDATES:
    print(f"\nTrying model: {model_name}")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents='Return this exact JSON: {"status": "working", "score": 50}',
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=100,
                response_mime_type="application/json",
            ),
        )
        print(f"  Response: {response.text}")
        parsed = json.loads(response.text)
        print(f"  Parsed OK: {parsed}")
        print(f"\n✓ WORKING MODEL: {model_name}")
        working_model = model_name
        break
    except Exception as e:
        print(f"  FAILED: {e}")

if working_model:
    print(f"\nUpdate _MODEL in app.py to: '{working_model}'")
else:
    print("\nNo working model found. Check your API key at aistudio.google.com")
# """
# test_gemini.py — run this to check if Gemini is working
# Command: python test_gemini.py
# """
# import os
# import json
# from google import genai
# from google.genai import types

# api_key = os.environ.get("GEMINI_API_KEY")
# if not api_key:
#     print("ERROR: GEMINI_API_KEY not set")
#     exit(1)

# print(f"API key found: {api_key[:8]}...")

# client = genai.Client(api_key=api_key)

# try:
#     response = client.models.generate_content(
#         model="gemini-2.0-flash",
#         contents="Return this exact JSON object: {\"status\": \"working\", \"score\": 50}",
#         config=types.GenerateContentConfig(
#             temperature=0.0,
#             max_output_tokens=100,
#             response_mime_type="application/json",
#         ),
#     )
#     print(f"Raw response: {response.text}")
#     parsed = json.loads(response.text)
#     print(f"Parsed OK: {parsed}")
#     print("\nGemini is working correctly.")

# except Exception as e:
#     import traceback
#     print(f"GEMINI FAILED:\n{traceback.format_exc()}")