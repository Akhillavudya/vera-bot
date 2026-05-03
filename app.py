from fastapi import FastAPI
from datetime import datetime, timezone

from schemas import ContextIn, TickIn, ReplyIn
from store import (
    put_context, 
    count_contexts, 
    load_store, 
    get_conversation, 
    save_conversation
)

# New Smart Logic Imports
from signal_ranker import pick_best_trigger
from templates import research_template, recall_template, perf_dip_template
from policies import get_category_policy, clean_offer_text

app = FastAPI(title="VERA Bot", version="1.0.0")

@app.get("/")
def root():
    return {"status": "VERA Bot running"}

@app.get("/v1/healthz")
def healthz():
    return {
        "status": "ok",
        "uptime_seconds": 0,
        "contexts_loaded": count_contexts()
    }

@app.get("/v1/metadata")
def metadata():
    return {
        "team_name": "Akhil VERA Bot",
        "team_members": ["Lavudya Akhil"],
        "model": "dynamic-signal-engine",
        "approach": "Weighted Ranking + Category Constraints + Clean Reasoning",
        "contact_email": "akhillavudya4567@gmail.com",
        "version": "1.0.0",
        "submitted_at": datetime.now(timezone.utc).isoformat()
    }

@app.post("/v1/context")
def receive_context(ctx: ContextIn):
    return put_context(
        scope=ctx.scope,
        context_id=ctx.context_id,
        version=ctx.version,
        payload=ctx.payload
    )

def get_best_offer(merchant_payload: dict, policy: dict) -> str:
    offers = merchant_payload.get("offers", [])
    for offer in offers:
        if offer.get("status") == "active":
            return offer.get("title", "")
    return policy.get("default_offer", "Exclusive Benefit")

@app.post("/v1/tick")
def tick(req: TickIn):
    store = load_store()

    if not req.available_triggers:
        return {"actions": []}

    # STEP 2: Smart Ranking applied here
    trigger_id = pick_best_trigger(req.available_triggers, store)
    if not trigger_id:
        return {"actions": []}

    trigger = store["trigger"].get(trigger_id)
    merchant_id = trigger["payload"].get("merchant_id") if trigger else None
    merchant = store["merchant"].get(merchant_id) if merchant_id else None

    if not trigger or not merchant:
        return {"actions": []}

    trigger_payload = trigger["payload"]
    merchant_payload = merchant["payload"]
    
    # Policy and Identity Setup
    category = merchant_payload.get("category_slug", "business")
    policy = get_category_policy(category)
    locality = merchant_payload.get("identity", {}).get("locality", "your area")
    
    # STEP 3: Clean the offer title based on Industry Guardrails
    raw_offer = get_best_offer(merchant_payload, policy)
    safe_offer = clean_offer_text(raw_offer, policy.get("avoid", []))
    
    # Apply Professional Prefix
    merchant_name = merchant_payload["identity"]["name"]
    prefix = policy.get("prefix", "")
    if prefix:
        words_in_name = merchant_name.lower().split()
        if prefix.lower() not in words_in_name and category.lower() not in words_in_name:
          merchant_name = f"{prefix} {merchant_name}"

    # Data Extraction
    ctr = merchant_payload.get("performance", {}).get("ctr", 0)
    lapsed = merchant_payload.get("customer_aggregate", {}).get("lapsed_180d_plus", 0)
    kind = trigger_payload.get("kind", "")
    signals = merchant_payload.get("signals", [])

    # STEP 1b: Logic Decoupling (Templates handle the body)
    if kind == "recall_due":
        body, cta = recall_template(merchant_name, lapsed, safe_offer, locality)
        rationale = f"Prioritizing retention: {lapsed} customers represent high recovery value."

    elif kind == "perf_dip":
        body, cta = perf_dip_template(merchant_name, ctr, safe_offer, locality)
        rationale = f"Urgent action: CTR dropped to {ctr:.2%}. Optimization required."

    elif kind in ["research_digest", "research_digest_release"]:
        body, cta = research_template(merchant_name, category, locality)
        rationale = "Stable performance; providing industry insights to maintain engagement."

    else:
        # Instead of "I've identified a growth op...", use industry data
        industry_metric = policy.get("industry_metric", "performance")
        body = (f"{merchant_name}, I'm analyzing your {locality} branch data. "
                f"Your {industry_metric} shows room for growth with a new {safe_offer}.")
        cta = f"Shall I show you how we can boost your {industry_metric}?"
        rationale = f"Fallback optimization using {industry_metric} for {category}."

    # Contextual Signal Injection
    if "low_footfall" in signals and kind != "perf_dip":
        body = f"With local footfall currently low, {body}"

    suppression_key = trigger_payload.get("suppression_key", f"sup_{trigger_id}")

    action = {
        "conversation_id": f"conv_{trigger_id}",
        "merchant_id": merchant_id,
        "customer_id": trigger_payload.get("customer_id"),
        "send_as": "vera",
        "trigger_id": trigger_id,
        "template_name": "basic_template",
        "template_params": [],
        "body": body,
        "cta": cta,
        "suppression_key": suppression_key,
        "rationale": rationale
    }

    save_conversation(action["conversation_id"], {
        "trigger_id": trigger_id,
        "kind": kind,
        "merchant_id": merchant_id,
        "lapsed": lapsed,
        "offer": safe_offer
    })

    return {"actions": [action]}

@app.post("/v1/reply")
def reply(req: ReplyIn):
    msg = req.message.lower().strip()
    convo = get_conversation(req.conversation_id)
    kind = convo.get("kind") if convo else None
    lapsed = convo.get("lapsed", 0) if convo else 0
    offer = convo.get("offer", "benefit") if convo else "benefit"

    # 1. Auto-reply detection
    if any(phrase in msg for phrase in ["thank you for contacting", "office hours", "will get back"]):
        return {
            "action": "end",
            "rationale": "Detected Business Auto-reply; terminating turn."
        }

    # 2. Refusal logic
    if any(phrase in msg for phrase in ["stop", "no", "not interested", "spam"]):
        return {
            "action": "end",
            "rationale": "Merchant declined; ending session politely."
        }

    # 3. Positive intent with Action-Oriented replies
    if any(word in msg for word in ["yes", "ok", "sure", "do it", "haan"]):
        if kind == "recall_due":
            body = f"Understood. I'm initiating the recall for those {lapsed} customers now. I'll prioritize those who haven't visited in 180+ days first."
        elif kind == "perf_dip":
            body = f"Great. I'm activating the {offer} creative now. We should see the CTR stabilize within 48 hours."
        elif kind in ["research_digest", "research_digest_release"]:
            body = "Done — I’ll send a 2-min summary and a customer-friendly version you can forward to your team."
        else:
            body = "Done — I’ll keep it short, specific, and easy for customers to engage with."

        return {
            "action": "send",
            "body": body,
            "cta": "Reply STOP anytime.",
            "rationale": f"Confirmed action for {kind}."
        }

    # 4. Ambiguity
    return {
        "action": "send",
        "body": "Should I go ahead with this? Reply YES or NO.",
        "cta": "Reply YES or NO.",
        "rationale": "Clarification needed for non-binary reply."
    }

# """
# VERA Bot v3.6 — Fixes merchant ID mismatch (root cause of 15ms fallback)

# Root cause: trigger says merchant_id="001" but store has "m_001_drmeera..."
# Fix: fuzzy merchant lookup tries exact → prefix → substring match

# PowerShell:
#   Remove-Item Env:GOOGLE_API_KEY
#   $env:GEMINI_API_KEY="your-key"
#   uvicorn app:app --host 0.0.0.0 --port 8080
# """

# import os
# import json
# import re
# import traceback
# from datetime import datetime, timezone

# if "GOOGLE_API_KEY" in os.environ:
#     del os.environ["GOOGLE_API_KEY"]

# from google import genai
# from google.genai import types
# from fastapi import FastAPI

# from schemas import ContextIn, TickIn, ReplyIn
# from store import (
#     put_context, count_contexts, load_store,
#     get_conversation, save_conversation, mark_suppressed,
# )
# from signal_ranker import pick_best_trigger
# from rag_store import get_examples, get_levers

# _api_key = os.environ.get("GEMINI_API_KEY")
# if not _api_key:
#     raise RuntimeError("GEMINI_API_KEY not set! Run: $env:GEMINI_API_KEY='your-key'")

# _client = genai.Client(api_key=_api_key)
# _MODEL  = "gemini-2.5-flash"

# app = FastAPI(title="VERA Bot", version="3.6.0")
# print(f"[STARTUP] Model={_MODEL} Key={_api_key[:10]}...")


# # ─────────────────────────────────────────────────────────────────────────────
# # FUZZY MERCHANT LOOKUP — fixes ID mismatch between triggers and store
# # ─────────────────────────────────────────────────────────────────────────────

# def find_merchant(store: dict, merchant_id: str) -> tuple[str | None, dict | None]:
#     """
#     Find merchant by ID with fallback matching.
#     Returns (actual_key, merchant_payload) or (None, None).

#     Tries in order:
#       1. Exact match:     "m_001_drmeera" == "m_001_drmeera"
#       2. Prefix match:    store key starts with merchant_id
#       3. Suffix match:    store key ends with merchant_id
#       4. Substring match: merchant_id appears anywhere in store key
#       5. Numeric match:   extract digits and compare
#     """
#     merchants = store.get("merchant", {})

#     if not merchant_id:
#         return None, None

#     # 1. Exact
#     if merchant_id in merchants:
#         print(f"[LOOKUP] Exact match: {merchant_id}")
#         return merchant_id, merchants[merchant_id]["payload"]

#     # 2. Prefix — store key starts with merchant_id
#     for key in merchants:
#         if key.startswith(merchant_id):
#             print(f"[LOOKUP] Prefix match: '{merchant_id}' → '{key}'")
#             return key, merchants[key]["payload"]

#     # 3. Suffix — store key ends with merchant_id
#     for key in merchants:
#         if key.endswith(merchant_id):
#             print(f"[LOOKUP] Suffix match: '{merchant_id}' → '{key}'")
#             return key, merchants[key]["payload"]

#     # 4. Substring — merchant_id is part of store key
#     for key in merchants:
#         if merchant_id in key:
#             print(f"[LOOKUP] Substring match: '{merchant_id}' → '{key}'")
#             return key, merchants[key]["payload"]

#     # 5. Numeric — extract digits and compare
#     id_digits = re.sub(r"\D", "", merchant_id)
#     if id_digits:
#         for key in merchants:
#             key_digits = re.sub(r"\D", "", key)
#             if id_digits == key_digits and key_digits:
#                 print(f"[LOOKUP] Numeric match: '{merchant_id}' ({id_digits}) → '{key}'")
#                 return key, merchants[key]["payload"]

#     print(f"[LOOKUP] NO MATCH for '{merchant_id}'. Store keys: {list(merchants.keys())}")
#     return None, None


# def find_category(store: dict, category_slug: str) -> dict:
#     """Find category with fallback matching."""
#     categories = store.get("category", {})

#     if category_slug in categories:
#         return categories[category_slug].get("payload", {"slug": category_slug})

#     # try substring
#     for key in categories:
#         if category_slug in key or key in category_slug:
#             print(f"[LOOKUP] Category match: '{category_slug}' → '{key}'")
#             return categories[key].get("payload", {"slug": key})

#     print(f"[LOOKUP] Category '{category_slug}' not found. Available: {list(categories.keys())}")
#     return {"slug": category_slug}


# # ─────────────────────────────────────────────────────────────────────────────
# # SYSTEM PROMPT
# # ─────────────────────────────────────────────────────────────────────────────

# SYSTEM_PROMPT = """You are Vera, magicpin's WhatsApp AI for Indian merchants.

# Judge scores 5 dimensions (0-10 each):
# 1. SPECIFICITY — REAL numbers/dates/prices from context only. Never invent stats.
# 2. CATEGORY FIT — dentists=clinical/peer, salons=warm, restaurants=operator, gyms=coach, pharmacies=precise/trustworthy
# 3. MERCHANT FIT — real name, locality, real active offers, real numbers, honor language pref (Hindi-English mix OK)
# 4. TRIGGER RELEVANCE — clearly say WHY NOW (the specific event that prompted this)
# 5. ENGAGEMENT — strong reason to reply NOW, single CTA as LAST sentence

# Hard rules:
# - Never fabricate numbers not in context
# - Single CTA only, LAST sentence of body
# - No preambles ("I hope you're doing well...")
# - No promotional tone for dentists/pharmacies
# - Never repeat last message verbatim

# Output valid JSON only. No markdown. No explanation. No extra text.
# {"body":"...","cta":"...","send_as":"vera" or "merchant_on_behalf","rationale":"..."}"""


# # ─────────────────────────────────────────────────────────────────────────────
# # GEMINI CALL — max_output_tokens=2048 prevents truncation
# # ─────────────────────────────────────────────────────────────────────────────

# def _call_gemini(prompt: str, max_tokens: int = 2048) -> dict:
#     response = _client.models.generate_content(
#         model=_MODEL,
#         contents=prompt,
#         config=types.GenerateContentConfig(
#             system_instruction=SYSTEM_PROMPT,
#             temperature=0.0,
#             max_output_tokens=max_tokens,
#             response_mime_type="application/json",
#         ),
#     )
#     raw = response.text.strip()
#     raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
#     raw = re.sub(r"\s*```$",          "", raw, flags=re.IGNORECASE)
#     raw = raw.strip()

#     try:
#         return json.loads(raw)
#     except json.JSONDecodeError as e:
#         print(f"[GEMINI] JSON parse failed ({len(raw)} chars): {e}")
#         print(f"[GEMINI] Raw:\n{raw[:400]}")
#         raise


# # ─────────────────────────────────────────────────────────────────────────────
# # RAG BLOCK — compact (1 example) to save tokens
# # ─────────────────────────────────────────────────────────────────────────────

# def _build_rag_block(category_slug: str, trigger_kind: str) -> str:
#     try:
#         examples = get_examples(category_slug, trigger_kind, n=1)
#         levers   = get_levers(trigger_kind)
#         if not examples:
#             return ""
#         ex = examples[0]
#         return (
#             f"=== GOLD EXAMPLE (score {ex['score']}/50) ===\n"
#             f"Body: {ex['body']}\n"
#             f"CTA: {ex['cta']}\n"
#             f"Why high: {ex['voice_notes']}\n\n"
#             f"=== USE THESE LEVERS (pick 2+) ===\n"
#             f"{', '.join(levers)}\n\n"
#             f"=== AVOID (judge penalises) ===\n"
#             f"- 'noticed your account has updates' (generic fallback)\n"
#             f"- '~12% improvement' (fabricated number)\n"
#             f"- Multiple CTAs\n\n"
#             f"Compose NEW message for context below. Same quality, different facts.\n"
#         )
#     except Exception as e:
#         print(f"[RAG] Failed: {e}")
#         return ""


# # ─────────────────────────────────────────────────────────────────────────────
# # COMPOSE PROMPT
# # ─────────────────────────────────────────────────────────────────────────────

# def build_compose_prompt(
#     category: dict,
#     merchant: dict,
#     trigger: dict,
#     customer: dict | None = None,
# ) -> str:
#     identity      = merchant.get("identity", {})
#     performance   = merchant.get("performance", {})
#     # offers        = merchant.get("offers", [])
#     offers        = merchant.get("offers", []) or []
#     offers        = [o for o in offers if isinstance(o, dict)]
#     cust_agg      = merchant.get("customer_aggregate", {})
#     signals       = merchant.get("signals", [])
#     # conv_history  = merchant.get("conversation_history", {})
#     conv_history  = merchant.get("conversation_history", None)
#     active_offers = [o for o in offers if o.get("status") == "active"]
#     paused_offers = [o for o in offers if o.get("status") == "paused"]
#     signals       = merchant.get("signals", []) or []
#     signals       = signals if isinstance(signals, list) else []
#     cust_agg      = merchant.get("customer_aggregate", {}) or {}
#     cust_agg      = cust_agg if isinstance(cust_agg, dict) else {}
#     # last_turns    = conv_history.get("last_turns", [])[-2:] if conv_history else []
#     # last_turns = (conv_history[-2:] if isinstance(conv_history, list) else conv_history.get("last_turns", [])[-2:]) if conv_history else []
#     try:
#        if not conv_history:
#          last_turns = []
#        elif isinstance(conv_history, list):
#          last_turns = conv_history[-2:]
#        elif isinstance(conv_history, dict):
#          last_turns = conv_history.get("last_turns", [])[-2:]
#        else:
#          last_turns = []
#     except Exception:
#         last_turns = []
#     trigger_payload = trigger.get("payload", {})
#     trigger_kind    = trigger_payload.get("kind", trigger.get("kind", "unknown"))
#     urgency         = trigger.get("urgency", trigger_payload.get("urgency", 2))
#     category_slug   = merchant.get("category_slug", category.get("slug", "business"))

#     rag_block    = _build_rag_block(category_slug, trigger_kind)
#     digest_item  = ""
#     if category.get("digest"):
#         d = category["digest"][0]
#         digest_item = f"{d.get('title','')[:120]} (source: {d.get('source','')})"

#     customer_block = ""
#     if customer:
#         ci = customer.get("identity", {})
#         cr = customer.get("relationship", {})
#         cp = customer.get("preferences", {})
#         customer_block = (
#             f"\nCUSTOMER (send on merchant behalf):\n"
#             f"Name={ci.get('name')} State={customer.get('state')} "
#             f"Last visit={cr.get('last_visit','?')} Visits={cr.get('visits_total',0)} "
#             f"Services={cr.get('services_received',[])} "
#             f"Lang={ci.get('language_pref','en')} "
#             f"Preferred time={cp.get('preferred_time','?')}\n"
#             f"send_as MUST be: merchant_on_behalf\n"
#         )
#     else:
#         customer_block = 'send_as MUST be: vera\n'

#     prompt = f"""{rag_block}
# --- TRIGGER ---
# Kind: {trigger_kind} | Urgency: {urgency}/5
# Payload: {json.dumps(trigger_payload, ensure_ascii=False)}

# --- MERCHANT (use ONLY these real facts) ---
# Name: {identity.get("name","Unknown")}
# Locality: {identity.get("locality","")}, {identity.get("city","")}
# Category: {category_slug}
# Languages: {identity.get("languages",["en"])}
# Performance 30d: views={performance.get("views_30d","?")} calls={performance.get("calls_30d","?")} ctr={performance.get("ctr","?")} directions={performance.get("directions_30d","?")}
# Performance 7d delta: views={performance.get("views_7d_delta","?")} calls={performance.get("calls_7d_delta","?")}
# Active offers: {json.dumps(active_offers, ensure_ascii=False)}
# Paused offers: {json.dumps(paused_offers, ensure_ascii=False)}
# Customer aggregate: {json.dumps(cust_agg, ensure_ascii=False)}
# Signals: {json.dumps(signals, ensure_ascii=False)}
# Last conversation: {json.dumps(last_turns, ensure_ascii=False) if last_turns else "None (first outreach)"}

# --- CATEGORY ---
# Peer stats: {json.dumps(category.get("peer_stats",{}), ensure_ascii=False)}
# Voice rules: {json.dumps(category.get("voice",{}), ensure_ascii=False)}
# Seasonal: {json.dumps(category.get("seasonal_beats",[])[:1], ensure_ascii=False)}
# Digest: {digest_item if digest_item else "None"}
# {customer_block}
# Compose now. Use ONLY facts above. Never invent numbers.
# Output valid JSON only."""

#     return prompt


# # ─────────────────────────────────────────────────────────────────────────────
# # VALIDATOR
# # ─────────────────────────────────────────────────────────────────────────────

# _FABRICATION = [
#     "trailing peers by ~", "i'm analyzing your", "studies show",
#     "research indicates", "3x more likely", "industry average", "i've identified",
#     "noticed your", "account has updates pending",
# ]

# def validate_output(composed: dict) -> dict:
#     body = composed.get("body", "")
#     warnings = []
#     if len(body.strip()) < 20:
#         warnings.append("body_too_short")
#     for phrase in _FABRICATION:
#         if phrase in body.lower():
#             warnings.append(f"fabrication: {phrase}")
#     if not composed.get("cta"):
#         warnings.append("missing_cta")
#     if composed.get("send_as") not in ("vera", "merchant_on_behalf"):
#         composed["send_as"] = "vera"
#     if warnings:
#         composed["_warnings"] = warnings
#         print(f"[VALIDATOR] {warnings}")
#     return composed


# def compose_message(
#     category: dict,
#     merchant: dict,
#     trigger: dict,
#     customer: dict | None = None,
# ) -> dict:
#     name = merchant.get("identity", {}).get("name", "?")
#     kind = trigger.get("payload", {}).get("kind", trigger.get("kind", "?"))
#     print(f"[COMPOSE] merchant={name} trigger={kind}")

#     prompt = build_compose_prompt(category, merchant, trigger, customer)
#     print(f"[COMPOSE] prompt={len(prompt)} chars → Gemini...")

# #     # result = _call_gemini(prompt, max_tokens=2048)
# #     result = _call_gemini(prompt, max_tokens=2048)

# # # fill missing fields with safe defaults instead of raising
# #     if "body" not in result or len(result.get("body","")) < 10:
# #          raise ValueError(f"Body missing or too short: {result}")
# #     if "cta" not in result:
# #          result["cta"] = "Reply YES to proceed."
# #     if "send_as" not in result:
# #          result["send_as"] = "vera"
# #     if "rationale" not in result:
# #         result["rationale"] = "Composed based on trigger context."

# #     for field in ("body", "cta", "send_as", "rationale"):
# #         if field not in result:
# #             raise ValueError(f"Missing field: '{field}'")

# #     print(f"[COMPOSE] OK → {result['body'][:100]}")
# #     return validate_output(result)
#     result = _call_gemini(prompt, max_tokens=2048)

#     if "body" not in result or len(result.get("body", "")) < 10:
#          raise ValueError(f"Body missing or too short: {result}")
#     if "cta" not in result:
#          result["cta"] = "Reply YES to proceed."
#     if "send_as" not in result:
#          result["send_as"] = "vera"
#     if "rationale" not in result:
#         result["rationale"] = "Composed based on trigger context."

#     print(f"[COMPOSE] OK → {result['body'][:100]}")
#     return validate_output(result)

# # ─────────────────────────────────────────────────────────────────────────────
# # REPLY PROMPT
# # ─────────────────────────────────────────────────────────────────────────────

# def build_reply_prompt(convo: dict, msg: str) -> str:
#     return f"""You are Vera continuing a WhatsApp conversation with a merchant.

# State: {json.dumps(convo, ensure_ascii=False)}
# Merchant message: "{msg}"

# ROUTING (strict order):
# 1. AUTO-REPLY: "thank you for contacting","office hours","automated","will get back","aapki madad","out of office" → action="end"
# 2. REFUSAL: "stop","not interested","spam","band karo","mat bhejo","nahi chahiye","no thanks" → action="end" body="Samajh gayi — reply START anytime. 🙂"
# 3. POSITIVE: "yes","ok","sure","haan","chalega","do it","kar do","go ahead","bhejo","theek hai" → action="send", SPECIFIC action NOW
# 4. INTENT: "join","subscribe","enroll","mujhe add karo" → onboard immediately
# 5. AMBIGUOUS → ask ONE specific question

# Output valid JSON only:
# {{"action":"send"/"end","body":"(if send)","cta":"(if send)","rationale":"one sentence"}}"""


# # ─────────────────────────────────────────────────────────────────────────────
# # ENDPOINTS
# # ─────────────────────────────────────────────────────────────────────────────

# @app.get("/v1/healthz")
# def healthz():
#     return {"status": "ok", "uptime_seconds": 0, "contexts_loaded": count_contexts()}


# @app.get("/v1/metadata")
# def metadata():
#     return {
#         "team_name":     "Akhil VERA Bot",
#         "team_members":  ["Lavudya Akhil"],
#         "model":         _MODEL,
#         "approach":      f"{_MODEL} + RAG + fuzzy merchant lookup + signal routing",
#         "contact_email": "akhillavudya4567@gmail.com",
#         "version":       "3.6.0",
#         "submitted_at":  datetime.now(timezone.utc).isoformat(),
#     }


# @app.post("/v1/context")
# def receive_context(ctx: ContextIn):
#     return put_context(
#         scope=ctx.scope,
#         context_id=ctx.context_id,
#         version=ctx.version,
#         payload=ctx.payload,
#     )


# @app.post("/v1/tick")
# def tick(req: TickIn):
#     store  = load_store()
#     counts = {k: len(v) for k, v in store.items() if isinstance(v, dict)}
#     print(f"[TICK] Store={counts}")
#     print(f"[TICK] Triggers={req.available_triggers}")

#     if not req.available_triggers:
#         return {"actions": []}

#     trigger_id = pick_best_trigger(req.available_triggers, store)
#     print(f"[TICK] Ranker selected={trigger_id}")

#     if not trigger_id:
#         return {"actions": []}

#     trigger = store["trigger"].get(trigger_id)
#     if not trigger:
#         print(f"[TICK] trigger {trigger_id} missing from store")
#         return {"actions": []}

#     trigger_payload = trigger["payload"]
#     merchant_id     = trigger_payload.get("merchant_id")
#     customer_id     = trigger_payload.get("customer_id")
#     trigger_kind    = trigger_payload.get("kind", trigger.get("kind", trigger_id))

#     print(f"[TICK] kind={trigger_kind} merchant_id={merchant_id}")

#     if not merchant_id:
#         print("[TICK] no merchant_id in trigger payload")
#         return {"actions": []}

#     # ── FUZZY MERCHANT LOOKUP — fixes ID mismatch ──
#     actual_merchant_key, merchant = find_merchant(store, merchant_id)
#     if not merchant:
#         return {"actions": []}

#     category_slug  = merchant.get("category_slug", "business")
#     category       = find_category(store, category_slug)

#     customer = None
#     if customer_id:
#         # try fuzzy lookup for customer too
#         customers = store.get("customer", {})
#         if customer_id in customers:
#             customer = customers[customer_id]["payload"]
#         else:
#             for key in customers:
#                 if customer_id in key or key in customer_id:
#                     customer = customers[key]["payload"]
#                     break

#     # ── COMPOSE ──
#     try:
#         composed = compose_message(category, merchant, trigger, customer)

#     except Exception:
#         print(f"[TICK] COMPOSE FAILED:\n{traceback.format_exc()}")
#         name     = merchant.get("identity", {}).get("name", "there")
#         locality = merchant.get("identity", {}).get("locality", "your area")
#         composed = {
#             "body":      f"{name}, quick update on your {locality} listing. Reply YES for details.",
#             "cta":       "Reply YES",
#             "send_as":   "vera",
#             "rationale": "Fallback — compose failed.",
#         }

#     # suppression_key = (
#     #     trigger.get("suppression_key")
#     #     or trigger_payload.get("suppression_key")
#     #     or f"sup_{category_slug}_{trigger_kind}"
#     # )
#     conversation_id = f"conv_{actual_merchant_key or merchant_id}_{trigger_kind}"

#     action = {
#         "conversation_id": conversation_id,
#         "merchant_id":     merchant_id,
#         "customer_id":     customer_id,
#         "send_as":         composed["send_as"],
#         "trigger_id":      trigger_id,
#         "template_name":   "basic_template",
#         "template_params": [],
#         "body":            composed["body"],
#         "cta":             composed["cta"],
#         # "suppression_key": suppression_key,
#         "rationale":       composed["rationale"],
#     }

#     # if suppression_key:
#     #     mark_suppressed(suppression_key)

#     save_conversation(conversation_id, {
#         "trigger_id":    trigger_id,
#         "trigger_kind":  trigger_kind,
#         "merchant_id":   merchant_id,
#         "customer_id":   customer_id,
#         "category_slug": category_slug,
#         "last_message":  composed["body"],
#         "merchant_name": merchant.get("identity", {}).get("name", ""),
#         "locality":      merchant.get("identity", {}).get("locality", ""),
#         "active_offers": [o for o in merchant.get("offers", []) if o.get("status") == "active"],
#         "lapsed":        merchant.get("customer_aggregate", {}).get("lapsed_180d_plus", 0),
#         "turns":         1,
#     })

#     return {"actions": [action]}


# @app.post("/v1/reply")
# def reply(req: ReplyIn):
#     msg       = req.message.strip()
#     msg_lower = msg.lower()
#     convo     = get_conversation(req.conversation_id) or {}

#     print(f"[REPLY] conv={req.conversation_id} msg={msg[:50]}")

#     if any(p in msg_lower for p in [
#         "thank you for contacting", "office hours", "automated",
#         "will get back", "aapki madad ke liye shukriya",
#         "main ek automated assistant hoon", "out of office",
#     ]):
#         return {"action": "end", "rationale": "Auto-reply detected."}

#     if any(p in msg_lower for p in [
#         "stop", "not interested", "spam", "band karo",
#         "mat bhejo", "nahi chahiye", "no thanks", "unsubscribe",
#     ]):
#         return {
#             "action":    "end",
#             "body":      "Samajh gayi — reply START anytime. 🙂",
#             "cta":       None,
#             "rationale": "Merchant declined.",
#         }

#     convo["merchant_latest_message"] = msg
#     convo["turns"]                   = convo.get("turns", 1) + 1

#     try:
#         result = _call_gemini(build_reply_prompt(convo, msg), max_tokens=512)
#         if result.get("action") == "send" and result.get("body"):
#             convo["last_message"] = result["body"]
#             save_conversation(req.conversation_id, convo)
#         print(f"[REPLY] action={result.get('action')} body={str(result.get('body',''))[:60]}")
#         return result
#     except Exception:
#         print(f"[REPLY] FAILED:\n{traceback.format_exc()}")
#         return {
#             "action":    "send",
#             "body":      "Should I go ahead? Reply YES or STOP.",
#             "cta":       "Reply YES or STOP.",
#             "rationale": "Fallback.",
#         }