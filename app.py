from flask import Flask, jsonify, render_template_string
import json

app = Flask(__name__)

def load_json(path):
    with open(path) as f:
        return json.load(f)

PAGE = """
<h1>Message Intelligence System</h1>
<ul>
  <li><a href="/classification">Classification results (Part 1)</a></li>
  <li><a href="/tasks_events">Tasks & Events (Part 2)</a></li>
  <li><a href="/sensitive_report">Sensitive Info Report - masked (Part 3)</a></li>
  <li><a href="/mandatory_demo">Mandatory Demo IDs Report</a></li>
</ul>
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

if __name__ == "__main__":
    app.run(debug=True)