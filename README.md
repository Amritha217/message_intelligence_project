# Message Intelligence System (L1 + L2)

A rule-based system that processes messages to classify them, extract tasks/events, detect sensitive information, assign priority, group related messages, and answer natural-language questions — all using explainable, local logic (no external AI API touches the data).

## Project Structure

```
message-intelligence-system/
├── data/                        # input CSVs (not pushed to repo)
├── src/
│   ├── load_data.py             # L1: loads & sorts L1 messages
│   ├── load_l2_data.py          # L2: loads L2 data, merges L1+L2 chronologically
│   ├── classify.py              # L1 Part 1: classification
│   ├── extract_tasks.py         # L1 Part 2: task/event extraction
│   ├── detect_sensitive.py      # L1 Part 3: sensitive info detection & masking
│   ├── priority_engine.py       # L2 Part 1: priority and action engine
│   ├── group_messages.py        # L2 Part 2: related-message grouping
│   ├── privacy_routing.py       # L2: privacy-aware routing
│   ├── assistant.py             # L2 Part 3: semantic search & Q&A assistant
│   ├── run_demo_queries.py      # runs mandatory L2 demo queries
│   ├── benchmark.py             # benchmark comparison for grouping threshold
│   └── main.py                  # runs the full L1 + L2 pipeline
├── output/                      # all generated JSON output files
├── app.py                       # Flask app for cloud-hosted demo
├── Procfile                     # deployment config for Render
├── requirements.txt
└── README.md
```

## How to Run

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

All outputs are generated in `output/`. To run the web demo locally:
```bash
python app.py
```

---

# L1 System (recap)

## Part 1: Classification
Rule-based keyword/regex matching into 6 categories (checked in priority order — Sensitive Information first — so a message like "reminder: your OTP is 4821" is never left unprotected): Action Required, Meeting or Event, Personal Information, Promotional, Sensitive Information, General Information (fallback). Confidence scales with number of keyword hits.

## Part 2: Task/Event Extraction
For `action_required`/`meeting_or_event` messages: title (cleaned of generic preambles like "For today:"), description, deadline (regex `YYYY-MM-DD`/`DD-MM-YYYY` only), time (`HH:MM` regex), person (explicit "with/for `<Name>`" patterns only), priority. **No field is guessed** — unclear fields are `null`.

## Part 3: Sensitive Information Detection
Regex rules per type (OTP, password, PIN, CVV, card/account number, API token, phone, address) → risk level + recommended action. Only the matched value is masked (`***`), not the whole message.

---

# L2 System — How It Extends L1

L2 does not replace or rebuild L1 — it **reuses L1's functions directly as building blocks**:
- `load_l2_data.py` imports `load_messages()` from L1's `load_data.py` and merges it with the new L2 CSVs into one chronologically sorted stream (`load_combined_messages()`), which every L2 module then processes.
- `priority_engine.py` reuses L1's `classify_message()` and `extract_date()` and `detect_sensitive()` to build on top of the same classification/extraction/sensitivity logic instead of re-implementing it.
- `group_messages.py` reuses `priority_engine.py`'s output (`build_priorities()`) to link groups to task/event IDs.
- `assistant.py` reads from **every** L1 and L2 output (classifications, tasks/events via priorities, sensitive results, priority results, groups) — it does not re-derive anything from scratch.
- The combined dataset processes **L1 → L2 → L2-demo messages, strictly in chronological (timestamp) order**, as required.

## Part 1: How Priority Is Calculated and Updated

Each actionable message (`action_required` / `meeting_or_event`) is scored using multiple signals, not one keyword:

| Signal | Points |
|---|---|
| Deadline overdue / today | +4 |
| Deadline within 2 days | +2 |
| Urgent keyword (urgent, asap, immediately, critical, important) | +3 |
| Message is sensitive | +2 |
| Response appears required ("can you", "please confirm", "?") | +1 |
| Overdue phrasing ("still pending", "haven't received") | +3 |
| Marked done ("completed", "submitted", "cancelled") | −3 |

Total score → priority band: `critical` ≥7, `high` ≥4, `medium` ≥2, else `low`. Confidence scales with number of signals found.

**Updating priority from later messages:** every new message is checked for shared "key words" (significant words, with globally common/generic words filtered out — see below) against existing tracked items. If a message shares 3+ such words with an earlier item **and** contains escalation/de-escalation language, that earlier item's score, priority, and reason are updated in place, and `updated_by_message_id` records which message triggered the change. This is how a task can go from `medium` to `critical` after a later urgent follow-up, or drop in priority once marked done.

## Part 2: How Related Messages Are Identified

Messages are linked into the same group when they share **3 or more significant words** (after stopword removal and after removing "globally common" words — words that appear in more than 2% of all messages, e.g. "form", "review", "please submit" — since generic/templated phrasing repeats hundreds of times across this dataset and would otherwise falsely merge unrelated messages). This word-overlap threshold was tuned via benchmarking (see below) specifically because the raw threshold of 2 produced a single 500+ message "mega-group."

Each group tracks: `group_id`, `title` (from its first message), `related_message_ids`, `related_task_or_event_ids` (cross-referenced from the priority report), `status`, `latest_deadline`, `summary`, `confidence`.

**Status detection** scans all messages in a group for keyword signals, checked in this priority order: cancelled → rescheduled → completed → in_progress → pending → unclear (default when no clear signal is found — chosen deliberately rather than guessing).

**Chronology**: groups are built by walking messages in timestamp order, so a group's "latest deadline" and "current status" always reflect the most recently mentioned information, consistent with how a human reading the messages in order would understand the current state.

## Part 3: How Semantic Retrieval Works

The assistant does **not** call an external LLM. It combines:
1. **Intent rules** — the query is checked against a fixed set of patterns (critical/high priority, rescheduled, completed/cancelled, confirmation-required, conflicting deadlines, status-of-a-specific-message-ID, blocked-from-external) and, when matched, pulls the answer directly from the corresponding structured output file (priority report, groups, privacy routing).
2. **Keyword-overlap fallback** — if no intent matches, the query's significant words are compared against every group's title/summary, then every individual message, using the same word-overlap scoring used for grouping. The highest-scoring match above a minimum relevance threshold (0.3) is returned.
3. **No unsupported answers** — if nothing clears the threshold, the assistant explicitly returns "Not enough evidence was found," rather than fabricating an answer, per the assignment rule.

Every answer includes: final answer, supporting message IDs, related task/event/group IDs, relevance scores, and a short reason explaining why that evidence was selected.

## How Privacy-Aware Routing Works

Every message (L1 + L2 + L2-demo) is passed through the same sensitive-detection logic from L1 (`detect_sensitive.py`). Each message gets a routing decision:
- No sensitive pattern → `safe_to_process_locally`
- Sensitive pattern detected → the type's specific recommended action (`do_not_store`, `do_not_send_external`, or `ask_for_confirmation`), consistent with the risk level assigned in L1.

This routing table (`privacy_routing.json`) is also consulted by the assistant — e.g. queries like "which messages must be blocked from external processing" are answered directly from this file, and raw sensitive values are never surfaced through search results (the assistant only ever returns message IDs and masked text, never raw values).

## What Component Was Optimized, and How Benchmarking Was Performed

**Component optimized:** the related-message grouping's word-overlap threshold (`MIN_SHARED_WORDS`), since this directly determines both grouping accuracy and priority-update accuracy (the same threshold is reused for follow-up detection in `priority_engine.py`).

**Benchmark method** (`src/benchmark.py`): the grouping logic was run three times against the full combined dataset with thresholds of 2, 3, and 4 shared significant words, measuring: number of groups formed, average group size, largest group size, and execution time. Results:

| Threshold | Groups (2+ msgs) | Avg. group size | Largest group | Time |
|---|---|---|---|---|
| 2 | 18 | 59.5 | 905 (!) | 0.042s |
| 3 | 75 | ~10 | 16 | 0.043s |
| 4 | 104 | 7.4 | 44 | 0.062s |

Threshold 2 clearly over-merges (one group swallowed nearly the entire dataset). Threshold 3 was selected as the best balance — realistic group sizes, sensible status distribution (rescheduled/completed/in-progress groups all present), and negligible extra runtime cost versus threshold 2. This is documented as the "before vs. after" comparison for the video demo.

## Assumptions & Limitations

- All classification, extraction, priority, grouping, and retrieval logic is keyword/regex-based, not semantic/embedding-based — chosen for full explainability as required by the assignment, at the cost of missing unusually-phrased messages.
- Date extraction only recognizes explicit `YYYY-MM-DD`/`DD-MM-YYYY` patterns; relative dates ("tomorrow") are never resolved, to avoid inventing information.
- The "common word" filter (words appearing in >2% of messages are excluded from matching) is a simple frequency-based heuristic, not true semantic similarity — it substantially reduced false grouping but may still occasionally over- or under-merge on borderline cases.
- Conflicting-deadline detection (`"conflict"` queries) is a simple heuristic: it flags any group where more than one distinct date appears across its messages. It does not attempt to determine which date is "correct" — it surfaces the group and lets the reader judge.
- The assistant's generic fallback (used when no specific intent matches, e.g. free-form factual questions) is keyword-overlap based and may occasionally return a topically related but not perfectly precise answer, or honestly report insufficient evidence — this is a known trade-off documented and demonstrated in the video.
- This system processes a fixed batch of CSV files; it is not a real-time message monitor.

## AI-Tool Usage Declaration

- Claude (Anthropic) was used as a coding assistant throughout, to help design the rule-based logic (classification rules, priority scoring, grouping thresholds), write and iteratively debug the Python scripts, and structure this documentation.
- No message content — from L1 or L2 datasets — was sent to any external AI/LLM service during actual data processing. All classification, extraction, priority, grouping, and retrieval logic runs locally using Python's `re` module and `pandas` only.
- All logic in this repository is understood and can be explained by the author.

## Links

- Video demonstration (Loom): `<ADD_LINK>`
- Cloud-hosted demo: `https://message-intelligence-system-mrfl.onrender.com/`
