"""Simple Flask application."""
from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/items")
def list_items():
    return jsonify({"items": []})


if __name__ == "__main__":
    app.run(debug=True)
