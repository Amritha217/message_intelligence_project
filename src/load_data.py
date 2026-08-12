import pandas as pd

MESSAGES_PATH = "data/messages.csv"
MANDATORY_IDS_PATH = "data/mandatory_demo_ids.csv"


def load_messages():
    df = pd.read_csv(MESSAGES_PATH)

     # Basic column check
    required_cols = {"message_id", "timestamp", "sender", "message"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in messages.csv: {missing}")
    
    # Parse timestamp (format: 01-09-2026 08:00:00 -> DD-MM-YYYY HH:MM:SS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%d-%m-%Y %H:%M")

    # Sort chronologically 
    df = df.sort_values("timestamp").reset_index(drop=True)

    return df



def load_mandatory_ids():
    df = pd.read_csv(MANDATORY_IDS_PATH)
    if "message_id" not in df.columns:
        raise ValueError("mandatory_demo_ids.csv must have a 'message_id' column")
    return df["message_id"].tolist()



if __name__ == "__main__":
    messages = load_messages()
    mandatory_ids = load_mandatory_ids()

    print(f"Loaded {len(messages)} messages.")
    print(f"Loaded {len(mandatory_ids)} mandatory demo IDs.")
    print("\nFirst 3 messages (chronological order):")
    print(messages[["message_id", "timestamp", "sender"]].head(3))

    missing_mandatory = set(mandatory_ids) - set(messages["message_id"])
    if missing_mandatory:
        print(f"\nWARNING: These mandatory IDs are not in messages.csv: {missing_mandatory}")
    else:
        print("\nAll mandatory demo IDs found in messages.csv ")






    


