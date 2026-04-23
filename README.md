# 🤖 GitHub RAG Chatbot

A Streamlit chatbot that lets you **talk to any GitHub repository** using RAG (Retrieval-Augmented Generation) powered by Claude.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
streamlit run app.py
```

### 3. Configure in the sidebar
- Paste your **Anthropic API Key** (get one at [console.anthropic.com](https://console.anthropic.com))
- Optionally add a **GitHub Token** (needed for private repos or to avoid rate limits)
- Paste a **GitHub repo URL**, e.g. `https://github.com/anthropics/anthropic-sdk-python`
- Choose file types to index and click **Load & Index Repo**

### 4. Chat!
Ask anything about the codebase — functions, architecture, how things work, etc.

---

## 🏗️ Architecture

```
app.py              ← Streamlit UI
github_loader.py    ← Fetches files from GitHub API
rag_engine.py       ← Chunks docs, TF-IDF retrieval, Claude API call
requirements.txt    ← Dependencies
```

### How RAG works here:
1. **Load** – GitHub API fetches all matching files from the repo
2. **Chunk** – Files are split into overlapping 800-char chunks
3. **Index** – TF-IDF vectors are built for fast retrieval (no vector DB needed!)
4. **Query** – Your question is matched against chunks via cosine similarity
5. **Generate** – Top-k chunks + question are sent to Claude for an accurate answer

---

## 💡 Example questions
- "How does authentication work in this project?"
- "What does the main.py do?"
- "Explain the folder structure"
- "What dependencies does this project use?"
- "How are errors handled?"

---

## 🔑 API Keys

| Key | Required | Where to get |
|-----|----------|--------------|
| Anthropic API Key | ✅ Yes | [console.anthropic.com](https://console.anthropic.com) |
| GitHub Token | ⚡ Optional | [github.com/settings/tokens](https://github.com/settings/tokens) |

> **Tip:** GitHub token lets you index private repos and avoids the 60 req/hour unauthenticated rate limit.
