import json
from load_l2_data import load_combined_messages
from extract_tasks import extract_date
from priority_engine import key_words, compute_common_words, build_priorities, MIN_SHARED_WORDS

CANCELLED_WORDS = ["cancelled", "canceled", "no longer happening", "called off", "cancel the"]
RESCHEDULED_WORDS = ["reschedul", "moved to", "postponed", "pushed to", "new date", "new time", "changed to"]
COMPLETED_WORDS = ["completed", "submitted", "has been done", "resolved", "confirmed successfully", "finished", "wrapped up"]
PROGRESS_WORDS = ["working on", "in progress", "started", "reviewing", "currently"]
PENDING_WORDS = ["please submit", "reminder", "pending", "waiting", "have you", "don't forget", "please share"]


def detect_status(texts):
    combined = " ".join(texts).lower()
    if any(w in combined for w in CANCELLED_WORDS):
        return "cancelled"
    if any(w in combined for w in RESCHEDULED_WORDS):
        return "rescheduled"
    if any(w in combined for w in COMPLETED_WORDS):
        return "completed"
    if any(w in combined for w in PROGRESS_WORDS):
        return "in_progress"
    if any(w in combined for w in PENDING_WORDS):
        return "pending"
    return "unclear"


def make_title(first_message_text):
    words = first_message_text.strip().split()
    return " ".join(words[:6])


def build_groups():
    df = load_combined_messages()
    common_words = compute_common_words(df)
    groups = []

    priorities = build_priorities()
    item_by_message = {p["message_id"]: p["item_id"] for p in priorities}

    for _, row in df.iterrows():
        msg_id, text = row["message_id"], row["message"]
        words = key_words(text, common_words)

        matched_group = None
        for g in groups:
            if words and len(g["words"] & words) >= MIN_SHARED_WORDS:
                matched_group = g
                break

        if matched_group:
            matched_group["message_ids"].append(msg_id)
            matched_group["texts"].append(text)
            matched_group["words"] |= words
        else:
            groups.append({
                "group_id": f"GROUP_{len(groups)+1:03d}",
                "title": make_title(text),
                "message_ids": [msg_id],
                "texts": [text],
                "words": words
            })

    output = []
    for g in groups:
        if len(g["message_ids"]) < 2:
            continue

        status = detect_status(g["texts"])
        deadlines = [extract_date(t) for t in g["texts"]]
        deadlines = [d for d in deadlines if d]
        latest_deadline = deadlines[-1] if deadlines else None
        confidence = round(min(0.5 + 0.1 * len(g["message_ids"]), 0.95), 2)
        summary = (
            f"{len(g['message_ids'])} related messages found on this subject; "
            f"current status is '{status}'."
        )
        related_items = list({item_by_message[m] for m in g["message_ids"] if m in item_by_message})

        output.append({
            "group_id": g["group_id"],
            "title": g["title"],
            "related_message_ids": g["message_ids"],
            "related_task_or_event_ids": related_items,
            "status": status,
            "latest_deadline": latest_deadline,
            "summary": summary,
            "confidence": confidence
        })

    return output


if __name__ == "__main__":
    groups = build_groups()
    with open("output/related_groups.json", "w") as f:
        json.dump(groups, f, indent=2)
    print(f"Generated {len(groups)} related-message groups -> output/related_groups.json")

    from collections import Counter
    print(Counter(g["status"] for g in groups))
    sizes = sorted((len(g["related_message_ids"]) for g in groups), reverse=True)
    print(f"Largest group size: {sizes[0] if sizes else 0}")