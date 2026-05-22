from flask import Flask, jsonify, render_template, request

from database.db import initialize_database
from services.productivity import (
    add_rule,
    delete_rule,
    get_task_summary,
    get_today_tasks,
    get_settings,
    get_state,
    get_monthly_analytics,
    get_weekly_analytics,
    handle_heartbeat,
    list_rules,
    replace_rules,
    update_today_task,
    update_settings,
)


app = Flask(__name__)


@app.after_request
def add_extension_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    return response


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/heartbeat", methods=["POST", "OPTIONS"])
def heartbeat():
    if request.method == "OPTIONS":
        return "", 204
    return jsonify(handle_heartbeat(request.get_json(silent=True) or {}))


@app.route("/api/state")
def state():
    return jsonify(get_state())


@app.route("/api/analytics/weekly")
def weekly_analytics():
    return jsonify(get_weekly_analytics())


@app.route("/api/analytics/monthly")
def monthly_analytics():
    return jsonify(get_monthly_analytics())


@app.route("/api/tasks/today", methods=["GET", "POST", "OPTIONS"])
def today_tasks():
    if request.method == "OPTIONS":
        return "", 204
    if request.method == "GET":
        return jsonify(get_today_tasks())
    return jsonify(update_today_task(request.get_json(silent=True) or {}))


@app.route("/api/tasks/summary")
def task_summary():
    return jsonify(get_task_summary())


@app.route("/api/rules", methods=["GET", "POST", "DELETE", "OPTIONS"])
def rules():
    if request.method == "OPTIONS":
        return "", 204
    if request.method == "GET":
        return jsonify(list_rules())

    payload = request.get_json(silent=True) or {}
    if request.method == "DELETE":
        return jsonify(delete_rule(payload.get("domain", "")))

    if "domain" in payload:
        return jsonify(add_rule(payload.get("domain", ""), payload.get("category", "")))
    return jsonify(replace_rules(payload))


@app.route("/api/settings", methods=["GET", "POST", "OPTIONS"])
def settings():
    if request.method == "OPTIONS":
        return "", 204
    if request.method == "GET":
        return jsonify(get_settings())
    return jsonify(update_settings(request.get_json(silent=True) or {}))


def main():
    initialize_database()
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
