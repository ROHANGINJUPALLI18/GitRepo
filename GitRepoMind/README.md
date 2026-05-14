# GitRepoMind

GitRepoMind is a repository Q&A app. It analyzes a GitHub repo, stores code chunks in Qdrant, and lets the user chat with the repository through an LLM-backed RAG flow.

## What it does

- Analyzes a public GitHub repository from a repo URL.
- Chunks source files into searchable code segments.
- Generates embeddings for each chunk.
- Stores chunks in Qdrant for semantic retrieval.
- Builds a prompt from the retrieved chunks.
- Sends the prompt to Ollama for the final answer.
- Shows the answer, sources, and chat history in the UI.

## Tech Stack

- Backend: FastAPI, Python, Qdrant, sentence-transformers, Ollama
- Frontend: React, Vite, Tailwind CSS, Axios
- Persistence: localStorage for frontend repo/chat state, Qdrant for vector search, in-memory server stores for analysis/chat history

## Important Folders

### Backend

- `server/src/api/`
  - HTTP routes for analyze, chat, repos, and health.
- `server/src/services/`
  - Core business logic for chunking, embeddings, vector search, prompt building, chat orchestration, GitHub fetches, and LLM calls.
- `server/src/models/`
  - Request and response schemas used by the API.
- `server/src/core/`
  - Shared runtime helpers such as repository cache.
- `server/src/main.py`
  - Uvicorn entry point.
- `server/src/app.py`
  - FastAPI app creation and router registration.

### Frontend

- `client/src/pages/`
  - Main screens for repo analysis and chat.
- `client/src/components/`
  - UI pieces such as chat window, chat input, sidebar, message bubbles, and repo form.
- `client/src/services/api.js`
  - Axios wrapper for backend calls.
- `client/src/App.jsx`
  - React router setup.

### Docs and Tests

- `ARCHITECTURE.md`
  - System architecture overview.
- `QUICKSTART.md`
  - Short setup and run guide.
- `server/src/api/openapi.json`
  - API contract snapshot.
- `tests/`
  - Python tests for backend services.

## How to Run the App Locally

### 1. Start the infrastructure services

The app expects Qdrant and Ollama to be available.

#### Qdrant

From the `server` folder:

```bash
docker-compose up -d
```

If Docker Desktop is not running, start it first.

#### Ollama

Start the Ollama daemon:

```bash
ollama serve
```

Pull the model used by the app:

```bash
ollama pull qwen2.5-coder:7b
```

### 2. Start the backend

From the `server` folder:

```bash
pip install -r requirements.txt
python -m uvicorn src.main:app --reload
```

Backend URLs:

- API: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

### 3. Start the frontend

From the `client` folder:

```bash
npm install
npm run dev
```

Frontend URL:

- `http://localhost:5173`

## Environment Variables

Backend settings are loaded from `server/.env`.

Common values:

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
RAG_TOP_K=5
RAG_MAX_CONTEXT_CHARS=12000
```

Frontend can use:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## API Endpoints

### Repository analysis

`POST /api/analyze-repo`

Request:

```json
{
  "repo_url": "https://github.com/owner/repo",
  "branch": "main",
  "force_reindex": false
}
```

Response includes:

- `repo_id`
- `repo_name`
- `total_files`
- `indexed_files`
- `language_info`
- `entry_points`
- `architecture`
- `readme_overview`

### Chat

`POST /api/chat`

Request:

```json
{
  "repo_id": "owner_repo",
  "query": "How does the authentication module work?",
  "session_id": "user_12345"
}
```

Response includes:

- `success`
- `answer`
- `sources`
- `session_id`

### Chat history

- `GET /api/chat/history/{session_id}`
- `DELETE /api/chat/history/{session_id}`

### Repository management

- `GET /api/repos`
- `GET /api/repos/{repo_id}/stats`
- `DELETE /api/repos/{repo_id}`

### Health

- `GET /health`
- `GET /api/health/qdrant`

## How Chat Works End to End

1. The user enters a GitHub repo URL on the home page.
2. The frontend calls `POST /api/analyze-repo`.
3. The backend downloads the repo, chunks files, generates embeddings, and stores the chunks in Qdrant.
4. The backend returns a stable `repo_id` in the form `owner_repo`.
5. The frontend stores that `repo_id` and navigates to the chat page.
6. When the user sends a question, the frontend calls `POST /api/chat` with:
   - `repo_id`
   - `query`
   - `session_id`
7. The backend does semantic search in Qdrant using the query embedding.
8. The retrieved chunks are inserted into a RAG prompt.
9. Ollama generates the final response from that prompt.
10. The backend returns the answer and sources.
11. The frontend fetches chat history for the same `session_id` and renders the messages.

## How the UI Is Built to Chat with the LLM

### Home page

- `client/src/pages/HomePage.jsx` handles repo analysis.
- `RepoForm.jsx` collects the repo URL and branch.
- After analysis, the UI saves the returned `repo_id` in `localStorage`.

### Chat page

- `client/src/pages/ChatPage.jsx` loads the selected repo.
- It creates or reuses a `session_id` per repo conversation.
- It loads existing chat history from `GET /api/chat/history/{session_id}`.
- It sends new messages through `sendChatMessage(repoId, query, sessionId)`.
- After each response, it refreshes history from the backend so the UI matches server state.

### Chat window

- `ChatWindow.jsx` renders messages and loading states.
- `MessageBubble.jsx` renders user and assistant messages.
- Assistant messages display source chunks when available.

### Why the UI now works correctly

- The frontend no longer depends only on localStorage for chat content.
- It uses the backend as the source of truth for chat history.
- It keeps a real session id so each conversation is tracked separately.
- It still keeps localStorage as a fallback for resilience.

## Production Notes

Use these checks before production deployment:

- Keep Qdrant persistent and reachable through a stable service URL.
- Keep Ollama running with the required model already pulled.
- Set `VITE_API_BASE_URL` for the deployed backend host.
- Add authentication if the app will be public.
- Use a reverse proxy such as Nginx or a cloud gateway in front of the backend.
- Enable structured logging and health monitoring.
- Set restart policies for backend, frontend, Qdrant, and Ollama services.
- Keep `.env` values out of source control.

## Deploying To Vercel And Render

The frontend is set up for Vercel and the backend is set up for Render.

### Frontend on Vercel

- Set the Vercel project root to `client/`.
- Keep `client/vercel.json` in place so React Router routes fall back to `index.html`.
- Set `VITE_API_BASE_URL` in Vercel to the public Render backend URL, for example `https://gitrepomind-backend.onrender.com`.

### Backend on Render

- Use the root `render.yaml` blueprint or create a Render Web Service from the `server/` folder.
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
- Required environment variables:
  - `QDRANT_URL` for the hosted Qdrant endpoint.
  - `QDRANT_API_KEY` if your Qdrant instance requires auth.
  - `OLLAMA_HOST` for the LLM endpoint.
  - `OLLAMA_MODEL` if you want to override the default model.
  - `OPENAI_API_KEY` if you use OpenAI-backed components.

### Important Runtime Note

Render will not provide Qdrant or Ollama for you. The backend expects both services to be reachable from the deployed app, so point `QDRANT_URL` and `OLLAMA_HOST` at hosted instances before treating the deployment as production-ready.
- Use a real persistent store if you need chat history across server restarts.

## Useful Commands

### Backend

```bash
cd server
pip install -r requirements.txt
python -m uvicorn src.main:app --reload
pytest
```

### Frontend

```bash
cd client
npm install
npm run dev
npm run build
```

## Project Notes

- `repo_id` is generated automatically from the GitHub owner and repo name.
- `session_id` identifies a single chat conversation.
- The backend currently stores repository cache and chat history in memory, so a server restart clears those stores.
- Qdrant stores the indexed chunks used for retrieval.
- Ollama generates the final natural-language answer.

## Recommended Flow for Users

1. Start Qdrant.
2. Start Ollama.
3. Start the backend.
4. Start the frontend.
5. Analyze a repository.
6. Open the chat page.
7. Ask questions about the repo.

## Short Version

- Analyze repo first.
- Save the returned `repo_id`.
- Use `repo_id` plus a `session_id` to chat.
- The backend retrieves chunks from Qdrant.
- Ollama writes the answer.
- The frontend shows the result and chat history.
