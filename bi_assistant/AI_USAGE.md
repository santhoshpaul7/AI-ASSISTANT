# AI Usage Notes  (EDIT this with your own experience before submitting!)

**Tools used:** Claude (chat) to scaffold the project.

**How AI was used:** Read the challenge brief, proposed the architecture (LLM = classifier, SQL = fixed
templates), generated the code and tests.

**Problems met & debugging**
- Shell brace-expansion did not create folders -> some files were missing; recreated them.
- Test `test_unsupported_question` failed: "best salesperson" matched the word "sales" and returned
  total revenue. Fixed by matching whole words (`\b(total|overall|revenue)\b`).
- Data issues found by inspecting the CSV: quantity 0, missing unit price, one Returned order.

**With another day:** add filters (region/product/channel), safe text-to-SQL with a SQL parser
validator, conversation memory, charts, Dockerfile, and RAG over a data dictionary.

**Interview prep:** be able to explain every file, why the LLM never writes SQL, and Agentic AI / RAG basics.
