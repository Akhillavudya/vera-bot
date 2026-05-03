# Expanded Policy Engine with Semantic Constraints
CATEGORY_POLICY = {
    "dentists": {
        "tone": "clinical",
        "avoid": ["guaranteed cure", "painless guaranteed", "100% results", "cheap", "sale", "discount"],
        "prefix": "Dr.",
        "default_offer": "Comprehensive Dental Consultation",
        "industry_metric": "Patient Retention Rate"
    },
    "salons": {
        "tone": "friendly",
        "avoid": ["medical claims", "surgery", "cure"],
        "prefix": "",
        "default_offer": "Haircut & Styling @ ₹199",
        "industry_metric": "Visit Frequency"
    },
    "restaurants": {
        "tone": "operator",
        "avoid": ["fake scarcity", "permanent closure"],
        "prefix": "Chef",
        "default_offer": "Complimentary Appetizer with Main Course",
        "industry_metric": "Table Occupancy"
    },
    "gyms": {
        "tone": "motivating",
        "avoid": ["guaranteed weight loss", "magic pill", "overnight results"],
        "prefix": "Coach",
        "default_offer": "Personal Training Trial Session",
        "industry_metric": "Member Churn Rate"
    },
    "pharmacies": {
        "tone": "trustworthy",
        "avoid": ["medical cure claims", "prescription misuse", "bargain", "clearance"],
        "prefix": "Pharmacist",
        "default_offer": "Health Wellness Checkup",
        "industry_metric": "Refill Adherence"
    }
}

def clean_offer_text(offer: str, avoid_list: list) -> str:
    """
    Sanitizes the offer title based on industry-specific forbidden words.
    Example: Converts 'Cheap Dental Sale' -> 'Dental Benefit' for a Doctor.
    """
    if not offer:
        return "Exclusive Benefit"
        
    cleaned = offer
    for word in avoid_list:
        if word.lower() in cleaned.lower():
            # Replace 'Sale/Discount/Cheap' with professional synonyms
            cleaned = cleaned.replace(word, "Special Benefit").replace(word.capitalize(), "Special Benefit")
    
    return cleaned

def get_category_policy(category_slug: str) -> dict:
    slug = category_slug.lower().strip()
    
    # Check for both singular and plural versions
    if slug in CATEGORY_POLICY:
        return CATEGORY_POLICY[slug]
    if f"{slug}s" in CATEGORY_POLICY:
        return CATEGORY_POLICY[f"{slug}s"]
    if slug.endswith('s') and slug[:-1] in CATEGORY_POLICY:
        return CATEGORY_POLICY[slug[:-1]]

    # Absolute fallback
    return {
        "tone": "business",
        "avoid": [],
        "prefix": "",
        "default_offer": "Standard Promotion",
        "industry_metric": "Customer Engagement"
    }
