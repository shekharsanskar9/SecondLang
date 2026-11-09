# SecondLang

Refine your English for two situations, **Formal** (teachers, office, HR) and **Family** (parents, siblings, relatives).
Type a phrase, pick a tone, and SecondLang will:

- rewrite it in correct, natural English for that tone
- show **what changed** word by word (red = removed, green = added)
- list each **correction with a short explanation** so you learn from it
- give you a **tip** based on your biggest mistake
- save a **history** and chart your **most common mistake types**

Mixed Hindi/Hinglish words are translated into English (except words like Mummy, Papa, Bhaiya, Didi in Family mode).

## Project structure

```
secondlang/
├── app/
│   ├── main.py        # FastAPI app: /api routes + serves the web page
│   ├── config.py      # settings from .env
│   ├── prompts.py     # tone definitions + the prompt sent to the model
│   ├── providers.py   # Ollama / Anthropic / OpenAI / offline backends
│   ├── refiner.py     # calls the model, parses JSON, builds the word diff
│   ├── offline.py     # rule-based fallback (no AI needed)
│   ├── db.py          # SQLite history + mistake stats
│   ├── schemas.py     # request/response models
│   └── __main__.py    # `python -m app` starts the server
├── static/            # web interface (index.html, style.css, app.js)
├── tests/             # pytest tests
├── requirements.txt
└── .env.example
```

## Setup

```bash
cd secondlang
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit .env
```

### Choose an engine (`LLM_PROVIDER` in `.env`)

| Provider    | Cost | What you need |
|-------------|------|---------------|
| `ollama`    | Free, runs on your computer | Install [Ollama](https://ollama.com), then `ollama pull qwen2.5:7b` |
| `anthropic` | Paid API | `ANTHROPIC_API_KEY` |
| `openai`    | Paid API | `OPENAI_API_KEY` |
| `offline`   | Free, no AI | Nothing. Fixes only common mistakes (spelling, text-speak, apostrophes, capitals). Good for a first test |

## Run

```bash
python -m app
```

Open **http://127.0.0.1:8000**. Press **Ctrl + Enter** (⌘ + Enter on Mac) to refine.

API docs (Swagger) are at **http://127.0.0.1:8000/docs**.

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/refine` | `{"text": "...", "tone": "formal" \| "family", "context": "optional", "save": true}` |
| `GET` | `/api/history?limit=50` | Past refinements, newest first |
| `DELETE` | `/api/history/{id}` | Delete one item |
| `DELETE` | `/api/history` | Clear history |
| `GET` | `/api/stats` | Count of mistakes by type |
| `GET` | `/api/tones` | Available tones |
| `GET` | `/api/health` | Active provider and model |

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/refine \
  -H "Content-Type: application/json" \
  -d '{"text": "sir i want leave tmrw coz my cousin marriage", "tone": "formal"}'
```

## Tests

```bash
pytest -q
```

## Adding a new tone

Add an entry to `TONES` in `app/prompts.py` (for example `"friends"` or `"customer"`) and a button in
`static/index.html` with the same `data-tone` value. Nothing else needs to change.
