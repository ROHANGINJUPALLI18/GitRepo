# RAG Chat Layer - Implementation Guide

## Overview

The RAG (Retrieval-Augmented Generation) chat layer transforms GitRepoMind from a semantic search tool into a conversational AI repository assistant. It combines code retrieval with local LLM inference to provide intelligent, context-aware answers about your codebase.

## Architecture

```
User Query
    ↓
SearchService (retrieves relevant code chunks from vector DB)
    ↓
Relevant Code Chunks
    ↓
PromptService (builds structured RAG prompt with context)
    ↓
LLMService (sends prompt to Ollama → qwen2.5-coder:7b)
    ↓
ChatService (orchestrates the full pipeline)
    ↓
FastAPI /api/chat endpoint
    ↓
AI-generated answer with source citations
```

## Components

### 1. **LLMService** (`server/src/services/llm_service.py`)

Handles communication with Ollama and local LLM inference.

**Key Features:**
- Connects to local Ollama instance
- Uses `qwen2.5-coder:7b` model by default
- Configurable temperature, top_p, timeout
- Health checks for Ollama availability
- Error handling for connection/generation failures

**Example Usage:**
```python
from src.services.llm_service import LLMService

llm = LLMService()
response = llm.generate_response(prompt)
is_healthy = llm.health_check()
```

### 2. **PromptService** (`server/src/services/prompt_service.py`)

Builds high-quality RAG prompts to reduce hallucinations and improve accuracy.

**Key Features:**
- Combines user query with retrieved code chunks
- Includes metadata (file paths, line numbers, language)
- Enforces instruction following (answer only from context)
- Handles empty retrieval gracefully
- Truncates oversized contexts safely

**Prompt Template:**
```
You are an expert AI repository assistant.

Your role is to answer technical questions about the codebase ONLY using 
the provided repository context.

User Question:
{query}

Repository Context:
File: src/auth/login.py
Lines: 10-45
<code>

Instructions:
- Answer ONLY using the provided context
- Be accurate and technical
- Mention source files when relevant
- If context is insufficient, explicitly say so
- Do not hallucinate information

Answer:
```

**Example Usage:**
```python
from src.services.prompt_service import PromptService

prompt_service = PromptService()
prompt = prompt_service.build_rag_prompt(
    query="How does authentication work?",
    chunks=[...]
)
```

### 3. **ChatService** (`server/src/services/chat_service.py`)

Main orchestration layer that coordinates retrieval, prompt generation, and LLM response.

**Key Features:**
- Retrieves relevant code chunks
- Builds RAG prompt with context
- Calls LLM for generation
- Extracts and deduplicates citations
- Returns structured response

**Response Format:**
```json
{
  "success": true,
  "query": "How does authentication work?",
  "answer": "Authentication is handled using JWT tokens...",
  "sources": [
    "src/auth/login.py",
    "src/middleware/jwt.py"
  ],
  "chunks_used": 2,
  "chunks_metadata": [
    {
      "file_path": "src/auth/login.py",
      "start_line": 10,
      "end_line": 45,
      "language": "python",
      "score": 0.95
    }
  ]
}
```

**Example Usage:**
```python
from src.services.chat_service import ChatService

chat = ChatService()
response = chat.chat(
    query="How does authentication work?",
    top_k=5,
    repo_filter=None
)
```

### 4. **Chat API Endpoint** (`server/src/api/chat.py`)

FastAPI endpoint for the chat interface.

**Endpoint:** `POST /api/chat`

**Request:**
```json
{
  "query": "How does JWT authentication work?",
  "top_k": 5,
  "repo_filter": "optional-repo-name"
}
```

**Response:**
```json
{
  "success": true,
  "query": "How does JWT authentication work?",
  "answer": "JWT tokens are created in the authenticate function...",
  "sources": ["src/auth/login.py", "src/middleware/jwt.py"],
  "chunks_used": 2,
  "chunks_metadata": [...]
}
```

**Health Check:** `GET /api/chat/health`

## Setup & Configuration

### 1. Install Dependencies

```bash
cd server
pip install -r requirements.txt
```

### 2. Setup Ollama

**Install Ollama:**
- Download from [ollama.ai](https://ollama.ai)
- Follow installation instructions for your OS

**Download Model:**
```bash
ollama pull qwen2.5-coder:7b
```

**Start Ollama Server:**
```bash
ollama serve
```

This starts Ollama on `http://localhost:11434` by default.

### 3. Configure Environment Variables

Create `.env` file in the project root (or copy from `.env.example`):

```env
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_TEMPERATURE=0.2
OLLAMA_TOP_P=0.9
OLLAMA_TIMEOUT=60

# RAG Configuration
RAG_TOP_K=5
RAG_MAX_CONTEXT_CHARS=12000

# Other services (PostgreSQL, Qdrant, Redis, etc.)
DATABASE_URL=postgresql://postgres:password@localhost:5432/gitrepomind
QUADRANT_URL=http://localhost:6333
CELERY_BROKER_URL=redis://localhost:6379/0
```

### 4. Start the Backend

```bash
cd server
python -m uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`

## Usage Examples

### Using cURL

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does the JWT authentication system work?",
    "top_k": 5
  }'
```

### Using Python Requests

```python
import requests

response = requests.post(
    "http://localhost:8000/api/chat",
    json={
        "query": "How does authentication work?",
        "top_k": 5,
        "repo_filter": "my-repo"
    }
)

data = response.json()
print(data["answer"])
print(f"Sources: {', '.join(data['sources'])}")
```

### Using FastAPI Interactive Docs

1. Start the server
2. Visit `http://localhost:8000/docs`
3. Find the `POST /api/chat` endpoint
4. Click "Try it out"
5. Enter your query and parameters
6. Click "Execute"

## Configuration Details

### Ollama Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | LLM model name |
| `OLLAMA_TEMPERATURE` | `0.2` | Sampling temperature (0-1) |
| `OLLAMA_TOP_P` | `0.9` | Top-p nucleus sampling |
| `OLLAMA_TIMEOUT` | `60` | Request timeout (seconds) |

### RAG Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `RAG_TOP_K` | `5` | Default chunks to retrieve |
| `RAG_MAX_CONTEXT_CHARS` | `12000` | Max context length for prompt |

## Logging

The RAG services provide detailed logging for debugging and monitoring.

**Log Levels:**
- `INFO` - Normal operation (queries, retrievals, responses)
- `WARNING` - Potential issues (empty retrievals, truncations)
- `ERROR` - Failures (Ollama unavailable, generation errors)

**Enable Debug Logging:**
```python
# In your .env
LOG_LEVEL=DEBUG
```

**View Logs:**
```bash
# When running with uvicorn
python -m uvicorn src.main:app --log-level debug
```

## Testing

Run the comprehensive test suite:

```bash
cd /path/to/GitRepoMind
pytest tests/test_chat_service.py -v
```

**Test Coverage:**
- PromptService (formatting, truncation, empty contexts)
- LLMService (generation, health checks, error handling)
- ChatService (orchestration, citations, error handling)
- API endpoints (validation, responses, integration)
- Integration tests (full pipeline with mocks)

**Run with Coverage:**
```bash
pytest tests/test_chat_service.py --cov=src.services --cov=src.api
```

## Troubleshooting

### Ollama Connection Failed

**Error:** `Failed to connect to Ollama at http://localhost:11434`

**Solution:**
1. Ensure Ollama is installed and running
2. Check Ollama is accessible at `http://localhost:11434`
3. Verify in your terminal: `curl http://localhost:11434/api/tags`

### Model Not Found

**Error:** `Model qwen2.5-coder:7b not found`

**Solution:**
```bash
ollama pull qwen2.5-coder:7b
```

### Slow Responses

**Symptoms:** Chat responses take >30 seconds

**Solutions:**
1. Increase timeout: `OLLAMA_TIMEOUT=120`
2. Reduce context size: `RAG_MAX_CONTEXT_CHARS=8000`
3. Reduce top_k: `RAG_TOP_K=3`
4. Check system resources (CPU/memory)

### Out of Memory Errors

**Solution:**
1. Use a smaller model (e.g., `qwen2.5-coder:3b`)
2. Reduce batch sizes
3. Clear Ollama cache: `ollama serve --no-memory-lock`

### Empty Responses from LLM

**Solution:**
1. Check Ollama is running correctly
2. Test directly: `curl -X POST http://localhost:11434/api/generate`
3. Verify model is loaded: `ollama list`

## Production Deployment

### Security Considerations

1. **API Security:**
   - Add authentication (JWT, API keys)
   - Validate all inputs
   - Rate limit chat endpoint
   - Use HTTPS in production

2. **Resource Management:**
   - Set up proper timeouts
   - Monitor Ollama memory usage
   - Implement request queuing for high load
   - Consider running Ollama on dedicated hardware

3. **Model Management:**
   - Cache LLM responses for common questions
   - Monitor hallucination rate
   - Log all interactions for audit trails
   - Implement guardrails/content filtering

### Deployment Checklist

- [ ] Ollama running on secure internal network
- [ ] Environment variables configured
- [ ] SSL/TLS certificates installed
- [ ] Authentication enabled
- [ ] Rate limiting configured
- [ ] Logging and monitoring setup
- [ ] Resource limits configured
- [ ] Backup/disaster recovery plan

## Performance Optimization

### Tips for Better Performance

1. **Prompt Optimization:**
   - Use fewer chunks (reduce to 3-5)
   - Truncate large chunks (6000 chars max)
   - Use simpler language in instructions

2. **Model Selection:**
   - `qwen2.5-coder:3b` - Faster, less accurate
   - `qwen2.5-coder:7b` - Balanced (default)
   - `qwen2.5-coder:32b` - Slower, more accurate (if resources allow)

3. **Caching:**
   - Cache frequently asked questions
   - Cache embedding for common queries

## Future Enhancements

- [ ] Conversation history/context
- [ ] User feedback loop for accuracy
- [ ] Custom fine-tuning for specific repos
- [ ] Batch processing for multiple queries
- [ ] GraphQL API alternative
- [ ] WebSocket support for streaming responses
- [ ] Multi-turn conversations
- [ ] Response confidence scoring
- [ ] Automatic hallucination detection

## Example Queries

These types of queries work well with the RAG chat:

1. **Architecture Questions:**
   - "How does the authentication system work?"
   - "What is the overall architecture of this project?"
   - "How are requests routed through the middleware?"

2. **Implementation Details:**
   - "How is JWT validation implemented?"
   - "What database ORM is used and how?"
   - "Show me the error handling pattern used here"

3. **API Documentation:**
   - "What endpoints are available?"
   - "How do I authenticate API requests?"
   - "What parameters does the POST /api/users endpoint accept?"

4. **Code Location:**
   - "Where is the login function implemented?"
   - "Find the password hashing implementation"
   - "Show me all database models"

## Support & Resources

- **Ollama Documentation:** https://ollama.ai
- **Qwen Model Card:** https://huggingface.co/Qwen/Qwen2.5-Coder-7B
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **RAG Best Practices:** https://docs.llamaindex.ai

---

**Created:** May 2026  
**Last Updated:** May 2026
