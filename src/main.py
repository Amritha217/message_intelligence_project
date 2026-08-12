import json
from load_data import load_messages, load_mandatory_ids
from classify import classify_all
from extract_tasks import extract_items
from detect_sensitive import detect_all



def build_mandatory_report(mandatory_ids, classifications, tasks_events, sensitive):
    # Index everything by message_id for quick lookup
    class_by_id = {c["message_id"]: c for c in classifications}
    tasks_by_source = {}
    for t in tasks_events:
        tasks_by_source.setdefault(t["source_message_id"], []).append(t)
    sensitive_by_id = {s["message_id"]: s for s in sensitive}

    report = []
    for mid in mandatory_ids:
        entry = {
            "message_id": mid,
            "classification": class_by_id.get(mid),
            "tasks_or_events": tasks_by_source.get(mid, []),
            "sensitive_info": sensitive_by_id.get(mid)
        }
        report.append(entry)
    return report




def run_pipeline():
    print("Step 1: Loading data...")
    messages = load_messages()
    mandatory_ids = load_mandatory_ids()
    print(f"  {len(messages)} messages loaded, {len(mandatory_ids)} mandatory IDs loaded.")

    print("\nStep 2: Classifying messages (Part 1)...")
    classifications = classify_all()
    with open("output/classification.json", "w") as f:
        json.dump(classifications, f, indent=2)
    print(f"  Saved output/classification.json ({len(classifications)} entries)")

    print("\nStep 3: Extracting tasks/events (Part 2)...")
    tasks_events = extract_items()
    with open("output/tasks_events.json", "w") as f:
        json.dump(tasks_events, f, indent=2)
    print(f"  Saved output/tasks_events.json ({len(tasks_events)} entries)")

    print("\nStep 4: Detecting sensitive information (Part 3)...")
    sensitive = detect_all()
    with open("output/sensitive_report.json", "w") as f:
        json.dump(sensitive, f, indent=2)
    print(f"  Saved output/sensitive_report.json ({len(sensitive)} entries)")

    print("\nStep 5: Building mandatory demo ID report...")
    mandatory_report = build_mandatory_report(mandatory_ids, classifications, tasks_events, sensitive)
    with open("output/mandatory_demo_report.json", "w") as f:
        json.dump(mandatory_report, f, indent=2)
    print(f"  Saved output/mandatory_demo_report.json ({len(mandatory_report)} entries)")

    print("\nPipeline complete. All outputs in /output folder.")


if __name__ == "__main__":
    run_pipeline()