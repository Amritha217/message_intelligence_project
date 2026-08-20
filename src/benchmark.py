import json
import time
from load_l2_data import load_combined_messages
from priority_engine import key_words


def run_grouping(df, threshold):
    groups = []
    for _, row in df.iterrows():
        words = key_words(row["message"])
        matched = None
        for g in groups:
            if len(g["words"] & words) >= threshold:
                matched = g
                break
        if matched:
            matched["message_ids"].append(row["message_id"])
            matched["words"] |= words
        else:
            groups.append({"message_ids": [row["message_id"]], "words": words})

    real_groups = [g for g in groups if len(g["message_ids"]) >= 2]
    avg_size = (
        sum(len(g["message_ids"]) for g in real_groups) / len(real_groups)
        if real_groups else 0
    )
    return {
        "threshold": threshold,
        "total_groups_with_2plus_messages": len(real_groups),
        "avg_messages_per_group": round(avg_size, 2),
        "largest_group_size": max((len(g["message_ids"]) for g in real_groups), default=0)
    }


def run_benchmark():
    df = load_combined_messages()

    report = []
    for threshold in [2, 3, 4]:
        start = time.time()
        stats = run_grouping(df, threshold)
        stats["time_seconds"] = round(time.time() - start, 3)
        report.append(stats)

    return report


if __name__ == "__main__":
    report = run_benchmark()
    with open("output/benchmark_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Benchmark comparison (word-overlap threshold for related-message grouping):")
    for r in report:
        print(r)
    print("\nSaved to output/benchmark_report.json")