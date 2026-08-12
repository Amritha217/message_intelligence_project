# Message Intelligence System

A rule-based system that processes 900 chronological messages to:
1. Classify each message into a category
2. Extract tasks and events with structured details
3. Detect and mask sensitive information

## Project Structure

```
message-intelligence-system/
├── data/                       # input CSVs (not pushed to repo)
│   ├── messages.csv
│   └── mandatory_demo_ids.csv
├── src/
│   ├── load_data.py            # loads & sorts messages chronologically
│   ├── classify.py             # Part 1: classification
│   ├── extract_tasks.py        # Part 2: task/event extraction
│   ├── detect_sensitive.py     # Part 3: sensitive info detection & masking
│   └── main.py                 # runs the full pipeline
├── output/
│   ├── classification.json
│   ├── tasks_events.json
│   ├── sensitive_report.json
│   └── mandatory_demo_report.json
├── requirements.txt
├── .gitignore
└── README.md
```

## How to Run

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

Outputs are generated in the `output/` folder:
- `classification.json` — Part 1 results for all messages
- `tasks_events.json` — Part 2 results
- `sensitive_report.json` — Part 3 results (masked only)
- `mandatory_demo_report.json` — combined view of the 15 mandatory demo message IDs

## Part 1: How Message Classification Works

Classification is fully **rule-based** using keyword and regex pattern matching — no external AI API is called, so all logic is transparent and explainable.

Each message is checked against categories in a fixed **priority order**, and the first strong match wins:

1. **Sensitive Information** — regex patterns for OTP, password, PIN, CVV, account/card numbers, tokens
2. **Action Required** — phrases like "please submit", "reminder", "deadline", "don't forget"
3. **Meeting or Event** — phrases like "meeting", "calendar", "scheduled", "event"
4. **Personal Information** — phrases like "my address", "family", "my number"
5. **Promotional** — phrases like "offer", "discount", "% off", "subscribe"
6. **General Information** — fallback when no other category matches

**Confidence score** is computed from the number of keyword hits (base score + increment per hit, capped at 0.95). The fallback category (General Information) is fixed at 0.5 since it reflects absence of signal, not certainty.

**Why sensitive info is checked first:** to ensure a message like "reminder: your OTP is 4821" is never mis-tagged as merely "action required" and left unprotected.

## Part 2: How Task/Event Extraction Works

Applies only to messages classified as `action_required` (→ type: `task`) or `meeting_or_event` (→ type: `event`).

- **Title**: derived from the message by stripping generic preambles (e.g. "For today:", "Reminder:") and filler phrases (e.g. "Don't forget to"), then taking the first clause, capped at 8 words.
- **Description**: the full original message text.
- **Deadline**: extracted via regex for `YYYY-MM-DD` or `DD-MM-YYYY` patterns only. No fuzzy/relative date parsing (e.g. "next week") is used, to avoid inventing dates.
- **Time**: extracted via regex for `HH:MM` patterns.
- **Person**: extracted only from explicit patterns like "with `<Name>`" / "for `<Name>`". If not explicitly named, left `null`.
- **Priority**: `high` if urgency words present (urgent, asap, immediately, important, must), `medium` if a date is present, otherwise `low`.

**No missing field is guessed** — if a date, time, or person is not explicitly stated in the message text, it is stored as `null`, per assignment rules.

## Part 3: How Sensitive Information Is Detected & Masked

Detection uses regex rules per sensitivity type:

| Type | Risk | Recommended Action |
|---|---|---|
| One-time password (OTP) | high | do_not_store |
| Password | high | do_not_store |
| PIN | high | do_not_store |
| CVV | high | do_not_store |
| API key / token | high | do_not_store |
| Card / account number | high | do_not_send_external |
| Private phone number | medium | ask_for_confirmation |
| Private address | medium | ask_for_confirmation |

**Masking**: only the detected sensitive *value* is replaced with `***` (not the whole message), so context remains readable while the actual value is destroyed. Masking happens immediately at detection time — the raw value is never written to any output file, log, or the mandatory demo report.

**Video/screenshot safety**: only masked output files (e.g. `sensitive_report.json`, `mandatory_demo_report.json`) are shown in the demo video and any screenshots — raw `messages.csv` content for sensitive rows is never displayed or recorded.

## Assumptions & Limitations

- Classification and extraction are keyword/regex-based, not semantic — messages using unusual phrasing may be misclassified. This is a deliberate trade-off in favor of full explainability, as required by the assignment.
- Date extraction only recognizes `YYYY-MM-DD` and `DD-MM-YYYY` formats; relative dates ("tomorrow", "next Friday") are not resolved, to avoid guessing.
- Person extraction only recognizes explicit "with/for `<Name>`" patterns; implied people (e.g. via context or sender field) are not inferred.
- The `card_or_account_number` sensitive-info rule (9–19 digit sequences) may produce false positives on other long numbers (e.g. order IDs); manually reviewed during testing and tightened where needed.
- This system processes a fixed CSV dataset in batch; it is not a real-time message monitor.
- Categories and rules were kept simple and rule-based per assignment instructions ("traditional/lightweight methods, custom logic" allowed) rather than using a trained ML model.

## AI-Tool Usage Declaration

- Claude (Anthropic) was used as a coding assistant to help design the rule-based logic, write and review Python scripts, and structure this documentation.
- No message content was sent to any external AI/LLM service during actual data processing — all classification, extraction, and detection logic runs locally using Python's built-in `re` module and `pandas`, per assignment rules.
- All logic in this repository is understood and can be explained by the author.

## Links

- GitHub repository: `<ADD_LINK>`
- Video demonstration (Loom): `<ADD_LINK>`
- Cloud-hosted demo: `https://message-intelligence-system-mrfl.onrender.com/`
