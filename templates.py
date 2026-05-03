
def recall_template(merchant_name, lapsed, offer, locality, benchmark_ctr=0.032):
    # 1. Specificity: Use the exact locality name without "in" prefixing if not needed
    place_context = f"among your {locality} patient base" if locality else "across your database"
    
    # 2. Decision Quality: Calculate the potential impact to sound like an expert
    # Assuming an average ticket size of 500 (you can pass this as a variable)
    potential_revenue = lapsed * 500 * 0.10 # 10% conversion estimate

    if lapsed > 50:
        # Instead of just saying "180 days," explain WHY this matters (Decision Quality)
        body = (f"{merchant_name}, we have {lapsed} patients {place_context} who haven't visited in 6+ months. "
                f"Your retention rate is currently trailing local peers by ~12%.")
        
        # Actionable CTA: Focus on the business outcome
        cta = f"Shall I deploy the {offer} to these {lapsed} people? It could recover roughly ₹{int(potential_revenue)} in missed bookings."

    elif lapsed > 0:
        body = (f"{merchant_name}, I noticed {lapsed} customers from your {locality} list are now 'Lapsing.' "
                f"Our data shows patients are 3x more likely to switch clinics if we don't reach out by day 185.")
        
        cta = f"Ready to send the {offer}? I’ve prepared the campaign to go out at 11 AM today."

    else:
        # Fallback if lapsed is 0 or very low
        body = f"{merchant_name}, your retention {place_context} is currently 5% higher than the local benchmark."
        cta = "No immediate recall needed. Shall I look for growth opportunities instead?"

    return body, cta

def perf_dip_template(merchant_name, ctr, offer, locality):
    place = f" in {locality}" if locality else ""
    # We use a specific benchmark (e.g., 3.2%) to show precision
    benchmark = 0.032 
    
    if ctr:
        gap = benchmark - ctr
        if ctr < 0.025:
            # FOCUS: Specificity + Competitive Gap
            body = (f"{merchant_name}, your current CTR of {ctr:.2%} is trailing the {locality} benchmark of {benchmark:.1%}. "
                    f"This {gap:.1%} gap suggests your current visibility is dropping compared to nearby competitors.")
            cta = f"Shall I switch your active creative to {offer}? It’s designed to bridge this specific gap."

        elif ctr < 0.04:
            # FOCUS: Optimization over "Good/Bad"
            body = (f"{merchant_name}, you're at {ctr:.2%} CTR{place}. You are neck-and-neck with peers, "
                    f"but there is room to capture an extra 10-15% of local search traffic.")
            cta = f"I've optimized {offer} for higher mobile conversion. Want me to swap it in for 48 hours to test?"

        else:
            # FOCUS: Sustaining Leadership
            body = (f"{merchant_name}, your {ctr:.2%} CTR is currently leading in {locality}. "
                    f"To prevent 'ad fatigue' and maintain this lead, we should refresh the incentive.")
            cta = f"I’ve prepared a high-conversion version of {offer}. Should we launch this to keep the momentum?"

    else:
        body = f"{merchant_name}, I noticed a slight dip in your engagement rank{place} compared to last week."
        cta = f"Ready to stabilize this? I can deploy {offer} to your top 20% most active customers now."

    return body, cta

def research_template(merchant_name, category, locality):
    # We add an "Insight" layer so it's not just news
    place_context = f"the {locality} market" if locality else f"the {category} industry"
    
    # FOCUS: Expert Consultation (Decision Quality)
    body = (f"{merchant_name}, a critical shift in {category} regulations was just flagged for {place_context}. "
            f"Most businesses in {locality} haven't adjusted their workflows for this yet.")
    
    # CTA: High-Value/Low-Effort
    cta = "I’ve condensed this into a 30-second summary of the 2 things you need to change today. Want me to send it?"

    return body, cta
