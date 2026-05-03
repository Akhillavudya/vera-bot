"""
rag_store.py — Gold-standard example store for Vera Bot RAG system.

Coverage: 5 categories × 8 trigger kinds = 40 examples
No vector DB. No embeddings. Pure Python dict.
Fast, zero-dependency, deterministic.

Retrieval priority:
  1. Exact match    → category__trigger_kind
  2. Category match → category__* sorted by score desc
  3. Global match   → all examples sorted by score desc
"""

# ─────────────────────────────────────────────────────────────────────────────
# COMPULSION LEVER MAP
# Which levers to emphasise per trigger kind.
# Injected into compose prompt as explicit instructions.
# ─────────────────────────────────────────────────────────────────────────────

LEVER_MAP = {
    "research_digest": [
        "source_citation",         # "JIDA Oct 2026 p.14" — credibility anchor
        "specificity",             # trial n, percentage, page number
        "reciprocity",             # "I'll pull it + draft a version for you"
        "curiosity",               # "want to see the 2-min abstract?"
    ],
    "research_digest_release": [
        "source_citation",
        "specificity",
        "reciprocity",
        "curiosity",
    ],
    "recall_due": [
        "specificity",             # real date, real price, real slot times
        "relationship_continuity", # reference prior visits, services received
        "effort_externalization",  # "2 slots ready — just pick one"
        "single_binary_cta",       # Reply 1 / 2 / YES
    ],
    "perf_dip": [
        "loss_aversion",           # "you're missing X searches / X calls"
        "specificity",             # exact CTR, exact peer benchmark
        "effort_externalization",  # "I've prepared the creative — just say go"
        "urgency",                 # "before this weekend's traffic"
    ],
    "seasonal_perf_dip": [
        "anxiety_preemption",      # "this drop is normal — here's why"
        "specificity",
        "reframe",                 # loss → opportunity
        "effort_externalization",
    ],
    "perf_spike": [
        "social_proof",            # "you're now top 15% in your locality"
        "momentum_framing",        # "let's lock in this lead"
        "reciprocity",             # "I noticed this — thought you'd want to know"
        "single_binary_cta",
    ],
    "festival_upcoming": [
        "urgency",                 # "4 days to Diwali — last window"
        "specificity",             # festival name, days remaining, offer price
        "effort_externalization",  # "I'll draft the WhatsApp + IG story"
        "loss_aversion",           # "competitors in your block already live"
    ],
    "curious_ask": [
        "asking_merchant",         # "what's been most requested this week?"
        "reciprocity",             # "I'll turn it into a Google post"
        "effort_externalization",  # "5 min, I handle the rest"
        "low_commitment",          # no money, no decision required
    ],
    "scheduled_recurring": [
        "asking_merchant",
        "reciprocity",
        "low_commitment",
        "curiosity",
    ],
    "customer_lapsed_soft": [
        "no_shame_framing",        # "happens to most members/patients"
        "specificity",             # days since last visit, real slot, real price
        "preference_honored",      # evening/weekend slot matching history
        "zero_barrier_cta",        # "no commitment, no auto-charge"
    ],
    "customer_lapsed_hard": [
        "no_shame_framing",
        "new_offering",            # something new since they last came
        "specificity",
        "zero_barrier_cta",
    ],
    "supply_alert": [
        "urgency",
        "specificity",             # batch numbers, molecule names, affected count
        "effort_externalization",  # "I'll draft customer WhatsApp + workflow"
        "trust_precision",         # clinical/pharmacy voice, no overclaim
    ],
    "regulation_change": [
        "urgency",
        "specificity",             # regulation name, effective date, required action
        "social_proof",            # "most clinics haven't updated yet"
        "effort_externalization",
    ],
    "milestone_reached": [
        "social_proof",
        "momentum_framing",
        "curiosity",
        "reciprocity",
    ],
    "dormant_with_vera": [
        "curiosity",
        "asking_merchant",
        "low_commitment",
        "reciprocity",
    ],
    "competitor_opened": [
        "loss_aversion",
        "specificity",             # distance, rating, review count
        "urgency",
        "effort_externalization",
    ],
    "review_theme_emerged": [
        "specificity",             # exact theme, count of mentions
        "asking_merchant",
        "reciprocity",
        "low_commitment",
    ],
    "active_planning_intent": [
        "complete_artifact",       # deliver full draft immediately
        "specificity",
        "effort_externalization",
        "single_binary_cta",
    ],
    "_default": [
        "specificity",
        "reciprocity",
        "effort_externalization",
        "single_binary_cta",
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# ANTI-PATTERNS
# Injected as "DO NOT do this" in the compose prompt.
# ─────────────────────────────────────────────────────────────────────────────

ANTI_PATTERNS = [
    {
        "bad_body": "Hi Doctor, want to run a discount campaign today to increase sales?",
        "why_bad": "No trigger, no merchant fact, no category voice, generic offer framing.",
    },
    {
        "bad_body": "Chef SK Pizza Junction, I'm analyzing your Sant Nagar branch data. Your performance shows room for growth with a new exclusive offer.",
        "why_bad": "Opens with 'I'm analyzing' meta-commentary. No real numbers. Generic offer. Zero trigger relevance.",
    },
    {
        "bad_body": "Your retention is trailing peers by ~12%. Reply YES to activate campaign.",
        "why_bad": "Fabricated percentage not in context. Judge penalises invented numbers as fabrication — 0/10 specificity.",
    },
    {
        "bad_body": "AMAZING DEAL! Get 30% off all dental treatments today only!!!",
        "why_bad": "Promotional tone for clinical category. Percentage offer instead of service+price. Multiple exclamation marks.",
    },
    {
        "bad_body": "I hope you're doing well. I'm reaching out today to let you know about some opportunities that might be helpful for your business.",
        "why_bad": "Long preamble. Zero information. No trigger. No merchant fact. No CTA.",
    },
    {
        "bad_body": "I've identified a growth opportunity for your business in your area.",
        "why_bad": "Vague, fabricated framing. No numbers, no specifics, no trigger relevance.",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# GOLD EXAMPLE STORE
# Key:   "category__trigger_kind"
# Value: body, cta, send_as, score (out of 50), levers, voice_notes
#
# voice_notes explains WHY it scores high — the LLM reads this too.
# score is from the judge rubric (5 dimensions × 10 each).
# ─────────────────────────────────────────────────────────────────────────────

EXAMPLE_STORE = {

    # ═══════════════════════════════════════════════════════════════
    # DENTISTS
    # Voice: clinical/peer, source citations, no promotional tone,
    #        technical vocabulary welcome, no "cure/guaranteed"
    # ═══════════════════════════════════════════════════════════════

    "dentists__research_digest": {
        "body": (
            "Dr. Meera, JIDA's Oct issue landed. One item relevant to your high-risk adult "
            "patients — 2,100-patient trial showed 3-month fluoride recall cuts caries "
            "recurrence 38% better than 6-month. Worth a look (2-min abstract). Want me to "
            "pull it + draft a patient-ed WhatsApp you can share?  — JIDA Oct 2026 p.14"
        ),
        "cta": "Want me to pull it + draft the patient message?",
        "send_as": "vera",
        "score": 50,
        "levers": ["source_citation", "specificity", "reciprocity", "curiosity"],
        "voice_notes": (
            "Clinical peer tone. n=2,100 and 38% are real numbers from the digest payload. "
            "'Your high-risk adult patients' is derived from customer_aggregate — not invented. "
            "Page citation (p.14) adds academic credibility. CTA is last sentence, low-friction."
        ),
    },

    "dentists__recall_due": {
        "body": (
            "Hi Priya, Dr. Meera's clinic here 🦷 It's been 5 months since your last visit "
            "— your 6-month cleaning recall is due. Apke liye 2 slots ready hain: Wed 5 "
            "Nov, 6pm ya Thu 6 Nov, 5pm. ₹299 cleaning + complimentary fluoride. "
            "Reply 1 for Wed, 2 for Thu, or tell us a time that works."
        ),
        "cta": "Reply 1 for Wed, 2 for Thu.",
        "send_as": "merchant_on_behalf",
        "score": 49,
        "levers": ["specificity", "language_mix", "preference_honored", "relationship_continuity"],
        "voice_notes": (
            "Hi-en mix matches patient language_pref. Real slot dates and times from available slots. "
            "Real catalog price ₹299. Evening slots match patient's booking history. "
            "Dental emoji adds warmth without being promotional. "
            "Multi-choice CTA allowed for booking flows."
        ),
    },

    "dentists__perf_dip": {
        "body": (
            "Dr. Meera, quick flag — your CTR dropped to 2.1% this week, against a "
            "Lajpat Nagar peer median of 3.0%. That gap means roughly 43 local searches "
            "found a competitor instead of you this week. "
            "Your last GBP post was 22 days ago — Google deprioritises stale listings. "
            "Shall I draft a post now? Takes 4 minutes on your end."
        ),
        "cta": "Shall I draft the post? Takes 4 minutes.",
        "send_as": "vera",
        "score": 49,
        "levers": ["loss_aversion", "specificity", "cause_explanation", "effort_externalization"],
        "voice_notes": (
            "CTR 2.1% from performance snapshot. Peer median 3.0% from category peer_stats. "
            "43 missed searches is a derived number (views × gap) — grounded in real data. "
            "22-day stale post from merchant signals list. "
            "Cause identified + fix offered. 4-minute commitment cap."
        ),
    },

    "dentists__perf_spike": {
        "body": (
            "Dr. Meera, your profile had 847 views this week — up 34% vs your 30-day average. "
            "That puts you in the top 18% of Lajpat Nagar dental listings right now. "
            "Your 'Dental Cleaning @ ₹299' offer is active but your profile has no booking link. "
            "Want me to add a WhatsApp booking button before this traffic drops off?"
        ),
        "cta": "Want me to add the booking button?",
        "send_as": "vera",
        "score": 48,
        "levers": ["social_proof", "specificity", "momentum_framing", "effort_externalization"],
        "voice_notes": (
            "847 views and 34% delta from performance snapshot. "
            "Top 18% derived from peer_stats distribution. "
            "Active offer referenced from offer catalog — not invented. "
            "Booking link gap from merchant signals."
        ),
    },

    "dentists__festival_upcoming": {
        "body": (
            "Dr. Meera, Dhanteras in 3 days — wedding season whitening requests peak in this "
            "window (Oct-Dec is your highest whitening month per seasonal data). "
            "Your 'Teeth Whitening @ ₹1,499' is currently paused. "
            "Reactivating it today means you catch the next 72 hours of search traffic. "
            "Shall I reactivate + draft a 'Wedding-ready smile' WhatsApp for your patient list?"
        ),
        "cta": "Shall I reactivate the offer + draft the WhatsApp?",
        "send_as": "vera",
        "score": 48,
        "levers": ["urgency", "seasonal_beat", "specificity", "effort_externalization"],
        "voice_notes": (
            "Dhanteras timing from trigger payload. Wedding whitening peak from category seasonal_beats. "
            "Paused offer from merchant offers list — not fabricated. "
            "72-hour window is real (3 days × 24h)."
        ),
    },

    "dentists__curious_ask": {
        "body": (
            "Dr. Meera, quick question — what treatment has your front desk been fielding "
            "the most enquiries about this week? "
            "I'll use the answer to draft a 3-line patient FAQ you can pin to your WhatsApp "
            "and a GBP Q&A update. Two outputs, 5 minutes of your time."
        ),
        "cta": "What's your most-asked treatment this week?",
        "send_as": "vera",
        "score": 46,
        "levers": ["asking_merchant", "reciprocity", "effort_externalization", "low_commitment"],
        "voice_notes": (
            "Asking-the-merchant lever is underused in production Vera — drives high engagement. "
            "Two concrete deliverables specified upfront (FAQ + GBP Q&A). "
            "5-minute cap. No money, no decision required."
        ),
    },

    "dentists__customer_lapsed_soft": {
        "body": (
            "Hi Priya, Dr. Meera's clinic here 🦷 It's been 5 months — your 6-month "
            "cleaning window is just opening. We have Wed 6pm and Thu 5pm slots this week. "
            "₹299 cleaning + fluoride application. "
            "Reply 1 for Wed or 2 for Thu — no deposit needed, free to reschedule."
        ),
        "cta": "Reply 1 for Wed, 2 for Thu.",
        "send_as": "merchant_on_behalf",
        "score": 48,
        "levers": ["specificity", "preference_honored", "zero_barrier_cta", "language_mix"],
        "voice_notes": (
            "Soft lapse — no shame framing, purely practical. "
            "Real slots matching patient's evening preference. "
            "Free reschedule removes the main commitment barrier. "
            "Price + benefit in one line."
        ),
    },

    "dentists__customer_lapsed_hard": {
        "body": (
            "Hi Priya, Dr. Meera's clinic here. It's been over 8 months — no worries, "
            "happens to all of us. We've added online booking since your last visit — "
            "no waiting at reception. Your cleaning is overdue. "
            "Wed 6pm slot is open this week. ₹299 + free X-ray review. "
            "Reply YES to confirm — I'll send the booking link."
        ),
        "cta": "Reply YES to confirm.",
        "send_as": "merchant_on_behalf",
        "score": 47,
        "levers": ["no_shame_framing", "new_offering", "specificity", "zero_barrier_cta"],
        "voice_notes": (
            "Hard lapse — no guilt, acknowledge time gap neutrally. "
            "New feature (online booking) gives genuine reason to return. "
            "Free X-ray review from offer catalog. Single slot removes decision paralysis."
        ),
    },

    "dentists__dormant_with_vera": {
        "body": (
            "Dr. Meera, just checking in — haven't heard back in 2 weeks. "
            "One thing I noticed: 190 people searched 'Dental Check Up Lajpat Nagar' "
            "this week and your listing appeared but your response rate shows as low. "
            "Want me to set up auto-responses for the top 3 questions patients ask? "
            "No changes to your profile, just faster replies."
        ),
        "cta": "Want me to set up the auto-responses?",
        "send_as": "vera",
        "score": 46,
        "levers": ["loss_aversion", "specificity", "low_commitment", "curiosity"],
        "voice_notes": (
            "Dormant — don't guilt-trip, offer specific value. "
            "190 searches from category trend signals or digest — must be real. "
            "'No changes to profile' removes fear of unilateral changes. "
            "3 auto-responses is a concrete, bounded deliverable."
        ),
    },


    # ═══════════════════════════════════════════════════════════════
    # SALONS
    # Voice: warm/practical, fellow-operator tone,
    #        emojis acceptable, service+price format
    # ═══════════════════════════════════════════════════════════════

    "salons__research_digest": {
        "body": (
            "Lakshmi, Indian Beauty & Hygiene Association quarterly brief just dropped — "
            "one finding for Studio11: salons offering a 'keratin + blowout' combo at a "
            "fixed price are seeing 31% higher repeat bookings vs à la carte pricing. "
            "You currently list them separately. "
            "Want me to draft a combo offer + a WhatsApp announcement to your active customers?"
        ),
        "cta": "Want me to draft the combo offer?",
        "send_as": "vera",
        "score": 47,
        "levers": ["source_citation", "specificity", "merchant_fit", "effort_externalization"],
        "voice_notes": (
            "Source from category digest. 31% specific and verifiable. "
            "Directly references merchant's current offer structure (listed separately) — merchant fit. "
            "Clear improvement path + complete deliverable."
        ),
    },

    "salons__recall_due": {
        "body": (
            "Hi Kavya 💍 Lakshmi from Studio11 Kapra here. 196 days to your wedding — "
            "perfect window to start the 30-day skin-prep program before serious bridal "
            "bookings roll in. ₹2,499 covers 4 sessions + a take-home kit. "
            "Want me to block your preferred Saturday 4pm slot for the first session next week?"
        ),
        "cta": "Want me to block Saturday 4pm?",
        "send_as": "merchant_on_behalf",
        "score": 47,
        "levers": ["specificity", "relationship_continuity", "urgency", "preference_honored"],
        "voice_notes": (
            "196-day countdown from wedding date in customer profile — real, verifiable. "
            "Program structure + price from merchant offer catalog. "
            "Saturday 4pm from customer booking history preference. "
            "Owner first name Lakshmi for warmth."
        ),
    },

    "salons__perf_dip": {
        "body": (
            "Lakshmi, calls from your Studio11 Kapra listing dropped 18% this week "
            "vs the previous 7 days. Your photos were last updated 45 days ago — "
            "salons with fresh photos every 3 weeks see 22% more profile actions. "
            "I can draft 5 caption ideas for photos you already have on your phone. "
            "Just send 3 recent ones and I'll handle the rest."
        ),
        "cta": "Send 3 recent photos and I'll draft the captions.",
        "send_as": "vera",
        "score": 47,
        "levers": ["specificity", "cause_explanation", "social_proof", "effort_externalization"],
        "voice_notes": (
            "Call drop 18% from performance 7d delta. "
            "Photo staleness 45 days from signals list. "
            "22% stat from category peer_stats — must be from context. "
            "Phone photos = zero cost, zero equipment barrier."
        ),
    },

    "salons__perf_spike": {
        "body": (
            "Lakshmi, Studio11 had 1,240 profile views this week — up 28% vs your monthly average. "
            "Your 4.9★ rating with 298 reviews is already pulling traffic. "
            "One gap: your business description is still missing, which means Google shows "
            "a blank under your name in search results. "
            "Shall I draft a 60-word description? I'll send it for your approval first."
        ),
        "cta": "Shall I draft the description for approval?",
        "send_as": "vera",
        "score": 48,
        "levers": ["social_proof", "specificity", "loss_aversion", "effort_externalization"],
        "voice_notes": (
            "1,240 views and 28% delta from performance snapshot. "
            "4.9★ and 298 reviews from performance data. "
            "Missing description from merchant signals list — not fabricated. "
            "Approval step removes fear of unilateral changes."
        ),
    },

    "salons__festival_upcoming": {
        "body": (
            "Lakshmi, Karwa Chauth in 4 days — last year your salon had a 3-day "
            "pre-festival spike in mehendi and blowout bookings. "
            "Your Saturday slots are still open. "
            "Want me to send a 'Karwa Chauth ready' WhatsApp to your 198 active customers? "
            "I'll draft it — you approve before it goes."
        ),
        "cta": "Want me to draft it for approval?",
        "send_as": "vera",
        "score": 48,
        "levers": ["urgency", "historical_data", "specificity", "effort_externalization"],
        "voice_notes": (
            "Festival from trigger. Historical booking pattern from seasonal_beats or conversation_history. "
            "198 active customers from customer_aggregate. "
            "Approval step before sending builds trust with merchant."
        ),
    },

    "salons__curious_ask": {
        "body": (
            "Hi Lakshmi! Quick check — what service has been most asked-for this week "
            "at Studio11? I'll turn the answer into a Google post + a 4-line WhatsApp "
            "reply you can use when customers ask about pricing. Takes 5 min."
        ),
        "cta": "What's been most asked this week?",
        "send_as": "vera",
        "score": 44,
        "levers": ["asking_merchant", "reciprocity", "effort_externalization", "low_commitment"],
        "voice_notes": (
            "Asking-the-merchant lever — high engagement. Two concrete deliverables. "
            "Uses owner first name Lakshmi. Warm-practical tone, not promotional. "
            "5-minute cap. No money, no approval required."
        ),
    },

    "salons__customer_lapsed_soft": {
        "body": (
            "Hi Meena 💇 Studio11 Kapra here. It's been 3 months since your last keratin "
            "treatment — your usual 10-week refresh window is open. "
            "We have Thursday 5pm and Saturday 11am this week. "
            "₹1,800 keratin + free head massage. Reply 1 for Thu or 2 for Sat."
        ),
        "cta": "Reply 1 for Thu, 2 for Sat.",
        "send_as": "merchant_on_behalf",
        "score": 48,
        "levers": ["specificity", "service_history", "preference_honored", "zero_barrier_cta"],
        "voice_notes": (
            "References specific service from customer visit history. "
            "10-week refresh is category knowledge — grounded. "
            "Real slots, real price, free add-on from offer catalog. "
            "Reply 1/2 is lowest-friction booking CTA."
        ),
    },

    "salons__customer_lapsed_hard": {
        "body": (
            "Hi Meena 💇 Studio11 Kapra here. It's been 6 months — we miss you! "
            "We've added a new 'Express Blow-dry @ ₹399' (30 min) since your last visit. "
            "Saturday 11am slot is open. No prior booking needed — just walk in "
            "or reply YES and I'll mark you down. No deposit."
        ),
        "cta": "Reply YES and I'll mark you down.",
        "send_as": "merchant_on_behalf",
        "score": 47,
        "levers": ["no_shame_framing", "new_offering", "specificity", "zero_barrier_cta"],
        "voice_notes": (
            "6 months from customer relationship data. "
            "New service gives genuine reason to return. "
            "No deposit + no prior booking = two barriers removed."
        ),
    },


    # ═══════════════════════════════════════════════════════════════
    # RESTAURANTS
    # Voice: operator-to-operator, uses "covers", "AOV", "delivery",
    #        Hindi-English mix fine, practical not promotional
    # ═══════════════════════════════════════════════════════════════

    "restaurants__research_digest": {
        "body": (
            "Rajan, NRAI monthly brief flagged something relevant: "
            "restaurants adding a 'meal for 2 under ₹500' tag to their Google listing "
            "are seeing 27% more direction requests from price-conscious searchers — "
            "a segment that's grown 40% in Delhi NCR this quarter. "
            "Your current tag is empty. Want me to add it now? "
            "I'll draft 3 options for you to pick from."
        ),
        "cta": "Want me to draft 3 tag options?",
        "send_as": "vera",
        "score": 47,
        "levers": ["source_citation", "specificity", "merchant_fit", "effort_externalization"],
        "voice_notes": (
            "Source: NRAI brief from category digest. Two percentages — verifiable. "
            "Delhi NCR localisation. Missing tag from merchant signals. "
            "3 options gives merchant control without open-ended effort."
        ),
    },

    "restaurants__recall_due": {
        "body": (
            "Hi Ananya 👋 Pizza Junction Sant Nagar here. Haven't seen you in 6 weeks — "
            "we've added a new Paneer Tikka Pizza since your last visit. "
            "Tuesday BOGO is still on (buy 1 get 1 free, dine-in or takeaway). "
            "Want me to reserve a table for Tuesday evening? Just tell me the time."
        ),
        "cta": "What time works Tuesday?",
        "send_as": "merchant_on_behalf",
        "score": 47,
        "levers": ["new_offering", "specificity", "existing_offer", "zero_barrier_cta"],
        "voice_notes": (
            "No shame framing. New menu item creates genuine reason to return. "
            "Active BOGO from offer catalog — not fabricated. "
            "Open-ended time CTA for booking context is appropriate. "
            "6-week gap from customer relationship data."
        ),
    },

    "restaurants__perf_dip": {
        "body": (
            "Rajan, your listing calls dropped from 31 to 24 this week. "
            "Your menu photos were last updated 60 days ago and you have no "
            "Google post in the last 3 weeks. "
            "Restaurants with a weekly post see 19% more calls on average in Sant Nagar. "
            "Shall I draft this week's post using your current lunch thali? "
            "You just confirm the price."
        ),
        "cta": "Shall I draft the post? Just confirm the thali price.",
        "send_as": "vera",
        "score": 47,
        "levers": ["specificity", "cause_explanation", "social_proof", "effort_externalization"],
        "voice_notes": (
            "Absolute numbers 31→24 from performance delta — more compelling than percentage alone. "
            "60-day photo staleness and 3-week post gap from signals list. "
            "19% stat from category peer_stats. Ultra-low friction: just confirm price."
        ),
    },

    "restaurants__perf_spike": {
        "body": (
            "Rajan, Pizza Junction had 2,100 views this week — highest in 30 days. "
            "Your BOGO Tuesday-Thursday offer is driving it. "
            "One gap: your Google listing has no 'Order Now' button. "
            "I can add your Swiggy link in 3 minutes. Want me to do that now?"
        ),
        "cta": "Want me to add the Order Now button?",
        "send_as": "vera",
        "score": 47,
        "levers": ["social_proof", "specificity", "momentum_framing", "effort_externalization"],
        "voice_notes": (
            "2,100 views from performance snapshot. Attributes cause correctly to active offer. "
            "Missing Order Now button from signals list. "
            "3-minute commitment. Single action, immediate value."
        ),
    },

    "restaurants__festival_upcoming": {
        "body": (
            "Quick heads-up Rajan — DC vs MI at Arun Jaitley tonight, 7:30pm. "
            "Important: Saturday IPL matches shift -12% restaurant covers "
            "(people watch at home). Skip the match-night promo today; "
            "instead push your BOGO pizza (already active) as a delivery-only Saturday special. "
            "Want me to draft the Swiggy banner + an Insta story? Live in 10 min."
        ),
        "cta": "Want me to draft it? Live in 10 min.",
        "send_as": "vera",
        "score": 50,
        "levers": ["contrarian_insight", "loss_aversion", "specificity", "effort_externalization"],
        "voice_notes": (
            "Trigger said IPL match — bot added judgment: Saturday = delivery, not dine-in. "
            "-12% from category data. Active BOGO referenced from offer catalog. "
            "10-minute cap. Contrarian recommendation is the highest signal of category understanding."
        ),
    },

    "restaurants__curious_ask": {
        "body": (
            "Rajan, quick one — what's your best-seller this week that you wish "
            "more people knew about? "
            "I'll build it into a 'hidden gem' Google post and a 2-line Instagram caption. "
            "Both ready in 10 minutes once you tell me."
        ),
        "cta": "What's your best-seller this week?",
        "send_as": "vera",
        "score": 45,
        "levers": ["asking_merchant", "reciprocity", "effort_externalization", "curiosity"],
        "voice_notes": (
            "Asking-the-merchant lever with two concrete deliverables. "
            "'Hidden gem' framing is compelling without being hype. "
            "10-minute cap. Uses owner name."
        ),
    },

    "restaurants__customer_lapsed_soft": {
        "body": (
            "Hi Ananya 👋 Pizza Junction Sant Nagar here. Aapko 6 hafte ho gaye — "
            "we've added Butter Chicken Pizza to the menu since your last order. "
            "Tuesday BOGO is still on. Want me to reserve a table this Tuesday evening? "
            "Just say the time."
        ),
        "cta": "What time works Tuesday?",
        "send_as": "merchant_on_behalf",
        "score": 46,
        "levers": ["language_mix", "new_offering", "existing_offer", "zero_barrier_cta"],
        "voice_notes": (
            "Hindi-English mix. 6-week gap from customer data. "
            "New menu item gives genuine reason to return. "
            "Active BOGO from offer catalog."
        ),
    },

    "restaurants__active_planning_intent": {
        "body": (
            "Suresh, here's a starter version — you can edit:\n\n"
            "Mylari Corporate Thali — for offices in Indiranagar\n"
            "· 10 thalis @ ₹125 each (₹25 off retail) + free delivery\n"
            "· 25 thalis @ ₹115 each + 2 free filter coffees\n"
            "· 50+: ₹105 each + 1 free dosa platter\n"
            "· WhatsApp day-before by 5pm; delivery 12:30–1pm\n\n"
            "3 offices in your delivery radius — Embassy Tech, RMZ Eco, Sigma Soft. "
            "Want me to draft a 3-line WhatsApp to their facilities managers?"
        ),
        "cta": "Want me to draft the facilities manager message?",
        "send_as": "vera",
        "score": 49,
        "levers": ["complete_artifact", "specificity", "effort_externalization", "social_proof"],
        "voice_notes": (
            "Merchant said yes to corporate thali idea — bot delivered the complete artifact immediately. "
            "No further qualifying questions. Tiered pricing is B2B-appropriate. "
            "Named offices in delivery radius from locality data. "
            "Follow-on: outreach to facilities managers is the natural next step."
        ),
    },


    # ═══════════════════════════════════════════════════════════════
    # GYMS
    # Voice: coach-to-operator, uses "conversion", "retention",
    #        "ad spend", "members", motivational but data-grounded
    # ═══════════════════════════════════════════════════════════════

    "gyms__research_digest": {
        "body": (
            "Karthik, Sports Medicine India journal this month: gyms offering "
            "a free 'fitness age assessment' at sign-up see 34% higher 3-month "
            "retention vs standard onboarding. Your current onboarding has no assessment step. "
            "I can draft a 10-question WhatsApp flow you run with new members — "
            "8 minutes per member. Want the draft?"
        ),
        "cta": "Want me to draft the assessment flow?",
        "send_as": "vera",
        "score": 47,
        "levers": ["source_citation", "specificity", "merchant_fit", "effort_externalization"],
        "voice_notes": (
            "Journal source from category digest. 34% retention lift. "
            "Gap identified from merchant onboarding signals. "
            "8-minute per-member effort is realistic and stated upfront."
        ),
    },

    "gyms__recall_due": {
        "body": (
            "Hi Rashmi 👋 Karthik from PowerHouse here. It's been about 8 weeks — "
            "happens to most members at some point, no judgment. "
            "We've added a Tue/Thu evening HIIT class that fits weight-loss goals well "
            "(45 min, 6:30pm). Want me to hold a free trial spot for you next Tue, 30 Apr? "
            "Reply YES — no commitment, no auto-charge."
        ),
        "cta": "Reply YES — no commitment, no auto-charge.",
        "send_as": "merchant_on_behalf",
        "score": 50,
        "levers": ["no_shame_framing", "new_offering", "specificity", "zero_barrier_cta"],
        "voice_notes": (
            "'No judgment' removes guilt. 'Happens to most members' = social proof framing. "
            "HIIT class tied to her stated goal (weight loss from customer profile). "
            "Specific day, time, duration. "
            "'No commitment, no auto-charge' removes two barriers in one line."
        ),
    },

    "gyms__perf_dip": {
        "body": (
            "Karthik, your PowerHouse profile calls dropped from 18 to 11 this week. "
            "Your nearest competitor 1.2km away added 14 new photos last month — "
            "their listing now ranks above yours for 'gym near me HSR Layout'. "
            "Your last photo upload was 47 days ago. "
            "Shall I draft 5 caption ideas for photos you can shoot today on your phone?"
        ),
        "cta": "Shall I draft the caption ideas?",
        "send_as": "vera",
        "score": 47,
        "levers": ["specificity", "loss_aversion", "competitor_context", "effort_externalization"],
        "voice_notes": (
            "Absolute call numbers 18→11 from performance delta. "
            "Competitor data from trigger payload. "
            "47-day photo staleness from signals list. "
            "Phone photos = zero cost, zero equipment barrier."
        ),
    },

    "gyms__perf_spike": {
        "body": (
            "Karthik, PowerHouse had 890 profile views this week — up 41% vs your 30-day average. "
            "You're in the top 12% of HSR Layout gyms right now. "
            "Your 'First month @ ₹499' offer is active — good conversion window. "
            "One gap: no customer reviews in the last 30 days. "
            "Want me to draft a 'how was your first week?' message to your 12 newest members? "
            "Reviews now lock in this ranking."
        ),
        "cta": "Want me to draft the review request?",
        "send_as": "vera",
        "score": 48,
        "levers": ["social_proof", "specificity", "momentum_framing", "effort_externalization"],
        "voice_notes": (
            "890 views and 41% delta from performance snapshot. "
            "Top 12% from category peer_stats distribution. "
            "Active offer from merchant catalog. "
            "Review gap from signals. 12 newest members from customer_aggregate."
        ),
    },

    "gyms__festival_upcoming": {
        "body": (
            "Karthik, New Year in 8 days — gym sign-ups spike 180% in the first "
            "2 weeks of January (your biggest acquisition window of the year). "
            "Your 'First month @ ₹499' offer is perfect for this. "
            "Last year you didn't run a pre-New Year campaign. "
            "Want me to draft a WhatsApp blast to your 89 lapsed members + "
            "a Google post targeting 'gym near me HSR Layout'?"
        ),
        "cta": "Want me to draft both?",
        "send_as": "vera",
        "score": 48,
        "levers": ["urgency", "specificity", "historical_comparison", "effort_externalization"],
        "voice_notes": (
            "180% spike from category seasonal_beats. 8 days creates urgency. "
            "Real offer from catalog. 89 lapsed from customer_aggregate. "
            "Two deliverables: WhatsApp + Google post."
        ),
    },

    "gyms__curious_ask": {
        "body": (
            "Karthik, quick one — what class or equipment are your members asking "
            "about most this month that you don't currently offer? "
            "I'll use the answer to draft a waitlist post for your Google profile "
            "and a member survey WhatsApp. Both ready in 15 minutes."
        ),
        "cta": "What are members asking for that you don't have yet?",
        "send_as": "vera",
        "score": 45,
        "levers": ["asking_merchant", "reciprocity", "effort_externalization", "curiosity"],
        "voice_notes": (
            "Asking-the-merchant lever. Waitlist post = smart demand signal. "
            "Two deliverables. 15-minute cap. Uses owner name."
        ),
    },

    "gyms__customer_lapsed_soft": {
        "body": (
            "Hi Rashmi 👋 Karthik from PowerHouse here. It's been 5 weeks — "
            "no worries, happens to all of us. Your membership is still active. "
            "We've extended morning batch timing to 6am (you mentioned early mornings work best). "
            "Want me to mark you in for this Saturday 6am? Reply YES — no charge, your plan covers it."
        ),
        "cta": "Reply YES for Saturday 6am.",
        "send_as": "merchant_on_behalf",
        "score": 47,
        "levers": ["no_shame_framing", "preference_honored", "specificity", "zero_barrier_cta"],
        "voice_notes": (
            "5-week gap from customer data. No shame. "
            "Early morning timing from customer preference. "
            "Active membership = no extra cost = zero barrier. "
            "Single YES CTA."
        ),
    },

    "gyms__seasonal_perf_dip": {
        "body": (
            "Karthik, your views are down 30% this week — but this is the normal "
            "April-June acquisition lull (every metro gym sees -25 to -35% in this window). "
            "Action: skip ad spend now, save it for Sept-Oct when conversion is 2x. "
            "Focus retention on your 245 active members instead. "
            "Want me to draft a 'summer attendance challenge' to keep them through the dip?"
        ),
        "cta": "Want me to draft the summer challenge?",
        "send_as": "vera",
        "score": 48,
        "levers": ["anxiety_preemption", "specificity", "reframe", "effort_externalization"],
        "voice_notes": (
            "Seasonal dip is normal — reframe prevents panic spend. "
            "Range -25 to -35% from category seasonal data. "
            "245 members from merchant data. Sept-Oct 2x conversion from category benchmarks."
        ),
    },


    # ═══════════════════════════════════════════════════════════════
    # PHARMACIES
    # Voice: trustworthy/precise, clinical, respectful,
    #        molecule names, no overclaims, namaste for seniors
    # ═══════════════════════════════════════════════════════════════

    "pharmacies__research_digest": {
        "body": (
            "Ramesh, IPA quarterly brief this month: pharmacies adding a "
            "'free home delivery for chronic prescriptions' tag to their Google profile "
            "are seeing 38% higher repeat customer retention. "
            "You offer free delivery above ₹499 but your Google listing doesn't mention it. "
            "That's a ranking advantage you're not using. "
            "Want me to add it now? Takes 2 minutes."
        ),
        "cta": "Want me to add the delivery tag? Takes 2 minutes.",
        "send_as": "vera",
        "score": 47,
        "levers": ["source_citation", "specificity", "merchant_fit", "effort_externalization"],
        "voice_notes": (
            "IPA source from category digest. 38% retention stat. "
            "Merchant already has free delivery from offers but doesn't advertise it — "
            "real gap, not fabricated. 2-minute commitment is minimal."
        ),
    },

    "pharmacies__recall_due": {
        "body": (
            "Namaste — Apollo Health Plus Malviya Nagar yahan. "
            "Sharma ji ki 3 monthly medicines (metformin, atorvastatin, telmisartan) "
            "28 April ko khatam hongi. Same dose, same brand pack ready hai. "
            "Senior discount 15% applied — total ₹1,420 (₹240 saved). "
            "Free home delivery to saved address by 5pm tomorrow. "
            "Reply CONFIRM to dispatch, or call 9876543210 if any change in dosage."
        ),
        "cta": "Reply CONFIRM to dispatch.",
        "send_as": "merchant_on_behalf",
        "score": 49,
        "levers": ["specificity", "savings_shown", "two_channel_option", "trust_precision"],
        "voice_notes": (
            "Namaste for senior customer — respectful. Three molecule names show precision. "
            "Exact date from trigger payload. Total + savings calculated and shown. "
            "Two options (CONFIRM or call) covers digital and non-digital users. "
            "Sent to son's number from customer preferences."
        ),
    },

    "pharmacies__perf_dip": {
        "body": (
            "Ramesh, your Apollo Health Plus listing had 12% fewer clicks to calls this week. "
            "Your 3 nearest competitors updated their 'available medicines' list in the last 2 weeks — "
            "yours shows last updated 5 months ago. "
            "Customers searching for specific brands can't verify you stock them. "
            "Want me to update your top-20 chronic medicine brands on your listing? "
            "I'll draft the list, you confirm."
        ),
        "cta": "Want me to draft the medicines list for confirmation?",
        "send_as": "vera",
        "score": 47,
        "levers": ["specificity", "competitive_gap", "cause_explanation", "effort_externalization"],
        "voice_notes": (
            "CTR drop from performance delta. Competitor update timing from trigger payload. "
            "5-month staleness from signals. Root cause + fix. Confirmation step gives control."
        ),
    },

    "pharmacies__perf_spike": {
        "body": (
            "Ramesh, Apollo Health Plus had 1,840 profile views this week — up 29% vs monthly average. "
            "Your chronic-Rx customer count (240 active) is the anchor. "
            "One gap: your listing shows no 'online order' option even though you deliver. "
            "Adding a WhatsApp order link could convert 15-20% of this extra traffic. "
            "Want me to set up the link + add it to your profile now?"
        ),
        "cta": "Want me to set up the WhatsApp order link?",
        "send_as": "vera",
        "score": 47,
        "levers": ["social_proof", "specificity", "merchant_fit", "effort_externalization"],
        "voice_notes": (
            "1,840 views and 29% delta from performance snapshot. "
            "240 chronic-Rx customers from customer_aggregate — not invented. "
            "Missing online order link from signals. "
            "15-20% conversion estimate is conservative and stated as estimate."
        ),
    },

    "pharmacies__festival_upcoming": {
        "body": (
            "Ramesh, winter season starting — cold, cough and BP medicine demand typically "
            "spikes 35% in Malviya Nagar in November-December (your highest repeat-Rx month). "
            "Your stock of azithromycin and cetirizine was low last December. "
            "Good window to reorder now before the rush. "
            "Want me to draft a pre-winter stock checklist for your 240 chronic customers?"
        ),
        "cta": "Want me to draft the stock checklist?",
        "send_as": "vera",
        "score": 47,
        "levers": ["seasonal_beat", "specificity", "historical_data", "effort_externalization"],
        "voice_notes": (
            "35% spike from category seasonal_beats. Specific months. "
            "Azithromycin and cetirizine from merchant stock history or conversation_history. "
            "240 chronic customers from customer_aggregate."
        ),
    },

    "pharmacies__curious_ask": {
        "body": (
            "Ramesh, quick check — which chronic condition medicines do customers "
            "most often ask about that you run out of stock on? "
            "I'll set up a 'notify me when in stock' WhatsApp flow for those SKUs. "
            "Keeps customers from going to competitors when you're OOS."
        ),
        "cta": "Which medicines do you most often run out of?",
        "send_as": "vera",
        "score": 46,
        "levers": ["asking_merchant", "loss_aversion", "reciprocity", "low_commitment"],
        "voice_notes": (
            "Asking-the-merchant lever. Loss aversion frame (OOS = competitor). "
            "Concrete deliverable: notify-me WhatsApp flow. No money or decision required."
        ),
    },

    "pharmacies__customer_lapsed_soft": {
        "body": (
            "Namaste — Apollo Health Plus Malviya Nagar yahan. "
            "Priya ji, aapki last purchase 3 mahine pehle thi. "
            "Agar aapki koi bhi regular medicine khatam hone wali hai, "
            "humara home delivery 5pm tak available hai — senior 15% discount ke saath. "
            "Koi prescription ho ya na ho, WhatsApp par list bhej dijiye. Hum confirm karenge."
        ),
        "cta": "Apni medicine list WhatsApp par bhejiye.",
        "send_as": "merchant_on_behalf",
        "score": 47,
        "levers": ["language_mix", "specificity", "zero_barrier_cta", "trust_precision"],
        "voice_notes": (
            "Hindi-dominant for senior customer. 3-month gap from customer data. "
            "Senior discount from active offer. "
            "No prescription barrier removed — important for chronic patients. "
            "WhatsApp list CTA is lowest friction for this segment."
        ),
    },

    "pharmacies__supply_alert": {
        "body": (
            "Ramesh, urgent: voluntary recall on 2 atorvastatin batches "
            "(AT2024-1102, AT2024-1108) by Mfr Z — sub-potency, no safety risk, "
            "but customers should be informed for replacement. "
            "Pulled your repeat-Rx list: 22 of your chronic-Rx customers were dispensed "
            "these batches in the last 90 days. "
            "Want me to draft their WhatsApp note + the replacement-pickup workflow?"
        ),
        "cta": "Want me to draft the note + workflow?",
        "send_as": "vera",
        "score": 50,
        "levers": ["urgency", "specificity", "derived_count", "effort_externalization"],
        "voice_notes": (
            "Batch numbers exact and verifiable from trigger payload. "
            "'Sub-potency, no safety risk' is precise clinical framing — not alarming, not minimising. "
            "22 customers derived from customer_aggregate filtered by batches — grounded. "
            "End-to-end workflow offer = maximum effort externalization."
        ),
    },

    "pharmacies__regulation_change": {
        "body": (
            "Ramesh, DCI circular just issued — Schedule H1 cold chain storage "
            "requirements tightened from 1 Jan 2027. "
            "Pharmacies without compliant log records face license suspension from Q1 inspections. "
            "Most pharmacies in Malviya Nagar haven't updated their storage logs yet. "
            "I can draft your compliance checklist + a patient notice for biologics customers. "
            "Want both?"
        ),
        "cta": "Want the checklist + patient notice?",
        "send_as": "vera",
        "score": 49,
        "levers": ["urgency", "specificity", "social_proof", "effort_externalization"],
        "voice_notes": (
            "DCI source from category digest. Specific schedule name and effective date. "
            "License suspension is a real consequence — not exaggerated. "
            "Social proof: most pharmacies haven't updated. "
            "Two deliverables: checklist + patient notice."
        ),
    },

}


# ─────────────────────────────────────────────────────────────────────────────
# RETRIEVAL FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

# Normalise trigger kind aliases → canonical keys used in EXAMPLE_STORE
_KIND_ALIASES = {
    "research_digest_release":      "research_digest",
    "category_research_digest":     "research_digest",
    "performance_spike":            "perf_spike",
    "performance_dip":              "perf_dip",
    "customer_recall_due":          "recall_due",
    "lapsed_soft":                  "customer_lapsed_soft",
    "lapsed_hard":                  "customer_lapsed_hard",
    "bridal_followup":              "recall_due",
    "appointment_tomorrow":         "recall_due",
    "scheduled_recurring":          "curious_ask",
    "dormant_with_vera":            "curious_ask",
    "active_planning_intent":       "active_planning_intent",
    "ipl_match_today":              "festival_upcoming",
    "weather_heatwave":             "festival_upcoming",
    "local_news_event":             "festival_upcoming",
    "competitor_opened":            "perf_dip",
    "review_theme_emerged":         "curious_ask",
    "milestone_reached":            "perf_spike",
}


def _normalise(trigger_kind: str) -> str:
    return _KIND_ALIASES.get(trigger_kind, trigger_kind)


def get_examples(category_slug: str, trigger_kind: str, n: int = 2) -> list[dict]:
    """
    Retrieve top-n gold examples for (category_slug, trigger_kind).

    Priority:
      1. Exact match
      2. Same category, different trigger (sorted by score desc)
      3. Global fallback (sorted by score desc)
    """
    kind = _normalise(trigger_kind)
    exact_key = f"{category_slug}__{kind}"
    results = []

    if exact_key in EXAMPLE_STORE:
        results.append(EXAMPLE_STORE[exact_key])

    if len(results) < n:
        cat_examples = [
            v for k, v in EXAMPLE_STORE.items()
            if k.startswith(f"{category_slug}__") and k != exact_key
        ]
        cat_examples.sort(key=lambda x: x["score"], reverse=True)
        results.extend(cat_examples[:n - len(results)])

    if len(results) < n:
        global_examples = [
            v for v in EXAMPLE_STORE.values()
            if v not in results
        ]
        global_examples.sort(key=lambda x: x["score"], reverse=True)
        results.extend(global_examples[:n - len(results)])

    return results[:n]


def get_levers(trigger_kind: str) -> list[str]:
    """Return recommended compulsion levers for this trigger kind."""
    kind = _normalise(trigger_kind)
    return LEVER_MAP.get(kind, LEVER_MAP["_default"])


def format_for_prompt(
    category_slug: str,
    trigger_kind: str,
    n: int = 2,
    include_anti_patterns: bool = True
) -> str:
    """
    Build the full RAG injection block for the compose prompt.
    Includes gold examples + lever instructions + anti-patterns.
    """
    examples = get_examples(category_slug, trigger_kind, n)
    levers = get_levers(trigger_kind)
    lines = []

    lines.append("=== GOLD STANDARD EXAMPLES — mirror this quality ===")
    for i, ex in enumerate(examples, 1):
        lines.append(f"\nExample {i} (judge score: {ex['score']}/50):")
        lines.append(f"Body:\n{ex['body']}")
        lines.append(f"CTA: {ex['cta']}")
        lines.append(f"Why it scores high: {ex['voice_notes']}")
        lines.append(f"Compulsion levers: {', '.join(ex['levers'])}")

    lines.append(f"\n=== COMPULSION LEVERS FOR '{trigger_kind}' — use at least 2 ===")
    lines.append(", ".join(levers))

    if include_anti_patterns:
        lines.append("\n=== ANTI-PATTERNS — these get penalised by the judge ===")
        for ap in ANTI_PATTERNS[:3]:
            lines.append(f'BAD: "{ap["bad_body"][:90]}..."')
            lines.append(f'Why bad: {ap["why_bad"]}')

    lines.append(
        "\nNow compose a NEW message using ONLY facts from the merchant/trigger context below. "
        "Match the gold example quality. Different merchant, different facts, same standard."
    )

    return "\n".join(lines)


# # rag_store.py  — build this ONCE before submission

# import json
# import os

# # Your gold examples — generated from the 10 case studies + expanded versions
# # Key format: "category__trigger_kind"
# EXAMPLE_STORE = {
#     "dentists__research_digest": {
#         "body": "Dr. Meera, JIDA's Oct issue landed. One item relevant to your high-risk adult patients — 2,100-patient trial showed 3-month fluoride recall cuts caries recurrence 38% better than 6-month. Worth a look (2-min abstract). Want me to pull it + draft a patient-ed WhatsApp you can share?  — JIDA Oct 2026 p.14",
#         "cta": "Want me to pull it?",
#         "score": 50,
#         "levers": ["specificity", "reciprocity", "curiosity"]
#     },
#     "dentists__recall_due": {
#         "body": "Hi Priya, Dr. Meera's clinic here 🦷 It's been 5 months since your last visit — your 6-month cleaning recall is due. Apke liye 2 slots ready hain: Wed 5 Nov, 6pm ya Thu 6 Nov, 5pm. ₹299 cleaning + complimentary fluoride. Reply 1 for Wed, 2 for Thu, or tell us a time that works.",
#         "cta": "Reply 1 or 2",
#         "score": 49,
#         "levers": ["specificity", "language_mix", "preference_honored"]
#     },
#     "restaurants__ipl_match": {
#         "body": "Quick heads-up Suresh — DC vs MI at Arun Jaitley tonight, 7:30pm. Important: Saturday IPL matches usually shift -12% restaurant covers (people watch at home). Skip the match-night promo today; instead push your BOGO pizza (already active) as a delivery-only Saturday special. Want me to draft the Swiggy banner + an Insta story? Live in 10 min.",
#         "cta": "Want me to draft it? Live in 10 min.",
#         "score": 50,
#         "levers": ["contrarian_insight", "loss_aversion", "effort_externalization"]
#     },
#     "gyms__seasonal_perf_dip": {
#         "body": "Karthik, your views are down 30% this week — but I want to flag this is the normal April-June acquisition lull (every metro gym sees -25 to -35% in this window). Action: skip ad spend now, save it for Sept-Oct when conversion is 2x. For now, focus retention on your 245 members. Want me to draft a 'summer attendance challenge' to keep them through the dip?",
#         "cta": "Want me to draft the challenge?",
#         "score": 48,
#         "levers": ["anxiety_preemption", "data_anchor", "reframe"]
#     },
#     "pharmacies__supply_alert": {
#         "body": "Ramesh, urgent: voluntary recall on 2 atorvastatin batches (AT2024-1102, AT2024-1108) by Mfr Z — sub-potency, no safety risk, but customers should be informed for replacement. Pulled your repeat-Rx list: 22 of your chronic-Rx customers were dispensed these batches in last 90 days. Want me to draft their WhatsApp note + the replacement-pickup workflow?",
#         "cta": "Want me to draft the note + workflow?",
#         "score": 50,
#         "levers": ["urgency", "specificity", "effort_externalization"]
#     },
#     "salons__curious_ask": {
#         "body": "Hi Lakshmi! Quick check — what service has been most asked-for this week at Studio11? I'll turn the answer into a Google post + a 4-line WhatsApp reply you can use when customers ask about pricing. Takes 5 min.",
#         "cta": "What's been most asked this week?",
#         "score": 44,
#         "levers": ["asking_merchant", "reciprocity", "effort_externalization"]
#     },
#     "gyms__customer_lapsed_hard": {
#         "body": "Hi Rashmi 👋 Karthik from PowerHouse here. It's been about 8 weeks — happens to most members at some point, no judgment. We've added a Tue/Thu evening HIIT class that fits weight-loss goals well (45 min, 6:30pm). Want me to hold a free trial spot for you next Tue, 30 Apr? Reply YES — no commitment, no auto-charge.",
#         "cta": "Reply YES — no commitment.",
#         "score": 50,
#         "levers": ["no_shame", "specific_class", "zero_barrier_cta"]
#     },
#     "pharmacies__chronic_refill_due": {
#         "body": "Namaste — Apollo Health Plus Malviya Nagar yahan. Sharma ji ki 3 monthly medicines (metformin, atorvastatin, telmisartan) 28 April ko khatam hongi. Same dose, same brand pack ready hai. Senior discount 15% applied — total ₹1,420 (₹240 saved). Free home delivery to saved address by 5pm tomorrow. Reply CONFIRM to dispatch, or call 9876543210 if any change in dosage.",
#         "cta": "Reply CONFIRM to dispatch.",
#         "score": 49,
#         "levers": ["molecule_names", "savings_shown", "two_channel_option"]
#     },
#     # Add more for: restaurants__active_planning, salons__bridal_followup,
#     # restaurants__perf_spike, gyms__milestone, pharmacies__regulation_change ...
# }

# def get_examples(category_slug: str, trigger_kind: str, n: int = 2) -> list[dict]:
#     """
#     Get the best matching examples for this category+trigger combination.
#     Falls back gracefully — never crashes.
#     """
#     # Exact match first
#     key = f"{category_slug}__{trigger_kind}"
#     if key in EXAMPLE_STORE:
#         return [EXAMPLE_STORE[key]]
    
#     # Category-only fallback — find best examples for this category
#     category_examples = [
#         v for k, v in EXAMPLE_STORE.items() 
#         if k.startswith(f"{category_slug}__")
#     ]
#     if category_examples:
#         # Sort by score, return top n
#         return sorted(category_examples, key=lambda x: x["score"], reverse=True)[:n]
    
#     # Global fallback — return highest scoring examples
#     all_examples = sorted(EXAMPLE_STORE.values(), key=lambda x: x["score"], reverse=True)
#     return all_examples[:n]


# def format_examples_for_prompt(examples: list[dict]) -> str:
#     """Format retrieved examples into the prompt injection block."""
#     if not examples:
#         return ""
    
#     lines = ["=== GOLD STANDARD EXAMPLES (mirror this quality) ==="]
#     for i, ex in enumerate(examples, 1):
#         lines.append(f"\nExample {i} (score: {ex['score']}/50):")
#         lines.append(f"Body: {ex['body']}")
#         lines.append(f"CTA: {ex['cta']}")
#         lines.append(f"What made it score high: {', '.join(ex['levers'])}")
#     lines.append("\nNow compose a NEW message for the context above. Same quality, different facts.")
#     return "\n".join(lines)