# VERA Bot: Deterministic AI Message Composer

VERA Bot is a deterministic merchant engagement engine built for the Magicpin AI Challenge.  
It composes the next best message for merchants using category context, merchant data, trigger signals, and optional customer context.

The goal is not just to generate good text, but to make a strong business decision: what should Vera say next, why now, and what action should the merchant take?

---

## 🚀 Features

- Deterministic `compose()` logic
- Context-aware message generation
- Merchant-specific personalization using offers, metrics, and history
- Category-specific tone for restaurants, dentists, salons, gyms, and pharmacies
- Trigger-based decision making for spikes, dips, recall, festivals, and research signals
- One clear CTA per message
- Suppression key generation to avoid repeated sends
- FastAPI endpoints compatible with the challenge harness

---

## 🧠 Core Idea

The bot follows a simple decision pipeline:

```text
Category + Merchant + Trigger + Customer
        ↓
Select strongest signal
        ↓
Choose campaign intent
        ↓
Apply category-specific rules
        ↓
Generate grounded message
        ↓
Return CTA, send identity, suppression key, and rationale
