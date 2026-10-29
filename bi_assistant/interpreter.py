"""Step 3 - Turn a question into {intent, months}. LLM (optional) first, rule-based fallback.
Either way the output is validated against a whitelist before anything touches the database."""
import json, os, re, urllib.request

INTENT_NAMES = ["total_revenue", "top_product", "top_region", "monthly_trend", "month_compare"]
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
YEAR = 2026  # dataset covers 2026 only
MONTH_RE = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", re.I)


def find_months(q):
    return [f"{YEAR}-{MONTHS[m.group(1).lower()]:02d}" for m in MONTH_RE.finditer(q)]


def rule_based(q):
    t, months = q.lower(), find_months(q)
    if len(months) >= 2 and re.search(r"compar|chang|between|vs|versus|differ|grow", t):
        return "month_compare", months[:2]
    if re.search(r"trend|monthly|month[- ]by[- ]month|per month|each month", t):
        return "monthly_trend", []
    if "region" in t:
        return "top_region", []
    if "product" in t or "item" in t:
        return "top_product", []
    if re.search(r"\b(total|overall|revenue)\b", t):
        return "total_revenue", []
    return None, []


SYSTEM = ("You classify questions about a sales dataset (2026 data). Reply with ONLY JSON: "
          '{"intent": one of ' + json.dumps(INTENT_NAMES) + ', "months": ["YYYY-MM", ...]} . '
          "months only for month_compare (exactly 2, in the order mentioned). "
          'If the question is not answerable with these intents reply {"intent": null, "months": []}.')


def llm_interpret(q):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = json.dumps({"model": "claude-sonnet-4-6", "max_tokens": 200, "system": SYSTEM,
                       "messages": [{"role": "user", "content": q}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", body,
                                 {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            text = json.load(r)["content"][0]["text"]
        d = json.loads(text[text.index("{"): text.rindex("}") + 1])
        months = d.get("months") or []
        if d.get("intent") not in INTENT_NAMES + [None]:
            return None
        if not all(isinstance(m, str) and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", m) for m in months):
            return None
        if d["intent"] == "month_compare" and len(months) != 2:
            return None
        return d["intent"], months
    except Exception:
        return None  # any LLM problem -> fall back to rules


def interpret(q):
    """Returns (intent, months, source)."""
    res = llm_interpret(q)
    if res is not None:
        return res[0], res[1], "llm"
    intent, months = rule_based(q)
    return intent, months, "rules"
