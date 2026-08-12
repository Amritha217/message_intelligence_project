import re
import json
from load_data import load_messages
from classify import classify_message


DATE_PATTERNS = [
    r"\b(\d{4}-\d{2}-\d{2})\b",        # 2026-09-19
    r"\b(\d{2}-\d{2}-\d{4})\b",        # 19-09-2026
]


TIME_PATTERN = r"\b(\d{1,2}:\d{2})\b"

URGENT_WORDS = ["urgent", "asap", "immediately", "important", "must"]

PERSON_PATTERNS = [
    r"\bwith\s+([A-Z][a-z]+)\b",
    r"\bfor\s+([A-Z][a-z]+)\b",
]


PREAMBLE_PHRASES = [
    "for today", "reminder", "note", "fyi", "heads up", "update",
    "quick update", "just a note", "calendar update", "notice"
]



def extract_date(text):
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def extract_time(text):
    match = re.search(TIME_PATTERN, text)
    if match:
        return match.group(1)
    return None


def extract_person(text):
    for pattern in PERSON_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def extract_priority(text, has_date):
    text_lower = text.lower()
    if any(word in text_lower for word in URGENT_WORDS):
        return "high"
    if has_date:
        return "medium"
    return "low"


def extract_title(text):
    working_text = text.strip()

   
    if ":" in working_text:
        prefix, rest = working_text.split(":", 1)
        if prefix.strip().lower() in PREAMBLE_PHRASES:
            working_text = rest.strip()

    
    first_part = re.split(r"[.,;]", working_text)[0].strip()

    
    first_part = re.sub(
        r"^(don't forget to|please|kindly|make sure to|you need to)\s+",
        "",
        first_part,
        flags=re.IGNORECASE
    )

    words = first_part.split()
    title = " ".join(words[:8])
    return title if title else working_text[:40]


def extract_items():
    df = load_messages()
    items = []
    task_counter = 1
    event_counter = 1

    for _, row in df.iterrows():
        text = row["message"]
        category, _, _ = classify_message(text)

        if category not in ("action_required", "meeting_or_event"):
            continue

        item_type = "task" if category == "action_required" else "event"
        date = extract_date(text)
        time = extract_time(text)
        person = extract_person(text)
        priority = extract_priority(text, has_date=bool(date))

        if item_type == "task":
            item_id = f"TASK_{task_counter:03d}"
            task_counter += 1
        else:
            item_id = f"EVENT_{event_counter:03d}"
            event_counter += 1

        items.append({
            "item_id": item_id,
            "type": item_type,
            "title": extract_title(text),
            "description": text,
            "deadline": date,
            "time": time,
            "person": person,
            "priority": priority,
            "source_message_id": row["message_id"]
        })

    return items


if __name__ == "__main__":
    items = extract_items()
    with open("output/tasks_events.json", "w") as f:
        json.dump(items, f, indent=2)
    print(f"Extracted {len(items)} tasks/events. Saved to output/tasks_events.json")

    tasks = sum(1 for i in items if i["type"] == "task")
    events = sum(1 for i in items if i["type"] == "event")
    print(f"  Tasks: {tasks}, Events: {events}")