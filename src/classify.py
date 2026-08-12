import re
import json
from load_data import load_messages


# --- Keyword/pattern rules per category ---

SENSITIVE_PATTERNS = [
    r"\botp\b", r"\bpassword\b", r"\bpin\b", r"\bcvv\b",
    r"\baccount\s*number\b", r"\bcard\s*number\b", r"\btoken\b",
    r"\bssn\b", r"\baadhaar\b", r"\bapi\s*key\b"
]

ACTION_KEYWORDS = [
    "please submit", "please complete", "reminder", "deadline",
    "need to", "make sure", "don't forget", "action required",
    "kindly", "you must", "complete the", "submit the", "pay the", "pending"
]

MEETING_KEYWORDS = [
    "meeting", "calendar", "scheduled", "event", "appointment",
    "call at", "join us", "conference", "session at", "invite"
]

PROMO_KEYWORDS = [
    "offer", "discount", "sale", "% off", "subscribe", "limited time",
    "buy now", "free trial", "deal", "promo code", "coupon"
]

PERSONAL_KEYWORDS = [
    "my address", "my number", "family", "birthday", "home town",
    "personal", "my daughter", "my son", "my wife", "my husband", "my phone"
]


def match_count(text, keywords):
    text = text.lower()
    return sum(1 for kw in keywords if kw in text)


def has_sensitive_pattern(text):
    text = text.lower()
    return any(re.search(p, text) for p in SENSITIVE_PATTERNS)



def classify_message(text):
    # 1. Sensitive Information — highest priority
    if has_sensitive_pattern(text):
        return "sensitive_information", 0.9, "Message contains a sensitive keyword pattern (e.g. OTP, password, account number)."

    # 2. Action Required
    action_hits = match_count(text, ACTION_KEYWORDS)
    if action_hits > 0:
        conf = min(0.6 + 0.1 * action_hits, 0.95)
        return "action_required", conf, "Message contains an instruction/request phrase (e.g. 'please submit', 'reminder')."

    # 3. Meeting or Event
    meeting_hits = match_count(text, MEETING_KEYWORDS)
    if meeting_hits > 0:
        conf = min(0.6 + 0.1 * meeting_hits, 0.95)
        return "meeting_or_event", conf, "Message references a meeting, event, or calendar item."

    # 4. Personal Information
    personal_hits = match_count(text, PERSONAL_KEYWORDS)
    if personal_hits > 0:
        conf = min(0.55 + 0.1 * personal_hits, 0.9)
        return "personal_information", conf, "Message shares personal/family-related details."

    # 5. Promotional
    promo_hits = match_count(text, PROMO_KEYWORDS)
    if promo_hits > 0:
        conf = min(0.6 + 0.1 * promo_hits, 0.95)
        return "promotional", conf, "Message contains promotional/marketing language (e.g. discount, offer)."

    # 6. Fallback
    return "general_information", 0.5, "No strong signals matched; treated as general information by default."


def classify_all():
    df = load_messages()
    results = []
    for _, row in df.iterrows():
        category, confidence, reason = classify_message(row["message"])
        results.append({
            "message_id": row["message_id"],
            "category": category,
            "confidence": round(confidence, 2),
            "reason": reason
        })
    return results


if __name__ == "__main__":
    results = classify_all()
    with open("output/classification.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"Classified {len(results)} messages. Saved to output/classification.json")

    
    from collections import Counter
    counts = Counter(r["category"] for r in results)
    print("\nCategory distribution:")
    for cat, cnt in counts.items():
        print(f"  {cat}: {cnt}")