# Mini AI Business Intelligence Assistant

Ask sales questions in plain English; get an answer **plus the SQL and figures behind it**.

## Run it (4 steps)
```bash
python -m pip install -r requirements.txt
python main.py                 # open http://localhost:5000
python -m pytest -q            # run the tests
export ANTHROPIC_API_KEY=...   # OPTIONAL: enables LLM question interpretation
```
Without an API key the app uses a rule-based interpreter, so it works fully offline.

## Architecture
```
Browser UI (static/index.html)
   |  POST /api/ask {question}
Flask API (main.py)  -- validates input (empty / too long -> 400, unsupported -> 422)
   |
interpreter.py  -- LLM (optional) or rules  ->  {intent, months}   [whitelist-validated]
   |
analytics.py    -- fixed, parameterised SQL template per intent
   |
SQLite (read-only connection)  <-- db.py loads + cleans data/sales.csv
```
**Key idea:** the LLM only *classifies* the question into one of 5 intents. It never writes SQL, so
destructive or wrong queries are impossible by design. Unknown intent -> refusal, not a guess.

## Data handling
- `sales` table keeps every CSV row; bad rows get `is_valid=0` + an `issue` note (nothing silently lost).
- Invalid: quantity <= 0 (TXN0034), missing unit price (TXN0051), bad date.
- `valid_sales` view = valid rows with status `Completed` (excludes Returned TXN0033) and
  `revenue = quantity * unit_price - discount_amount`.
- Dates are `dd-mm-yyyy` in the CSV; stored as ISO plus a `YYYY-MM` month column.
- `GET /api/data-quality` lists excluded rows.

## Preventing wrong / unsupported answers
1. LLM output must match the intent whitelist and `YYYY-MM` format, otherwise it is ignored (falls back to rules).
2. Only parameterised SQL templates run; user text never enters SQL.
3. DB connection is read-only (`mode=ro`, `query_only`) - writes fail even if code were wrong.
4. Every answer shows its SQL and supporting rows so the user can verify it.

## Supported questions
Total revenue - top product - monthly trend - top region - compare two months (all 5).

## Known limitations
- Only 5 fixed question types; no free-form text-to-SQL, no filters like "in the North region".
- Year assumed to be 2026. Currency not specified in the data, so none is shown.
- Rule-based parser is keyword matching; odd phrasings may be refused.
- Returned orders are fully excluded (no partial-return logic).
