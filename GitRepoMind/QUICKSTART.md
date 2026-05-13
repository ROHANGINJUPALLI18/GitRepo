# RAG Chat Layer - Quick Start Guide

## 5-Minute Setup

### Prerequisites
- Python 3.8+
- Ollama installed ([download](https://ollama.ai))
- Docker (for database services) - optional but recommended

### Step 1: Install the Model (2 minutes)

```bash
# Start Ollama daemon
ollama serve &

# In another terminal, pull the model
ollama pull qwen2.5-coder:7b

# Verify it's loaded
ollama list
```

### Step 2: Install Dependencies (2 minutes)

```bash
cd server
pip install -r requirements.txt
```

### Step 3: Start the Server (1 minute)

```bash
python -m uvicorn src.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Test the Chat Endpoint

Open a new terminal:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What endpoints are available in this API?"
  }'
```

You should get a response like:
```json
{
  "success": true,
  "query": "What endpoints are available in this API?",
  "answer": "Based on the provided repository context...",
  "sources": ["src/api/search.py", "src/api/chat.py"],
  "chunks_used": 2,
  "chunks_metadata": [...]
}
```

### Step 5: Interactive Testing

Visit http://localhost:8000/docs to use the interactive Swagger UI.

---

## Common Commands

### Run Tests
```bash
cd /path/to/GitRepoMind
pytest tests/test_chat_service.py -v
```

### Check Ollama Status
```bash
# Is Ollama running?
curl http://localhost:11434/api/tags

# Is the model loaded?
ollama list
```

### View Logs
```bash
# With debug logging
python -m uvicorn src.main:app --reload --log-level debug
```

### Reset Everything
```bash
# Stop Ollama
pkill ollama

# Clear Ollama cache
rm -rf ~/.ollama/models

# Reinstall model
ollama pull qwen2.5-coder:7b
```

---

## File Structure

```
server/
├── src/
│   ├── api/
│   │   ├── chat.py                 # NEW: Chat API endpoint
│   │   └── search.py               # Semantic search endpoint
│   ├── services/
│   │   ├── llm_service.py          # NEW: Ollama LLM integration
│   │   ├── prompt_service.py       # NEW: RAG prompt building
│   │   ├── chat_service.py         # NEW: RAG orchestration
│   │   ├── search_service.py       # Semantic search
│   │   ├── embedding_service.py    # Text embeddings
│   │   └── ...
│   ├── app.py                      # UPDATED: Added chat router
│   └── config.py                   # UPDATED: Added Ollama config
├── requirements.txt                # UPDATED: Added ollama package
└── ...

tests/
└── test_chat_service.py            # NEW: Comprehensive tests

.env.example                        # UPDATED: Full config template
RAG_CHAT_IMPLEMENTATION.md          # NEW: Detailed documentation
```

---

## Key Configuration Options

All configurable via environment variables in `.env`:

```env
# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_TEMPERATURE=0.2

# RAG
RAG_TOP_K=5
RAG_MAX_CONTEXT_CHARS=12000
```

---

## API Overview

### POST /api/chat
Chat with RAG-powered repository assistant

**Request:**
```json
{
  "query": "How does authentication work?",
  "top_k": 5,
  "repo_filter": null
}
```

**Response:**
```json
{
  "success": true,
  "query": "...",
  "answer": "...",
  "sources": ["src/auth/login.py", ...],
  "chunks_used": 2,
  "chunks_metadata": [...]
}
```

### GET /api/chat/health
Check RAG component health

**Response:**
```json
{
  "search_service": "healthy",
  "llm_service": true,
  "prompt_service": "healthy"
}
```

---

## Example Queries

```bash
# Architecture questions
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the overall architecture?"}'

# Specific code questions  
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How does JWT validation work?"}'

# File location queries
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Where is the authentication logic?"}'
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Connection refused: 11434` | Make sure `ollama serve` is running |
| `Model not found: qwen2.5-coder:7b` | Run `ollama pull qwen2.5-coder:7b` |
| `Slow responses (>30s)` | Increase `OLLAMA_TIMEOUT` or reduce `RAG_TOP_K` |
| `Empty responses` | Check Ollama is loaded: `ollama list` |
| `Tests failing` | Run `pip install -r requirements.txt` again |

---

## What's New in This Update

✅ **New Services:**
- `LLMService` - Ollama integration
- `PromptService` - RAG prompt building
- `ChatService` - RAG orchestration

✅ **New API:**
- `POST /api/chat` - Chat endpoint
- `GET /api/chat/health` - Health check

✅ **Configuration:**
- Ollama settings in config.py
- RAG settings support
- Full .env.example template

✅ **Testing:**
- 50+ tests covering all components
- Mocked services for unit tests
- Integration tests
- API endpoint tests

✅ **Documentation:**
- RAG_CHAT_IMPLEMENTATION.md - Full guide
- This quick start guide
- Docstrings in all services

---

## Next Steps

1. **Test the basic flow:**
   ```bash
   # Terminal 1: Start Ollama
   ollama serve
   
   # Terminal 2: Start API
   python -m uvicorn src.main:app --reload
   
   # Terminal 3: Test chat
   curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"query": "test query"}'
   ```

2. **Explore the interactive API docs:**
   - Visit http://localhost:8000/docs
   - Try the `/api/chat` endpoint
   - Check `/api/chat/health`

3. **Run the tests:**
   ```bash
   pytest tests/test_chat_service.py -v
   ```

4. **Read the full documentation:**
   - Open `RAG_CHAT_IMPLEMENTATION.md`
   - Review service docstrings
   - Check example use cases

---

## Questions?

- Check `RAG_CHAT_IMPLEMENTATION.md` for detailed docs
- Review docstrings in service files
- Look at tests for usage examples
- Check logs for error messages

Happy coding! 🚀
