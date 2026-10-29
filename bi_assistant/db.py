"""Step 1 - Load the CSV into SQLite, validate rows, flag bad ones (never silently drop)."""
import csv, os, sqlite3
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, "data", "sales.csv")
DB_PATH = os.path.join(BASE, "data", "sales.db")

SCHEMA = """CREATE TABLE sales(
  transaction_id TEXT PRIMARY KEY, order_date TEXT, month TEXT, product TEXT, category TEXT,
  region TEXT, sales_channel TEXT, quantity INTEGER, unit_price REAL, discount_amount REAL,
  status TEXT, is_valid INTEGER NOT NULL, issue TEXT)"""
# Revenue only counts rows that are valid AND Completed (returned orders are excluded).
VIEW = """CREATE VIEW valid_sales AS
  SELECT *, quantity*unit_price - discount_amount AS revenue
  FROM sales WHERE is_valid=1 AND status='Completed'"""


def _num(v):
    try:
        return float(v) if v.strip() != "" else None
    except ValueError:
        return None


def clean_row(r):
    """Return (db_row_tuple, issue_text). issue_text is '' when the row is valid."""
    issues = []
    try:
        dt = datetime.strptime(r["Order_date"].strip(), "%d-%m-%Y")
        date, month = dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m")
    except ValueError:
        date = month = None
        issues.append("invalid order date")
    qty, price, disc = _num(r["Quantity"]), _num(r["Unit_price"]), _num(r["Discount_amount"])
    if qty is None or qty <= 0:
        issues.append("quantity missing or <= 0")
    if price is None or price <= 0:
        issues.append("unit price missing or <= 0")
    if disc is None:
        disc = 0.0
    issue = "; ".join(issues)
    return (r["Transaction_Id"].strip(), date, month, r["Product"].strip(), r["Category"].strip(),
            r["Region"].strip(), r["Sales_channel"].strip(), int(qty) if qty is not None else None,
            price, disc, r["Status"].strip(), 0 if issue else 1, issue), issue


def load(csv_path=CSV_PATH, db_path=DB_PATH):
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    con.execute(SCHEMA)
    con.execute(VIEW)
    with open(csv_path, newline="") as f:
        for r in csv.DictReader(f):
            row, _ = clean_row(r)
            con.execute("INSERT OR REPLACE INTO sales VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
    con.commit()
    con.close()


def connect_readonly(db_path=DB_PATH):
    """Every query runs on a read-only connection, so writes are impossible at DB level."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    return con


def data_quality(con):
    cur = con.execute("SELECT transaction_id, issue FROM sales WHERE is_valid=0")
    bad = [{"transaction_id": a, "issue": b} for a, b in cur]
    ret = [a for (a,) in con.execute("SELECT transaction_id FROM sales WHERE is_valid=1 AND status!='Completed'")]
    total = con.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    return {"total_rows": total, "invalid_rows": bad, "excluded_non_completed": ret}
