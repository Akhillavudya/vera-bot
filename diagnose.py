"""
diagnose.py — simulates exactly what /v1/tick does
Run: python diagnose.py
This will show the EXACT error causing the fallback to fire.
"""
import os
import json
import traceback

# Remove conflicting key
if "GOOGLE_API_KEY" in os.environ:
    del os.environ["GOOGLE_API_KEY"]

print("=" * 60)
print("STEP 1 — checking imports")
print("=" * 60)

try:
    from google import genai
    from google.genai import types
    print("[OK] google.genai imported")
except Exception as e:
    print(f"[FAIL] google.genai import: {e}")
    exit(1)

try:
    from store import load_store
    print("[OK] store imported")
except Exception as e:
    print(f"[FAIL] store: {e}")
    exit(1)

try:
    from rag_store import format_for_prompt
    print("[OK] rag_store imported")
except Exception as e:
    print(f"[FAIL] rag_store: {e}")
    exit(1)

try:
    from signal_ranker import pick_best_trigger
    print("[OK] signal_ranker imported")
except Exception as e:
    print(f"[FAIL] signal_ranker: {e}")
    exit(1)

print()
print("=" * 60)
print("STEP 2 — checking store contents")
print("=" * 60)

store = load_store()
for key in ["category", "merchant", "customer", "trigger"]:
    items = store.get(key, {})
    print(f"  {key}: {len(items)} items — {list(items.keys())[:3]}")

print()
print("=" * 60)
print("STEP 3 — checking Gemini API key")
print("=" * 60)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("[FAIL] GEMINI_API_KEY not set")
    exit(1)
print(f"[OK] GEMINI_API_KEY: {api_key[:10]}...")

print()
print("=" * 60)
print("STEP 4 — test raw Gemini call")
print("=" * 60)

client = genai.Client(api_key=api_key)
MODEL  = "gemini-2.5-flash"

try:
    r = client.models.generate_content(
        model=MODEL,
        contents="Return this JSON: {\"body\": \"hello\", \"cta\": \"reply yes\", \"send_as\": \"vera\", \"rationale\": \"test\"}",
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=200,
            response_mime_type="application/json",
        ),
    )
    print(f"[OK] Gemini responded: {r.text[:200]}")
    parsed = json.loads(r.text)
    print(f"[OK] JSON parsed: {parsed}")
except Exception as e:
    print(f"[FAIL] Gemini call failed:\n{traceback.format_exc()}")
    exit(1)

print()
print("=" * 60)
print("STEP 5 — simulate full compose with real store data")
print("=" * 60)

# get first available merchant and trigger
merchants = store.get("merchant", {})
triggers  = store.get("trigger",  {})
categories= store.get("category", {})

if not merchants:
    print("[FAIL] No merchants in store — run judge_simulator.py warmup first")
    print("       or push context manually via POST /v1/context")
    exit(1)

if not triggers:
    print("[FAIL] No triggers in store — run judge_simulator.py first")
    exit(1)

# pick first merchant and trigger
merchant_id    = list(merchants.keys())[0]
trigger_id     = list(triggers.keys())[0]
merchant       = merchants[merchant_id]["payload"]
trigger        = triggers[trigger_id]["payload"]
category_slug  = merchant.get("category_slug", "business")
category       = categories.get(category_slug, {}).get("payload", {"slug": category_slug})

print(f"  Merchant: {merchant.get('identity',{}).get('name','?')} ({merchant_id})")
print(f"  Trigger:  {trigger_id} kind={trigger.get('kind','?')}")
print(f"  Category: {category_slug}")

print()
print("STEP 5a — building prompt...")
try:
    from app import build_compose_prompt
    # wrap trigger in expected format
    trigger_wrapper = {"payload": trigger, "kind": trigger.get("kind", "unknown")}
    prompt = build_compose_prompt(category, merchant, trigger_wrapper)
    print(f"[OK] Prompt built — {len(prompt)} chars")
    print(f"     First 300 chars:\n{prompt[:300]}")
except Exception as e:
    print(f"[FAIL] build_compose_prompt crashed:\n{traceback.format_exc()}")
    exit(1)

print()
print("STEP 5b — calling Gemini with full prompt...")
try:
    SYSTEM = """You are Vera, magicpin's merchant AI. Output valid JSON only.
{
  "body": "message body",
  "cta": "call to action",
  "send_as": "vera",
  "rationale": "one sentence"
}"""

    r = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            temperature=0.0,
            max_output_tokens=1024,
            response_mime_type="application/json",
        ),
    )
    print(f"[OK] Gemini responded!")
    print(f"     Raw response:\n{r.text[:500]}")
    
    parsed = json.loads(r.text)
    print(f"\n[OK] Parsed successfully!")
    print(f"     body: {parsed.get('body','MISSING')[:100]}")
    print(f"     cta:  {parsed.get('cta','MISSING')}")
    print(f"     send_as: {parsed.get('send_as','MISSING')}")
    print(f"     rationale: {parsed.get('rationale','MISSING')[:80]}")
    
    print()
    print("=" * 60)
    print("ALL STEPS PASSED — Gemini compose is working!")
    print("The fallback in app.py is NOT being triggered by compose.")
    print("Check: is the server restarted after changing _MODEL?")
    print("=" * 60)

except Exception as e:
    print(f"[FAIL] Gemini full compose failed:\n{traceback.format_exc()}")
    print()
    print("THIS IS THE ROOT CAUSE OF YOUR FALLBACK")