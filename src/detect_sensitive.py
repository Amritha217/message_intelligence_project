import re
import json
from load_data import load_messages


SENSITIVE_RULES = [
    ("one_time_password", r"\botp\s*(?:is|:)?\s*(\d{4,8})\b", "high", "do_not_store"),
    ("password", r"\bpassword\s*(?:is|:)?\s*([^\s,.;]{4,})", "high", "do_not_store"),
    ("pin", r"\bpin\s*(?:is|:)?\s*(\d{4,6})\b", "high", "do_not_store"),
    ("cvv", r"\bcvv\s*(?:is|:)?\s*(\d{3,4})\b", "high", "do_not_store"),
    ("api_token", r"\b(?:token|api\s*key)\s*(?:is|:)?\s*([A-Za-z0-9\-_]{6,})", "high", "do_not_store"),
    ("card_or_account_number", r"\b(\d{9,19})\b", "high", "do_not_send_external"),
    ("private_phone", r"\b(?:phone|contact|mobile)\s*(?:number|no\.?)?\s*(?:is|:)?\s*(\+?\d{7,13})\b", "medium", "ask_for_confirmation"),
    ("private_address", r"\baddress\s*(?:is|:)?\s*([A-Za-z0-9,.\s]{10,60})", "medium", "ask_for_confirmation"),
]


def mask_value(text, value):
    return text.replace(value, "*" * min(len(value), 6))


def detect_sensitive(text):
    for sens_type, pattern, risk, action in SENSITIVE_RULES:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1)
            masked = mask_value(text, value)
            return sens_type, risk, masked, action
    return None


def detect_all():
    df = load_messages()
    results = []
    for _, row in df.iterrows():
        detection = detect_sensitive(row["message"])
        if detection:
            sens_type, risk, masked_text, action = detection
            results.append({
                "message_id": row["message_id"],
                "sensitivity_type": sens_type,
                "risk": risk,
                "masked_text": masked_text,
                "recommended_action": action
            })
    return results


if __name__ == "__main__":
    results = detect_all()
    with open("output/sensitive_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"Detected {len(results)} sensitive messages. Saved to output/sensitive_report.json")

    from collections import Counter
    counts = Counter(r["sensitivity_type"] for r in results)
    print("\nSensitivity type distribution:")
    for t, c in counts.items():
        print(f"  {t}: {c}")