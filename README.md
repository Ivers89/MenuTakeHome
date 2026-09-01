# Menu Buddy
 
Upload a photo of a restaurant menu, then chat with it. Tracks the cost of every OpenAI call along the way.
 
## Running it
 
```bash
python -m venv venv
source venv/Scripts/activate 
pip install -r requirements.txt
export OPENAI_API_KEY=sk-your-key-here
uvicorn main:app --reload
```

Open http://localhost:8000.

- **strict: True on the schema** — guarantees shape of output (every field present, correct types, no extras) at generation time. However, it does not guarante content accuracy see more in testing notes. I chose to trust strict mode for shape and skip a separate Pydantic validation pass on top of it because strict mode already enforces the menu schema.
- **Everything in memory** — *menus_db* and *analytics_db* are plain dicts/lists, no database to follow the task requirements. Restarting the server clears all state.
- **Error handling on /menus** — three separate failure modes are checked after the OpenAI call: empty *output_text* (502), output that isn't valid JSON (502), and valid JSON with an empty menu_items list (422 The model succeeding at the task but finding no menu items).


## Testing notes
 
Tested against the provided sample menu plus a few of my own phone photos, including some at extreme angles. A few observations:
 
- Extreme-angle or blurry photos occasionally misread numbers — a lemonade priced at $4.50 came back as $4.30 in one test.
- Tags aren't always reliable at the margins — a "vegetarian" item was tagged "vegan" in one run.
- I believe this is partly a `gpt-4o-mini` trade-off: it's fast and cheap, but not as strong at OCR reading as larger/pricier models. Strict mode guarantees the *shape* of the output is always correct — it doesn't guarantee the *values* inside that shape are accurate reads of the image.

## What I'd do next

Compare gpt-4o-mini against a stronger model on a batch of angled/blurry test photos to see whether accuracy improves enough to justify the added cost.
Implement SQLite database on disk or try cloud database so menus will persist each time the page is refreshed.
Cost alerts that keeps track of total cost in a chat session if it exceeds a set threshold then block or warn users in session.