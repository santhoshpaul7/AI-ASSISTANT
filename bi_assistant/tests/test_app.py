import csv, os, sys, sqlite3, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db, interpreter
from main import create_app


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("d") / "t.db")
    db.load(db.CSV_PATH, path)
    return create_app(path).test_client(), path


def ask(c, q):
    return c.post("/api/ask", json={"question": q})


def expected_total():  # independent calculation straight from the CSV
    t = 0
    for r in csv.DictReader(open(db.CSV_PATH)):
        if r["Status"] == "Completed" and r["Quantity"] not in ("", "0") and r["Unit_price"]:
            t += int(r["Quantity"]) * float(r["Unit_price"]) - float(r["Discount_amount"])
    return t


# ---- valid questions ----
def test_total_revenue(client):
    d = ask(client[0], "What is the total revenue?").get_json()
    assert d["rows"][0][4] == expected_total()

def test_top_product(client):
    d = ask(client[0], "Which product generated the highest revenue?").get_json()
    assert d["intent"] == "top_product" and d["rows"][0][1] >= d["rows"][-1][1]

def test_monthly_trend(client):
    d = ask(client[0], "What is the monthly revenue trend?").get_json()
    assert [r[0] for r in d["rows"]] == [f"2026-0{i}" for i in range(1, 7)]

def test_top_region(client):
    d = ask(client[0], "Which region generated the highest sales?").get_json()
    assert d["intent"] == "top_region" and d["answer"].startswith(d["rows"][0][0])

def test_month_compare(client):
    d = ask(client[0], "How did revenue change between January and February?").get_json()
    assert d["intent"] == "month_compare" and d["params"] == ["2026-01", "2026-02"]

# ---- invalid questions / input ----
def test_empty_question(client):
    assert ask(client[0], "   ").status_code == 400

def test_missing_body(client):
    assert client[0].post("/api/ask", data="nope").status_code == 400

def test_unsupported_question(client):
    r = ask(client[0], "Who is the best salesperson?")
    assert r.status_code == 422 and "supported_examples" in r.get_json()

def test_sql_injection_text_is_harmless(client):
    r = ask(client[0], "total revenue; DROP TABLE sales;")
    assert r.status_code == 200
    assert ask(client[0], "total revenue").get_json()["rows"][0][4] == expected_total()

# ---- edge cases ----
def test_bad_rows_excluded(client):
    q = client[0].get("/api/data-quality").get_json()
    ids = [x["transaction_id"] for x in q["invalid_rows"]]
    assert set(ids) == {"TXN0034", "TXN0051"} and q["excluded_non_completed"] == ["TXN0033"]

def test_month_with_no_data(client):
    d = ask(client[0], "Compare revenue between January and December").get_json()
    assert "No valid sales data" in d["answer"]

def test_database_is_read_only(client):
    con = db.connect_readonly(client[1])
    with pytest.raises(sqlite3.OperationalError):
        con.execute("DELETE FROM sales")

def test_rule_parser_months():
    assert interpreter.rule_based("revenue change from March to April") == ("month_compare", ["2026-03", "2026-04"])
