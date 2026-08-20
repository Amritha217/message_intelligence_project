import json
from load_l2_data import load_l2_demo_queries
from assistant import load_all_data, answer_query


def run_all_demo_queries():
    queries_df = load_l2_demo_queries()
    data = load_all_data()

    results = []
    for _, row in queries_df.iterrows():
        answer = answer_query(row["query"], data)
        answer["query_id"] = row["query_id"]
        results.append(answer)

    return results


if __name__ == "__main__":
    results = run_all_demo_queries()
    with open("output/mandatory_query_answers.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"Answered {len(results)} mandatory demo queries -> output/mandatory_query_answers.json")

    for r in results:
        print(f"\n[{r['query_id']}] {r['query']}\n-> {r['answer']}")