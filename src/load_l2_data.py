import pandas as pd
from load_data import load_messages  

L2_MESSAGES_PATH = "data/l2_messages.csv"
L2_DEMO_MESSAGES_PATH = "data/l2_demo_messages.csv"
L2_DEMO_QUERIES_PATH = "data/l2_demo_queries.csv"


def _load_l2_csv(path):
    df = pd.read_csv(path)

    required_cols = {"message_id", "timestamp", "sender", "message"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def load_l2_messages():
    return _load_l2_csv(L2_MESSAGES_PATH)


def load_l2_demo_messages():
    return _load_l2_csv(L2_DEMO_MESSAGES_PATH)


def load_l2_demo_queries():
    df = pd.read_csv(L2_DEMO_QUERIES_PATH)
    required_cols = {"query_id", "query"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {L2_DEMO_QUERIES_PATH}: {missing}")
    return df


def load_combined_messages():
    l1 = load_messages().copy()
    l1["batch"] = "L1"

    l2 = load_l2_messages().copy()
    l2["batch"] = "L2"

    l2_demo = load_l2_demo_messages().copy()
    l2_demo["batch"] = "L2_DEMO"

    combined = pd.concat([l1, l2, l2_demo], ignore_index=True)
    combined = combined.sort_values("timestamp").reset_index(drop=True)
    return combined


if __name__ == "__main__":
    combined = load_combined_messages()
    queries = load_l2_demo_queries()

    print(f"Combined dataset: {len(combined)} messages")
    print(combined["batch"].value_counts())

    print(f"\nLoaded {len(queries)} mandatory demo queries")
    print(queries.head())

    is_sorted = combined["timestamp"].is_monotonic_increasing
    print(f"\nChronological order preserved: {is_sorted}")

    print("\nFirst 3 combined messages:")
    print(combined[["message_id", "timestamp", "batch"]].head(3))

    print("\nLast 3 combined messages:")
    print(combined[["message_id", "timestamp", "batch"]].tail(3))