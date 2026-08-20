import re
import json
from collections import Counter
from datetime import datetime
from load_l2_data import load_combined_messages
from classify import classify_message
from extract_tasks import extract_date
from detect_sensitive import detect_sensitive

URGENT_WORDS = ["urgent", "asap", "immediately", "critical", "important"]
RESPONSE_WORDS = ["can you", "could you", "please confirm", "please share", "?"]
OVERDUE_WORDS = ["overdue", "still pending", "haven't received", "missed the deadline"]
DONE_WORDS = ["completed", "done", "submitted", "resolved", "cancelled"]

STOPWORDS = {"the", "a", "an", "to", "for", "of", "is", "on", "at", "and", "please", "your",
             "you", "can", "will", "with", "this", "that", "have", "has", "are", "was", "update"}

MIN_SHARED_WORDS = 3          
COMMON_WORD_FRACTION = 0.02   


def base_words(text):
    words = re.findall(r"[a-z]+", text.lower())
    return set(w for w in words if w not in STOPWORDS and len(w) > 3)


def compute_common_words(df):
    
    doc_freq = Counter()
    for text in df["message"]:
        doc_freq.update(base_words(text))
    total = len(df)
    return {w for w, c in doc_freq.items() if c / total > COMMON_WORD_FRACTION}


def key_words(text, common_words=None):
    words = base_words(text)
    if common_words:
        words = words - common_words
    return words


def score_item(text, deadline, msg_time, is_sensitive):
    signals = []
    score = 0
    t = text.lower()

    if deadline:
        try:
            days_left = (datetime.strptime(deadline, "%Y-%m-%d").date() - msg_time.date()).days
            if days_left < 0:
                signals.append("deadline_overdue"); score += 4
            elif days_left == 0:
                signals.append("deadline_today"); score += 4
            elif days_left <= 2:
                signals.append("deadline_soon"); score += 2
        except ValueError:
            pass

    if any(w in t for w in URGENT_WORDS):
        signals.append("urgent_keyword"); score += 3
    if is_sensitive:
        signals.append("sensitive_related"); score += 2
    if any(w in t for w in RESPONSE_WORDS):
        signals.append("response_required"); score += 1
    if any(w in t for w in OVERDUE_WORDS):
        signals.append("overdue_phrasing"); score += 3
    if any(w in t for w in DONE_WORDS):
        signals.append("marked_done"); score -= 3

    return signals, score


def score_to_priority(score):
    if score >= 7:
        return "critical"
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def build_priorities():
    df = load_combined_messages()
    common_words = compute_common_words(df)
    items = []
    task_n, event_n = 1, 1

    for _, row in df.iterrows():
        text, msg_id, msg_time = row["message"], row["message_id"], row["timestamp"]
        category, _, _ = classify_message(text)
        is_sensitive = detect_sensitive(text) is not None
        words = key_words(text, common_words)

        followed_item = None
        for item in reversed(items):
            if words and len(item["words"] & words) >= MIN_SHARED_WORDS:
                followed_item = item
                break

        if followed_item is not None:
            new_signals, new_score = score_item(text, None, msg_time, is_sensitive)
            followed_item["score"] += new_score
            followed_item["signals"] = list(set(followed_item["signals"] + new_signals))
            followed_item["priority"] = score_to_priority(followed_item["score"])
            followed_item["reason"] = f"Updated by follow-up message {msg_id} with signals {new_signals}."
            followed_item["updated_by"] = msg_id
            continue

        if category not in ("action_required", "meeting_or_event"):
            continue

        item_type = "task" if category == "action_required" else "event"
        if item_type == "task":
            item_id = f"TASK_{task_n:03d}"; task_n += 1
        else:
            item_id = f"EVENT_{event_n:03d}"; event_n += 1

        deadline = extract_date(text)
        signals, score = score_item(text, deadline, msg_time, is_sensitive)
        priority = score_to_priority(score)
        reason = f"Priority based on signals: {signals}" if signals else "No strong urgency signals found."

        items.append({
            "message_id": msg_id,
            "item_id": item_id,
            "priority": priority,
            "reason": reason,
            "signals": signals,
            "score": score,
            "words": words,
            "updated_by": None
        })

    output = []
    for it in items:
        confidence = round(min(0.5 + 0.1 * len(it["signals"]), 0.95), 2)
        output.append({
            "message_id": it["message_id"],
            "item_id": it["item_id"],
            "priority": it["priority"],
            "reason": it["reason"],
            "signals": it["signals"],
            "confidence": confidence,
            "updated_by_message_id": it["updated_by"]
        })
    return output


if __name__ == "__main__":
    results = build_priorities()
    with open("output/priority_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"Generated {len(results)} priority entries -> output/priority_report.json")

    from collections import Counter as C
    print(C(r["priority"] for r in results))
    print(f"Updated by follow-up: {sum(1 for r in results if r['updated_by_message_id'])}")