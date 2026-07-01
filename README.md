# 🔌 API Doc Agent

<div align="center">

**An AI Chrome extension that reads any API documentation page and instantly generates ready-to-run code, Postman payloads, and plain-English explanations.**

![API Doc Agent](https://img.shields.io/badge/API_Doc_Agent-AI_Powered-blue?style=for-the-badge&logo=google-gemini)
![Chrome Extension](https://img.shields.io/badge/Chrome_Extension-Manifest_V3-green?style=flat-square&logo=google-chrome)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)
![LangGraph](https://img.shields.io/badge/Agent-LangGraph-FF4F00?style=flat-square)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)

</div>

---

## 📖 Overview

Reading API documentation and translating it into working code is repetitive, error-prone busywork — every developer does it, every day, for every new integration.

**API Doc Agent** removes that friction. Open any API docs page — Stripe, Twilio, OpenAI, GitHub, or your own internal API — click the extension icon, and a multi-agent LLM pipeline reads the page, understands the endpoint, and hands you back:

- A working code snippet in your language of choice
- A Postman-ready JSON payload
- A plain-English explanation of what the endpoint actually does
- Root-cause analysis if you paste in an error message

No copy-pasting docs into ChatGPT. No manually re-typing parameters. It's a side panel that lives in your browser and understands whatever page you're looking at.

---

## ✨ Features

| Feature | Description |
|---|---|
| ⚡ **Instant Analysis** | One click extracts and analyzes the API doc page you're viewing — no setup per page. |
| 💻 **Ready-to-Run Code** | Generates accurate, runnable snippets in Python, JavaScript, or cURL. |
| 📦 **Postman-Ready Payloads** | Outputs a correctly formatted JSON payload you can paste straight into Postman. |
| 📖 **Plain-English Explanations** | Breaks down parameters and responses into clear, 2–4 sentence summaries. |
| 🐛 **Smart Error Tracing** | Paste an error message and the agent traces it back to the docs to explain the fix. |
| 💬 **Follow-Up Chat** | Ask the agent follow-up questions about the endpoint, right in the side panel. |
| 💾 **Persistent Caching** | Analyses and chat history are cached in PostgreSQL, so revisiting a page is instant. |

---

## 🏗️ Architecture

The project has two halves that talk to each other over a REST API:

```
┌─────────────────────────┐         ┌──────────────────────────┐
│   Chrome Extension       │  HTTP   │   FastAPI Backend         │
│   (Manifest V3)          │ ──────► │   + LangGraph Pipeline    │
│                           │         │                            │
│  • Side Panel UI          │         │  • classify_doc_node       │
│  • Content script         │         │  • extract_endpoint_node   │
│    extracts page text     │         │  • generate_outputs_node   │
│  • Service worker routes  │         │  • error_trace_node        │
│    messages               │         │                            │
└─────────────────────────┘         └────────────┬─────────────┘
                                                    │
                                          ┌─────────▼─────────┐
                                          │   PostgreSQL (Neon) │
                                          │  sessions/messages   │
                                          └─────────────────────┘
```

### Chrome Extension (`/extension`)
- **Manifest V3** with the **Side Panel API** for a persistent, cross-tab UI
- **Service worker** (`background.js`) orchestrates messaging between the page, UI, and backend
- **Content script** (`extractor.js`) pulls the readable text out of whatever API doc page is open

### Python Backend (`/backend`)
- **FastAPI** — async REST API
- **LangGraph** — orchestrates a 4-node agent pipeline (classify → extract → generate → trace)
- **Gemini API** (`gemini-2.5-flash-lite`) — fast structured extraction, bring-your-own-key (BYOK)
- **PostgreSQL (Neon)** — persists sessions, parsed endpoints, and chat history

---

## 🛠️ Tech Stack

`Python` · `FastAPI` · `LangGraph` · `LangChain` · `Google Gemini` · `PostgreSQL` · `asyncpg` · `Chrome Extensions (Manifest V3)` · `JavaScript` · `Docker` · `Railway`

---

## 🚀 Getting Started

### Prerequisites
- [Google Chrome](https://www.google.com/chrome/)
- [Python 3.9+](https://www.python.org/downloads/)
- A [Neon PostgreSQL](https://neon.tech/) database (or any standard Postgres instance)
- A [Gemini API key](https://aistudio.google.com/)

### Backend Setup

```bash
cd api-doc-agent/backend

# Create a virtual environment and install dependencies
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# then edit .env and set your DATABASE_URL
```

Initialize the database schema:

```bash
python -c "
import asyncio, asyncpg, os
from dotenv import load_dotenv
async def main():
    load_dotenv()
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    with open('schema.sql', 'r', encoding='utf-8') as f:
        await conn.execute(f.read())
    await conn.close()
asyncio.run(main())
"
```

Start the server:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Chrome Extension Setup

1. Open `chrome://extensions/` and enable **Developer mode**
2. Click **Load unpacked** and select the `api-doc-agent/extension` folder
3. Right-click the extension icon → **Options**
4. Paste your **Gemini API key**, set your preferred language, and click **Save**

---

## 🎯 How to Use

1. Open any API documentation page (e.g. [Stripe's Create Charge docs](https://docs.stripe.com/api/charges/create))
2. Click the **API Doc Agent** icon in your toolbar
3. The side panel opens and analysis runs automatically
4. Review the generated code snippet, Postman payload, and explanation
5. Got an error? Paste it into **Trace an Error**
6. Have more questions? Ask the agent directly in **Follow-up Chat**

---

## 🧠 LangGraph Pipeline

Each analysis request runs through a sequential graph:

1. **`classify_doc_node`** — identifies the doc type (REST, GraphQL, webhook, etc.)
2. **`extract_endpoint_node`** — extracts method, URL, auth, parameters, and error codes into structured JSON
3. **`generate_outputs_node`** — produces the language-specific code snippet, Postman payload, and explanation
4. **`error_trace_node`** *(conditional)* — if an error string is supplied, traces it against the parsed doc context

---

## 🗺️ Roadmap

- [ ] Support additional languages (Go, Ruby, Java)
- [ ] One-click "Send to Postman" via the Postman API
- [ ] Firefox / Edge extension builds
- [ ] Multi-page doc context (linked pages, shared auth sections)

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes
4. Open a pull request

---

## 📝 License

Licensed under the [MIT License](LICENSE).
