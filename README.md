# SecondLang

**Refine your English for the person you're writing to.**
SecondLang rewrites your phrases in correct, natural English, either **Formal** (teachers, office, HR) or **Family** (parents, siblings, relatives), and explains every correction so you learn from your mistakes.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688)
![SQLite](https://img.shields.io/badge/SQLite-history-003B57)
![License](https://img.shields.io/badge/license-MIT-green)

> 🔗 **Live demo:** _coming soon_ <!-- TODO: add deployed URL -->

<!-- TODO: add a screenshot or GIF of the app, e.g. docs/demo.gif -->
<p align="center">
  <img src="docs/demo.gif" alt="SecondLang demo: typing a phrase, picking a tone, seeing the word diff" width="700">
</p>

---

## Why I built this

English is my second language. I write in two very different situations: formal messages (leave applications, emails to professors, HR) and casual messages to family, often mixing in Hindi. Grammar checkers fix spelling but miss **tone**, and they don't explain *why* something is wrong. SecondLang does both, and tracks which mistakes I make most so I can actually improve.

## Example

**Input** (Formal):
```
sir i want leave tmrw coz my cousin marriage
```

**Output:**
```
Dear Sir, I would like to request leave tomorrow, as I need to attend my cousin's wedding.
```

**Corrections:**
| Mistake | Fix | Why |
|---|---|---|
| `tmrw`, `coz` | `tomorrow`, `as` | Text-speak isn't suitable for formal writing |
| `i want leave` | `I would like to request leave` | "Want" sounds demanding; "would like to request" is polite |
| `cousin marriage` | `cousin's wedding` | Possessive needs `'s`; "wedding" is the event, "marriage" is the relationship |

## Features

- **Two tones:** Formal and Family, each with its own rules
- **Word-by-word diff:** red = removed, green = added
- **Explained corrections:** a short reason for every change
- **Personal tip:** based on your biggest mistake in that phrase
- **Hinglish support:** Hindi words are translated, except family words like *Mummy, Papa, Bhaiya, Didi* in Family mode
- **History and stats:** every refinement is saved locally, with a chart of your most common mistake types
- **Choose your engine:** a local model (Ollama), Anthropic, OpenAI, or an offline rule-based mode that needs no AI at all

## How it works

```mermaid
flowchart LR
    UI[Web UI<br/>static/] -->|POST /api/refine| API[FastAPI<br/>main.py]
    API --> R[Refiner<br/>refiner.py]
    R -->|tone prompt| P{Provider<br/>providers.py}
    P --> O[Ollama<br/>local]
    P --> A[Anthropic]
    P --> G[OpenAI]
    P --> F[Offline rules<br/>offline.py]
    R -->|JSON + word diff| API
    API --> DB[(SQLite<br/>history + stats)]
```

1. The UI sends your text and tone to `/api/refine`.
2. `prompts.py` builds a tone-specific prompt that asks for a structured JSON answer.
3. The selected provider returns the rewrite, corrections and tip.
4. `refiner.py` parses the JSON and computes the word-level diff.
5. The result is saved in SQLite, and the mistake types feed the stats chart.

## Tech stack

**Backend:** Python, FastAPI, Pydantic, SQLite
**Frontend:** HTML, CSS, vanilla JavaScript
**AI engines:** Ollama (Qwen 2.5 7B), Anthropic API, OpenAI API, rule-based fallback
**Testing:** pytest

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
├── docs/              # screenshots / demo GIF
├── requirements.txt
└── .env.example
```

## Getting started

### 1. Install

```bash
git clone https://github.com/shekharsanskar9/secondlang.git   # TODO: confirm repo name
cd secondlang
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit .env
```

### 2. Choose an engine (`LLM_PROVIDER` in `.env`)

| Provider    | Cost | What you need |
|-------------|------|---------------|
| `ollama`    | Free, runs on your computer | Install [Ollama](https://ollama.com), then `ollama pull qwen2.5:7b` |
| `anthropic` | Paid API | `ANTHROPIC_API_KEY` |
| `openai`    | Paid API | `OPENAI_API_KEY` |
| `offline`   | Free, no AI | Nothing. Fixes only common mistakes (spelling, text-speak, apostrophes, capitals). Good for a first test |

### 3. Run

```bash
python -m app
```

Open **http://127.0.0.1:8000** and press **Ctrl + Enter** (⌘ + Enter on Mac) to refine.
Interactive API docs (Swagger) are at **http://127.0.0.1:8000/docs**.

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/refine` | Refine a phrase: `{"text": "...", "tone": "formal" \| "family", "context": "optional", "save": true}` |
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

## Roadmap

- [ ] Deploy a public demo
- [ ] Evaluation set of real phrases to compare engines and catch prompt regressions
- [ ] Practice mode: quiz yourself on your past mistakes
- [ ] Progress chart: mistakes per 100 words over time
- [ ] Explanations in Hindi/Hinglish (toggle)
- [ ] More tones: Friends, Professor, Interview/HR email
- [ ] Templates: leave application, email to professor, interview follow-up
- [ ] Voice input (speech-to-text) and read-aloud (text-to-speech)
- [ ] Validate model JSON with Pydantic and retry once if it's malformed; stream responses
- [ ] Docker + GitHub Actions CI

## Privacy

History is stored only in a local SQLite file on your machine. With `ollama` or `offline`, your text never leaves your computer.

## Author

**Sanskar Shekhar**, B.Tech CSE, BIT Mesra
[GitHub](https://github.com/shekharsanskar9) · [LinkedIn](https://linkedin.com/in/sanskar-shekhar)

## License

MIT. See [LICENSE](LICENSE). <!-- TODO: add a LICENSE file -->
