# VERA Bot: Deterministic AI Message Composer

VERA Bot is a deterministic merchant engagement engine built for the Magicpin AI Challenge.  
It composes the next best message for merchants using category context, merchant data, trigger signals, and optional customer context.

The goal is not just to generate good text, but to make a strong business decision:
- What should Vera say next?
- Why now?
- What action should the merchant take?

---

# 🚀 Features

- Deterministic `compose()` logic
- Context-aware message generation
- Merchant-specific personalization using offers, metrics, and history
- Category-specific tone for:
  - Restaurants
  - Dentists
  - Salons
  - Gyms
  - Pharmacies
- Trigger-based decision making for:
  - Spikes
  - Dips
  - Recall
  - Festivals
  - Research signals
- One clear CTA per message
- Suppression key generation to avoid repeated sends
- FastAPI endpoints compatible with the challenge harness

---

# 🧠 Core Idea

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

---

# 📁 Project Structure

```text
vera-bot/
├── app.py
├── composer.py
├── decision_engine.py
├── signal_ranker.py
├── templates.py
├── store.py
├── schemas.py
├── utils.py
├── requirements.txt
└── README.md
```

---

# 🔌 API Endpoints

The bot exposes the required challenge endpoints:

```text
GET  /v1/healthz
GET  /v1/metadata
POST /v1/context
POST /v1/tick
POST /v1/reply
```

---

# 📊 Example Output

```json
{
  "message": "Lunch demand is high around your outlet right now. Should I push your ₹199 combo to nearby customers before 2 PM?",
  "cta": "Reply YES to send",
  "send_as": "Vera",
  "suppression_key": "m_001:restaurant:lunch_spike:2026-05-01",
  "rationale": "Lunch demand is the strongest trigger. The message uses the merchant's live ₹199 combo offer and gives one clear action."
}
```

---

# 🖥️ Setup Instructions

## 1. Clone the repository

```bash
git clone <your-repo-url>
cd vera-bot
```

---

## 2. Create virtual environment

```bash
python -m venv venv
```

Activate it:

### Windows

```bash
venv\Scripts\activate
```

### Linux / Mac

```bash
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Run the server

```bash
uvicorn app:app --reload
```

Server runs at:

```text
http://localhost:8000
```

---

# ✅ Health Check

```bash
curl http://localhost:8000/v1/healthz
```

Expected response:

```json
{
  "ok": true
}
```

---

# 🧩 How It Works

1. The judge sends category, merchant, trigger, and customer context through `/v1/context`.
2. The bot stores the latest version of each context item.
3. On `/v1/tick`, the bot evaluates active triggers.
4. It selects the strongest signal for each merchant.
5. It generates a grounded message with one CTA.
6. It returns actions in the expected JSON format.

---

# 🎯 Design Choices

- Used deterministic rules instead of random LLM generation
- Prioritized decision quality before message style
- Avoided fake claims and unsupported numbers
- Kept messages short, specific, and easy to reply to
- Designed suppression keys to reduce repeated campaign suggestions

---

# ⚠️ Constraints Followed

- One clear CTA per message
- No invented facts
- Same input gives same output
- Maximum 20 actions per tick
- Fast response under timeout
- Grounded only in received context

---

# 🔮 Future Improvements

- Add stronger reply intent handling
- Add merchant conversation memory
- Improve scoring-based signal ranking
- Add more category-specific templates
- Add A/B style message variants while keeping determinism
- Add dashboard for inspecting generated actions

---

# 👨‍💻 Author

Built by **Akhil** for the Magicpin VERA AI Challenge.
