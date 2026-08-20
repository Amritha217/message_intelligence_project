import re
import json
from load_l2_data import load_combined_messages
from priority_engine import key_words, compute_common_words, build_priorities
from group_messages import build_groups
from classify import classify_all
from detect_sensitive import detect_all
from privacy_routing import build_privacy_routing

MIN_RELEVANCE = 0.3

MSG_ID_PATTERN = r"\b([A-Z]+_\d+)\b"


def load_all_data():
    df = load_combined_messages()
    messages_by_id = {row["message_id"]: row["message"] for _, row in df.iterrows()}
    batch_by_id = {row["message_id"]: row["batch"] for _, row in df.iterrows()}
    classifications = {c["message_id"]: c for c in classify_all()}
    priorities = build_priorities()
    groups = build_groups()
    sensitive = {s["message_id"]: s for s in detect_all()}
    privacy = build_privacy_routing()
    common_words = compute_common_words(df)
    return {
        "messages": messages_by_id,
        "batch": batch_by_id,
        "classifications": classifications,
        "priorities": priorities,
        "groups": groups,
        "sensitive": sensitive,
        "privacy": privacy,
        "common_words": common_words
    }


def relevance(query_words, text, common_words):
    text_words = key_words(text, common_words)
    if not query_words:
        return 0
    overlap = query_words & text_words
    return len(overlap) / len(query_words)


def find_group_for_message(msg_id, groups):
    for g in groups:
        if msg_id in g["related_message_ids"]:
            return g
    return None


def no_evidence_answer(query):
    return {
        "query": query,
        "answer": "Not enough evidence was found in the processed data to answer this confidently.",
        "supporting_message_ids": [],
        "related_ids": [],
        "relevance_scores": [],
        "reason": "No message, task, or group met the minimum relevance threshold for this query."
    }


def answer_query(query, data):
    q_lower = query.lower()
    q_words = key_words(query, data["common_words"])

    # --- Intent: status of a specific item referenced by an explicit message ID ---
    id_match = re.search(MSG_ID_PATTERN, query)
    if id_match and ("status" in q_lower or "latest" in q_lower):
        target_id = id_match.group(1)

        group = find_group_for_message(target_id, data["groups"])
        if group:
            return {
                "query": query,
                "answer": f"The latest status of this item is '{group['status']}'.",
                "supporting_message_ids": group["related_message_ids"],
                "related_ids": [group["group_id"]],
                "relevance_scores": [group["confidence"]],
                "reason": f"Message {target_id} belongs to group '{group['title']}', whose latest known status is '{group['status']}'."
            }

        priority_entry = next((p for p in data["priorities"] if p["message_id"] == target_id), None)
        if priority_entry:
            return {
                "query": query,
                "answer": f"No related-message group was found, but this item has priority '{priority_entry['priority']}'. {priority_entry['reason']}",
                "supporting_message_ids": [target_id],
                "related_ids": [priority_entry["item_id"]],
                "relevance_scores": [priority_entry["confidence"]],
                "reason": "Retrieved directly from the priority report since no multi-message group contains this ID."
            }

        # Fallback: the message exists but wasn't tracked as a task/group member directly.
        # Find the closest matching group using the message's own text.
        target_text = data["messages"].get(target_id)
        if target_text:
            target_words = key_words(target_text, data["common_words"])
            scored = []
            for g in data["groups"]:
                gtext = g["title"] + " " + g["summary"]
                gwords = key_words(gtext, data["common_words"])
                if target_words:
                    overlap = target_words & gwords
                    score = len(overlap) / len(target_words)
                    if score >= 0.2:
                        scored.append((score, g))
            if scored:
                scored.sort(key=lambda x: -x[0])
                score, best = scored[0]
                return {
                    "query": query,
                    "answer": (
                        f"No direct record was found for {target_id}, but its content closely matches "
                        f"group '{best['title']}', whose latest status is '{best['status']}'."
                    ),
                    "supporting_message_ids": best["related_message_ids"],
                    "related_ids": [best["group_id"]],
                    "relevance_scores": [round(score, 2)],
                    "reason": f"{target_id} was not classified as an actionable item or grouped directly, "
                              f"so the closest matching group was used based on shared keywords."
                }

        return no_evidence_answer(query)

    # --- Intent: messages that must be blocked from external processing ---
    if "blocked" in q_lower or "external" in q_lower or "do not send" in q_lower:
        restrict_actions = {"do_not_store", "do_not_send_external"}
        matches = [p for p in data["privacy"] if p["routing_decision"] in restrict_actions]
        if "demo" in q_lower:
            demo_matches = [m for m in matches if data["batch"].get(m["message_id"]) == "L2_DEMO"]
            if demo_matches:
                matches = demo_matches
        if not matches:
            return no_evidence_answer(query)
        return {
            "query": query,
            "answer": f"{len(matches)} message(s) must be blocked from external processing.",
            "supporting_message_ids": [m["message_id"] for m in matches],
            "related_ids": [],
            "relevance_scores": [1.0] * len(matches),
            "reason": "Filtered from privacy routing decisions marked 'do_not_store' or 'do_not_send_external'."
        }

    # --- Intent: conflicting/uncertain deadlines ---
    if "conflict" in q_lower or "uncertain" in q_lower:
        matches = []
        for g in data["groups"]:
            deadlines_in_group = set()
            for m in g["related_message_ids"]:
                text = data["messages"].get(m, "")
                dt = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
                if dt:
                    deadlines_in_group.add(dt.group(1))
            if len(deadlines_in_group) > 1:
                matches.append(g)
        if not matches:
            return no_evidence_answer(query)
        return {
            "query": query,
            "answer": f"{len(matches)} group(s) show more than one deadline mentioned across their messages, suggesting a conflict.",
            "supporting_message_ids": sum([m["related_message_ids"] for m in matches], []),
            "related_ids": [m["group_id"] for m in matches],
            "relevance_scores": [1.0] * len(matches),
            "reason": "Groups where multiple distinct dates were found across related messages."
        }

    # --- Intent: rescheduled meetings ---
    if "reschedul" in q_lower:
        matches = [g for g in data["groups"] if g["status"] == "rescheduled"]
        if not matches:
            return no_evidence_answer(query)
        return {
            "query": query,
            "answer": f"{len(matches)} group(s) marked as rescheduled. Latest deadline(s): "
                      f"{[m['latest_deadline'] for m in matches]}.",
            "supporting_message_ids": sum([m["related_message_ids"] for m in matches], []),
            "related_ids": [m["group_id"] for m in matches],
            "relevance_scores": [1.0] * len(matches),
            "reason": "Filtered directly from related-message groups with status 'rescheduled'."
        }

    # --- Intent: completed or cancelled tasks/meetings ---
    if "completed" in q_lower or "cancel" in q_lower or "done" in q_lower:
        matches = [g for g in data["groups"] if g["status"] in ("completed", "cancelled")]
        if not matches:
            return no_evidence_answer(query)
        return {
            "query": query,
            "answer": f"{len(matches)} group(s) marked as completed or cancelled.",
            "supporting_message_ids": sum([m["related_message_ids"] for m in matches], []),
            "related_ids": [m["group_id"] for m in matches],
            "relevance_scores": [1.0] * len(matches),
            "reason": "Filtered directly from related-message groups with status 'completed' or 'cancelled'."
        }

    # --- Intent: critical/high priority items (including "became critical") ---
    if "critical" in q_lower or "high priority" in q_lower or "priority" in q_lower:
        base = [p for p in data["priorities"] if p["priority"] in ("critical", "high")]

        became = [p for p in base if p["updated_by_message_id"]]
        in_demo = [
            p for p in base
            if data["batch"].get(p["message_id"]) == "L2_DEMO"
            or (p["updated_by_message_id"] and data["batch"].get(p["updated_by_message_id"]) == "L2_DEMO")
        ]

        wants_became = "became" in q_lower or "updated" in q_lower
        wants_demo = "demo" in q_lower

        if wants_became and wants_demo:
            final = [p for p in became if p in in_demo] or became or in_demo
        elif wants_became:
            final = became
        elif wants_demo:
            final = in_demo
        else:
            final = base

        if not final:
            return no_evidence_answer(query)
        return {
            "query": query,
            "answer": f"{len(final)} critical/high priority item(s) found.",
            "supporting_message_ids": [m["message_id"] for m in final],
            "related_ids": [m["item_id"] for m in final],
            "relevance_scores": [1.0] * len(final),
            "reason": "Filtered from the priority report for critical/high priority items, "
                      "narrowed by 'became/updated' and/or 'demo data' if mentioned in the query."
        }

    # --- Intent: confirmation required ---
    if "confirmation" in q_lower or "confirm" in q_lower:
        matches = [p for p in data["priorities"] if "response_required" in p["signals"]]
        if not matches:
            return no_evidence_answer(query)
        return {
            "query": query,
            "answer": f"{len(matches)} message(s) appear to require confirmation/response.",
            "supporting_message_ids": [m["message_id"] for m in matches],
            "related_ids": [m["item_id"] for m in matches],
            "relevance_scores": [1.0] * len(matches),
            "reason": "Filtered from priority signals containing 'response_required'."
        }

    # --- Generic fallback: keyword relevance search across groups, then messages ---
    scored_groups = []
    for g in data["groups"]:
        text = g["title"] + " " + g["summary"]
        score = relevance(q_words, text, data["common_words"])
        if score >= MIN_RELEVANCE:
            scored_groups.append((score, g))

    if scored_groups:
        scored_groups.sort(key=lambda x: -x[0])
        best_score, best_group = scored_groups[0]
        return {
            "query": query,
            "answer": f"Found related group '{best_group['title']}' with status '{best_group['status']}'.",
            "supporting_message_ids": best_group["related_message_ids"],
            "related_ids": [best_group["group_id"]],
            "relevance_scores": [round(best_score, 2)],
            "reason": "Matched based on shared keywords between the query and this group's title/summary."
        }

    scored_msgs = []
    for msg_id, text in data["messages"].items():
        score = relevance(q_words, text, data["common_words"])
        if score >= MIN_RELEVANCE:
            scored_msgs.append((score, msg_id))

    if scored_msgs:
        scored_msgs.sort(key=lambda x: -x[0])
        top_msgs = scored_msgs[:3]
        return {
            "query": query,
            "answer": "Found related message(s), see supporting IDs.",
            "supporting_message_ids": [m[1] for m in top_msgs],
            "related_ids": [],
            "relevance_scores": [round(m[0], 2) for m in top_msgs],
            "reason": "Matched based on keyword overlap between the query and individual messages."
        }

    return no_evidence_answer(query)


if __name__ == "__main__":
    data = load_all_data()
    test_queries = [
        "Which critical or high priority tasks are still pending?",
        "What meetings were rescheduled?",
        "Which tasks have been completed?",
        "Which messages require confirmation?",
    ]
    results = [answer_query(q, data) for q in test_queries]
    with open("output/assistant_test_answers.json", "w") as f:
        json.dump(results, f, indent=2)
    for r in results:
        print(f"\nQ: {r['query']}\nA: {r['answer']}")