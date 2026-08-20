import json
from load_l2_data import load_combined_messages
from detect_sensitive import detect_sensitive


def route_message(text):
    result = detect_sensitive(text)
    if result is None:
        return "safe_to_process_locally", None, None

    sens_type, risk, masked_text, action = result
    return action, sens_type, risk


def build_privacy_routing():
    df = load_combined_messages()
    routing = []

    for _, row in df.iterrows():
        text, msg_id = row["message"], row["message_id"]
        action, sens_type, risk = route_message(text)

        routing.append({
            "message_id": msg_id,
            "sensitivity_type": sens_type,
            "risk": risk,
            "routing_decision": action,
            "reason": (
                f"Message matched sensitive pattern '{sens_type}', routed as '{action}'."
                if sens_type else
                "No sensitive pattern detected; safe to process locally."
            )
        })

    return routing


if __name__ == "__main__":
    routing = build_privacy_routing()
    with open("output/privacy_routing.json", "w") as f:
        json.dump(routing, f, indent=2)
    print(f"Generated {len(routing)} routing decisions -> output/privacy_routing.json")

    from collections import Counter
    print(Counter(r["routing_decision"] for r in routing))