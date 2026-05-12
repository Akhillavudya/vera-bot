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

```

🔌 API Endpoints

The bot exposes the required challenge endpoints:

GET  /v1/healthz
GET  /v1/metadata
POST /v1/context
POST /v1/tick
POST /v1/reply

🖥️ Setup Instructions
1. Clone the repository
git clone <your-repo-url>
cd vera-bot
2. Create virtual environment
python -m venv venv

Activate it:

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
3. Install dependencies
pip install -r requirements.txt
4. Run the server
uvicorn app:app --reload

Server runs at:

http://localhost:8000
✅ Health Check
curl http://localhost:8000/v1/healthz

Expected response:

{
  "ok": true
}
🧩 How It Works
The judge sends category, merchant, trigger, and customer context through /v1/context.
The bot stores the latest version of each context item.
On /v1/tick, the bot evaluates active triggers.
It selects the strongest signal for each merchant.
It generates a grounded message with one CTA.
It returns actions in the expected JSON format.
🎯 Design Choices
Used deterministic rules instead of random LLM generation.
Prioritized decision quality before message style.
Avoided fake claims and unsupported numbers.
Kept messages short, specific, and easy to reply to.
Designed suppression keys to reduce repeated campaign suggestions.
⚠️ Constraints Followed
One clear CTA per message
No invented facts
Same input gives same output
Maximum 20 actions per tick
Fast response under timeout
Grounded only in received context
🔮 Future Improvements
Add stronger reply intent handling
Add merchant conversation memory
Improve scoring-based signal ranking
Add more category-specific templates
Add A/B style message variants while keeping determinism
Add dashboard for inspecting generated actions
👨‍💻 Author

Built by Akhil for the Magicpin VERA AI Challenge.


Use this, but change project structure names if your actual files are different.
