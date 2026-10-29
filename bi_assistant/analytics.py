"""Step 2 - Deterministic analytics. Fixed, parameterised SQL templates: the LLM never writes SQL."""

def _run(con, sql, params=()):
    cur = con.execute(sql, params)
    return [d[0] for d in cur.description], [list(r) for r in cur.fetchall()]

def _fmt(n):
    return f"{n:,.2f}".rstrip("0").rstrip(".")

def total_revenue(con):
    sql = ("SELECT COUNT(*) AS orders, SUM(quantity) AS units, SUM(quantity*unit_price) AS gross_sales, "
           "SUM(discount_amount) AS discounts, SUM(revenue) AS net_revenue FROM valid_sales")
    cols, rows = _run(con, sql)
    return dict(answer=f"Total revenue is {_fmt(rows[0][4])} (gross {_fmt(rows[0][2])} minus discounts {_fmt(rows[0][3])}, across {rows[0][0]} completed orders).",
                sql=sql, columns=cols, rows=rows)

def _top(con, col, label):
    sql = f"SELECT {col}, SUM(revenue) AS revenue, SUM(quantity) AS units FROM valid_sales GROUP BY {col} ORDER BY revenue DESC"
    cols, rows = _run(con, sql)
    return dict(answer=f"{rows[0][0]} generated the highest revenue by {label}: {_fmt(rows[0][1])}.",
                sql=sql, columns=cols, rows=rows)

def top_product(con): return _top(con, "product", "product")
def top_region(con): return _top(con, "region", "region")

def monthly_trend(con):
    sql = "SELECT month, SUM(revenue) AS revenue FROM valid_sales GROUP BY month ORDER BY month"
    cols, rows = _run(con, sql)
    prev = None
    for r in rows:
        r.append(None if prev is None else round((r[1] - prev) / prev * 100, 1))
        prev = r[1]
    cols.append("change_vs_prev_month_%")
    best = max(rows, key=lambda r: r[1])
    return dict(answer=f"Monthly revenue over {len(rows)} months. Peak month: {best[0]} ({_fmt(best[1])}).",
                sql=sql, columns=cols, rows=rows)

def month_compare(con, a, b):
    sql = "SELECT month, SUM(revenue) AS revenue FROM valid_sales WHERE month IN (?, ?) GROUP BY month ORDER BY month"
    cols, rows = _run(con, sql, (a, b))
    got = {r[0]: r[1] for r in rows}
    missing = [m for m in (a, b) if m not in got]
    if missing:
        return dict(answer=f"No valid sales data for: {', '.join(missing)}. Cannot compare.", sql=sql, params=[a, b], columns=cols, rows=rows)
    diff = got[b] - got[a]
    pct = diff / got[a] * 100
    word = "increased" if diff > 0 else "decreased" if diff < 0 else "did not change"
    return dict(answer=f"Revenue {word} from {_fmt(got[a])} in {a} to {_fmt(got[b])} in {b} ({diff:+,.0f}, {pct:+.1f}%).",
                sql=sql, params=[a, b], columns=cols, rows=rows)

INTENTS = {"total_revenue": total_revenue, "top_product": top_product, "top_region": top_region,
           "monthly_trend": monthly_trend, "month_compare": month_compare}
