"""Step 4 - Flask API + serves the UI.  Run: python main.py  ->  http://localhost:5000"""
import os
from flask import Flask, jsonify, request, send_from_directory
import analytics, db, interpreter

MAX_LEN = 300
EXAMPLES = ["What is the total revenue?", "Which product generated the highest revenue?",
            "What is the monthly revenue trend?", "Which region generated the highest sales?",
            "How did revenue change between January and February?"]


def create_app(db_path=db.DB_PATH):
    app = Flask(__name__, static_folder="static")
    if not os.path.exists(db_path):
        db.load(db.CSV_PATH, db_path)

    @app.get("/")
    def index():
        return send_from_directory("static", "index.html")

    @app.get("/api/examples")
    def examples():
        return jsonify(EXAMPLES)

    @app.get("/api/data-quality")
    def quality():
        con = db.connect_readonly(db_path)
        try:
            return jsonify(db.data_quality(con))
        finally:
            con.close()

    @app.post("/api/ask")
    def ask():
        body = request.get_json(silent=True) or {}
        q = body.get("question")
        if not isinstance(q, str) or not q.strip():
            return jsonify(error="Please provide a non-empty 'question' string."), 400
        if len(q) > MAX_LEN:
            return jsonify(error=f"Question too long (max {MAX_LEN} characters)."), 400
        intent, months, source = interpreter.interpret(q)
        if intent is None:
            return jsonify(error="Sorry, I can't answer that from this dataset.", supported_examples=EXAMPLES), 422
        con = db.connect_readonly(db_path)
        try:
            fn = analytics.INTENTS[intent]  # whitelist lookup - unknown intent can never run
            result = fn(con, *months) if intent == "month_compare" else fn(con)
        except Exception as e:  # noqa
            return jsonify(error=f"Query failed: {e}"), 500
        finally:
            con.close()
        return jsonify(question=q, intent=intent, interpreted_by=source, **result)

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
