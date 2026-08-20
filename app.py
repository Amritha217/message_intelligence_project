from flask import Flask, jsonify, render_template_string, request
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from assistant import load_all_data, answer_query

app = Flask(__name__)

_data_cache = None


def get_data():
    global _data_cache
    if _data_cache is None:
        _data_cache = load_all_data()
    return _data_cache


def load_json(path):
    with open(path) as f:
        return json.load(f)


PAGE = """
<h1>Message Intelligence System</h1>
<h3>L1</h3>
<ul>
  <li><a href="/classification">Classification results (Part 1)</a></li>
  <li><a href="/tasks_events">Tasks & Events (Part 2)</a></li>
  <li><a href="/sensitive_report">Sensitive Info Report - masked (Part 3)</a></li>
  <li><a href="/mandatory_demo">L1 Mandatory Demo IDs Report</a></li>
</ul>
<h3>L2</h3>
<ul>
  <li><a href="/priority_report">Priority Report</a></li>
  <li><a href="/related_groups">Related-Message Groups</a></li>
  <li><a href="/privacy_routing">Privacy Routing Report</a></li>
  <li><a href="/mandatory_query_answers">Mandatory Demo Query Answers</a></li>
  <li><a href="/benchmark_report">Benchmark Report</a></li>
</ul>
<h3>Ask the Assistant</h3>
<form action="/ask" method="get">
  <input type="text" name="q" style="width:400px" placeholder="Ask a question...">
  <input type="submit" value="Ask">
</form>
"""


@app.route("/")
def home():
    return render_template_string(PAGE)


@app.route("/classification")
def classification():
    return jsonify(load_json("output/classification.json"))


@app.route("/tasks_events")
def tasks_events():
    return jsonify(load_json("output/tasks_events.json"))


@app.route("/sensitive_report")
def sensitive_report():
    return jsonify(load_json("output/sensitive_report.json"))


@app.route("/mandatory_demo")
def mandatory_demo():
    return jsonify(load_json("output/mandatory_demo_report.json"))


@app.route("/priority_report")
def priority_report():
    return jsonify(load_json("output/priority_report.json"))


@app.route("/related_groups")
def related_groups():
    return jsonify(load_json("output/related_groups.json"))


@app.route("/privacy_routing")
def privacy_routing():
    return jsonify(load_json("output/privacy_routing.json"))


@app.route("/mandatory_query_answers")
def mandatory_query_answers():
    return jsonify(load_json("output/mandatory_query_answers.json"))


@app.route("/benchmark_report")
def benchmark_report():
    return jsonify(load_json("output/benchmark_report.json"))


@app.route("/ask")
def ask():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "Provide a question using ?q=your question"})
    data = get_data()
    answer = answer_query(query, data)
    return jsonify(answer)


if __name__ == "__main__":
    app.run(debug=True)