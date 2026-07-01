# 🔌 API Doc Agent

![API Doc Agent Banner](https://img.shields.io/badge/API_Doc_Agent-AI_Powered-blue?style=for-the-badge&logo=google-gemini)
![Chrome Extension](https://img.shields.io/badge/Chrome_Extension-Manifest_V3-green?style=flat-square&logo=google-chrome)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)
![LangGraph](https://img.shields.io/badge/Agent-LangGraph-FF4F00?style=flat-square)

**API Doc Agent** is an intelligent Chrome Extension that acts as your personal API integration assistant. Open any API documentation page (Stripe, Twilio, OpenAI, GitHub, etc.), click the extension icon, and instantly get tailored code snippets, Postman payloads, and plain English explanations directly in your browser's side panel.

---

## ✨ Features

- **⚡ Instant Analysis**: Click the extension icon to automatically extract and analyze the API documentation you are viewing.
- **💻 Ready-to-Run Code**: Generates accurate, runnable code snippets in your preferred language (Python, JavaScript, or cURL).
- **📦 Postman-Ready Payloads**: Provides a perfectly formatted JSON payload that you can paste directly into Postman.
- **📖 Plain English Explanations**: Breaks down complex API parameters and responses into simple, 2-4 sentence summaries.
- **🐛 Smart Error Tracing**: Paste an error message into the panel, and the agent will trace it back to the documentation, explaining exactly what went wrong and how to fix it.
- **💬 Follow-up Chat**: Have an interactive conversation with the agent in the side panel to ask further questions about the endpoint.
- **💾 Intelligent Caching**: Analysis results and chat history are cached persistently via a PostgreSQL backend, meaning returning to a docs page is lightning fast.

---

## 🏗️ Architecture

The project is split into two main components: a **Manifest V3 Chrome Extension** and a **FastAPI + LangGraph Backend**.

### 1. Chrome Extension (`/extension`)
- **Manifest V3**: Modern extension architecture.
- **Side Panel API**: Provides a persistent UI (`sidepanel.html`) that stays open across tabs.
- **Service Worker (`background.js`)**: Orchestrates messaging between the UI and the backend.
- **Content Scripts (`extractor.js`)**: Extracts the main readable text from the active API documentation page.

### 2. Python Backend (`/backend`)
- **FastAPI**: High-performance async REST API.
- **LangGraph**: Orchestrates the multi-agent LLM workflow (Classification ➔ Extraction ➔ Generation ➔ Error Tracing).
- **Gemini API**: Powered by Google's `gemini-2.5-flash-lite` (or standard flash) for fast, structured data extraction.
- **PostgreSQL (Neon)**: Persists session data, endpoints, and chat histories to ensure instantaneous reloads.

---

## 🚀 Getting Started

### Prerequisites
- [Google Chrome](https://www.google.com/chrome/)
- [Python 3.9+](https://www.python.org/downloads/)
- [Neon PostgreSQL Database](https://neon.tech/) (or any standard Postgres instance)
- [Gemini API Key](https://aistudio.google.com/)

### Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd api-doc-agent/backend
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the `backend/` directory:
   ```env
   DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
   ```

4. **Initialize the Database:**
   Run the schema setup script to create the necessary tables (`sessions` and `messages`):
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

5. **Start the FastAPI Server:**
   ```bash
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

### Chrome Extension Setup

1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable **Developer mode** using the toggle in the top right corner.
3. Click **Load unpacked** and select the `api-doc-agent/extension` folder.
4. Once loaded, right-click the API Doc Agent icon in your toolbar and select **Options**.
5. Paste your **Gemini API Key** and set your preferred programming language, then click **Save**.

---

## 🎯 How to Use

1. Navigate to any API documentation page (e.g., [Stripe Create Charge](https://docs.stripe.com/api/charges/create)).
2. Click the **API Doc Agent icon** in your browser toolbar.
3. The Chrome side panel will open instantly and trigger the analysis.
4. Review the generated Code Snippet, Postman Payload, and Plain English summary.
5. Have an error? Paste it into the **Trace an Error** box at the bottom of the panel.
6. Want to know more? Chat with the agent directly in the **Follow-up Chat** section.

---

## 🛠️ LangGraph Pipeline Workflow

When an analysis is requested, the backend runs a sequential graph:
1. **`classify_doc_node`**: Identifies if the page is a REST endpoint, GraphQL, Webhook, etc.
2. **`extract_endpoint_node`**: Extracts the method, URL, auth type, parameters, and error codes into a structured JSON schema.
3. **`generate_outputs_node`**: Generates the final language-specific code snippet, Postman payload, and plain English explanation.
4. **`error_trace_node`** *(Conditional)*: If an error string is provided, traces it against the parsed documentation context.

---

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
