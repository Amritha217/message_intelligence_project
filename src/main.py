import json
from load_data import load_messages, load_mandatory_ids
from classify import classify_all
from extract_tasks import extract_items
from detect_sensitive import detect_all
from priority_engine import build_priorities
from group_messages import build_groups
from privacy_routing import build_privacy_routing
from run_demo_queries import run_all_demo_queries
from benchmark import run_benchmark
from assistant import save_data_cache

def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {path} ({len(data)} entries)")


def run_pipeline():
    print("=== L1 Pipeline ===")
    save("output/classification.json", classify_all())
    save("output/tasks_events.json", extract_items())
    save("output/sensitive_report.json", detect_all())

    print("\n=== L2 Pipeline ===")
    save("output/priority_report.json", build_priorities())
    save("output/related_groups.json", build_groups())
    save("output/privacy_routing.json", build_privacy_routing())
    save("output/mandatory_query_answers.json", run_all_demo_queries())
    save_data_cache()
    save("output/benchmark_report.json", run_benchmark())

    print("\nPipeline complete. All outputs in /output folder.")


if __name__ == "__main__":
    run_pipeline()