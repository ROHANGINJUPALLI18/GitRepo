# RAG Chat Layer - Technical Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER/CLIENT LAYER                        │
│                                                                 │
│  curl, Python requests, FastAPI Swagger UI, etc.              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ POST /api/chat
                         │ {"query": "...", "top_k": 5}
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI LAYER                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  ChatRequest (Pydantic)                                 │  │
│  │  - query: str (validated)                               │  │
│  │  - top_k: int (1-50, default 5)                        │  │
│  │  - repo_filter: str (optional)                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                         │                                       │
│                         ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  /api/chat endpoint                                     │  │
│  │  - Request validation                                   │  │
│  │  - Dependency injection: get_chat_service()            │  │
│  │  - Service call with parameters                         │  │
│  └─────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CHAT SERVICE LAYER                           │
│                  (Orchestration Service)                        │
│                                                                 │
│  ChatService - Main RAG coordinator                            │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  chat(query, top_k, repo_filter) -> dict                │ │
│  │                                                          │ │
│  │  Step 1: Call SearchService.search()                    │ │
│  │  Step 2: Call PromptService.build_rag_prompt()          │ │
│  │  Step 3: Call LLMService.generate_response()            │ │
│  │  Step 4: Extract citations from chunks                  │ │
│  │  Step 5: Format and return response                     │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────┬────────────────────────────────────────────────────────┘
         │
         ├─────────────────┬──────────────────┬──────────────────┐
         │                 │                  │                  │
         ▼                 ▼                  ▼                  ▼
┌──────────────────┐ ┌────────────────┐ ┌───────────────┐ ┌──────────┐
│ SearchService    │ │ PromptService  │ │ LLMService    │ │ Config   │
│                  │ │                │ │               │ │          │
│ ┌──────────────┐ │ │┌──────────────┐│ │┌────────────┐ │ │Settings: │
│ │Embedding     │ │ ││Build RAG     ││ ││Generate   │ │ │- Ollama  │
│ │Service       │ │ ││Prompt        ││ ││Response   │ │ │- RAG     │
│ └──────────────┘ │ ││- Combine     │ │ ││via Ollama │ │ │- Search  │
│                  │ ││  query +     │ │ │└────────────┘ │ │          │
│ ┌──────────────┐ │ ││  chunks      │ │ │             │ │ From .env │
│ │Vector Store  │ │ ││- Format      │ │ │ Ollama      │ │          │
│ │(Qdrant)      │ │ ││  metadata    │ │ │ Connection: │ │ Type:    │
│ │- Store       │ │ ││- Truncate    │ │ │             │ │ - str    │
│ │- Retrieve    │ │ ││  safely      │ │ │ qwen2.5-    │ │ - int    │
│ │- Search      │ │ ││- Add         │ │ │ coder:7b    │ │ - float  │
│ └──────────────┘ │ ││  instructions│ │ │             │ │ - bool   │
│                  │ │└──────────────┘ │ │ Params:     │ │          │
│ Returns:         │ │                │ │ - temp:0.2  │ │ Defaults:│
│ - chunks        │ │ Returns:       │ │ - top_p:0.9 │ │ provided │
│ - metadata      │ │ - prompt       │ │ - timeout:60│ │          │
│ - scores        │ │   string       │ │             │ │ Validation│
└──────────────────┘ │                │ │ Returns:    │ │ included │
                     │└──────────────┘ │ │ - answer    │ │          │
                     └────────────────┘ │  string      │ │          │
                                        └────────────────┘ └──────────┘
                     │                 │                  │
                     └─────────────────┼──────────────────┘
                                       │
                                       │ (Orchestration)
                                       ▼
                        ┌──────────────────────────┐
                        │   External Services      │
                        │                          │
                        │  Qdrant (Vector DB)      │
                        │  PostgreSQL (if used)    │
                        │  Ollama (LLM)            │
                        │  Redis (if used)         │
                        └──────────────────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────┐
                        │   Response Assembly      │
                        │                          │
                        │ {                        │
                        │   "success": true,       │
                        │   "query": "...",        │
                        │   "answer": "...",       │
                        │   "sources": [...],      │
                        │   "chunks_used": 2,      │
                        │   "chunks_metadata":[...]│
                        │ }                        │
                        └──────────────────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────┐
                        │   ChatResponse           │
                        │   (Pydantic validation)  │
                        └──────────────────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────┐
                        │   JSON Response          │
                        │   (HTTP 200)             │
                        └──────────────────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────┐
                        │   CLIENT                 │
                        │   - Receives answer      │
                        │   - Displays to user     │
                        │   - Shows citations      │
                        └──────────────────────────┘
```

## Data Flow Diagram

```
INPUT: User Query
  "How does JWT authentication work?"
         │
         ▼
   VALIDATION
   ┌─────────────────────┐
   │ Query validation    │
   │ - Not empty         │
   │ - Max 5000 chars    │
   │ - Valid UTF-8       │
   └──────────┬──────────┘
              │
              ▼
   RETRIEVAL (SearchService)
   ┌──────────────────────────────┐
   │ 1. Generate embedding        │
   │ 2. Search Qdrant with        │
   │    query_vector, top_k=5     │
   │ 3. Return chunks with:       │
   │    - text                    │
   │    - file_path               │
   │    - start_line/end_line     │
   │    - language                │
   │    - score                   │
   └──────────┬───────────────────┘
              │
    ┌─────────┴──────────┐
    │ 2 chunks retrieved │
    │ (score: 0.95, 0.87)│
    └─────────┬──────────┘
              │
              ▼
   PROMPT BUILDING (PromptService)
   ┌──────────────────────────────┐
   │ 1. Format chunks with        │
   │    metadata                  │
   │ 2. Sort by relevance         │
   │ 3. Build context section:    │
   │    - Include file paths      │
   │    - Include line numbers    │
   │    - Include code blocks     │
   │ 4. Create full prompt:       │
   │    - System instructions     │
   │    - User query              │
   │    - Context                 │
   │    - Answer instructions     │
   └──────────┬───────────────────┘
              │
    ┌─────────┴──────────────────────┐
    │ RAG Prompt (1,250 chars)        │
    │ - Instructions: 400 chars       │
    │ - Query: 50 chars               │
    │ - Context: 800 chars            │
    └─────────┬──────────────────────┘
              │
              ▼
   LLM GENERATION (LLMService)
   ┌──────────────────────────────┐
   │ 1. Verify Ollama available   │
   │ 2. Prepare request:          │
   │    - model: qwen2.5-coder:7b │
   │    - temperature: 0.2        │
   │    - top_p: 0.9              │
   │    - max_tokens: 1024        │
   │ 3. Send prompt to Ollama     │
   │ 4. Stream response           │
   │ 5. Aggregate result          │
   │ 6. Return answer string      │
   └──────────┬───────────────────┘
              │
    ┌─────────┴──────────────────┐
    │ Generated Answer (450 chars)│
    │ "JWT tokens are created..  │
    │  Found in src/auth/..."     │
    └─────────┬──────────────────┘
              │
              ▼
   RESPONSE FORMATTING (ChatService)
   ┌──────────────────────────────┐
   │ 1. Extract source citations: │
   │    - src/auth/login.py       │
   │    - src/middleware/jwt.py   │
   │ 2. Deduplicate sources       │
   │ 3. Build metadata:           │
   │    - chunk scores            │
   │    - line numbers            │
   │    - languages               │
   │ 4. Create response dict      │
   │ 5. Validate response schema  │
   └──────────┬───────────────────┘
              │
    ┌─────────┴──────────────────────┐
    │ ChatResponse (Pydantic)         │
    │ {                               │
    │   "success": true,              │
    │   "query": "How does JWT...",   │
    │   "answer": "JWT tokens...",    │
    │   "sources": [                  │
    │     "src/auth/login.py",        │
    │     "src/middleware/jwt.py"     │
    │   ],                            │
    │   "chunks_used": 2,             │
    │   "chunks_metadata": [...]      │
    │ }                               │
    └─────────┬──────────────────────┘
              │
              ▼
OUTPUT: JSON Response (HTTP 200)
   Returned to client
   User sees answer + citations
```

## Component Interaction Diagram

```
                      ┌─────────────────────────┐
                      │    FastAPI Application  │
                      │                         │
                      │  @router.post("/chat")  │
                      │  - Validates request    │
                      │  - Calls ChatService    │
                      │  - Returns response     │
                      └────────────┬────────────┘
                                   │
                      ┌────────────┴────────────┐
                      │                         │
                      ▼                         ▼
            ┌──────────────────┐      ┌──────────────────┐
            │  ChatService     │      │  Config/Settings │
            │                  │      │                  │
            │  Methods:        │      │  Provides:       │
            │  - chat()        │      │  - ollama_host   │
            │  - health_check()│      │  - ollama_model  │
            │  - _extract_     │      │  - temperatures  │
            │    citations()   │      │  - timeouts      │
            │                  │      │  - rag settings  │
            └────┬────┬────┬───┘      └──────────────────┘
                 │    │    │
        ┌────────┘    │    └──────────┐
        │             │               │
        ▼             ▼               ▼
  ┌─────────────┐ ┌──────────────┐ ┌───────────────┐
  │ Search      │ │ Prompt       │ │ LLM Service   │
  │ Service     │ │ Service      │ │               │
  │             │ │              │ │ Methods:      │
  │ Methods:    │ │ Methods:     │ │ - generate_   │
  │ - search()  │ │ - build_rag_ │ │   response()  │
  │             │ │   prompt()   │ │ - health_     │
  │ Returns:    │ │ - format_    │ │   check()     │
  │ - chunks    │ │   chunks()   │ │               │
  │ - scores    │ │ - truncate_  │ │ Uses:         │
  │ - metadata  │ │   context()  │ │ - Ollama API  │
  │             │ │              │ │ - qwen model  │
  │ Uses:       │ │ Returns:     │ │               │
  │ - Embedding │ │ - prompt     │ │ Returns:      │
  │   Service   │ │   string     │ │ - response    │
  │ - Vector    │ │              │ │   text        │
  │   Store     │ │ Uses:        │ │               │
  │             │ │ - Config     │ │ Uses:         │
  │             │ │   settings   │ │ - Ollama      │
  │             │ │              │ │   connection  │
  └─────────────┘ └──────────────┘ └───────────────┘
        │             │               │
        └────────┬────┴───────┬───────┘
                 │            │
        ┌────────┴────┐       │
        │ External    │       │
        │ Services    │       │
        │             │       │
        │ ┌─────────┐ │       │
        │ │ Qdrant  │ │       │
        │ │ Vector  │ │       │
        │ │ Store   │ │       │
        │ └─────────┘ │       │
        │             │       │
        │ ┌─────────┐ │       │
        │ │ Sentence│ │       │
        │ │Transform│ │       ◄────────┐
        │ │ Encoder │ │               │
        │ └─────────┘ │        Ollama API
        │             │        qwen2.5-coder:7b
        └─────────────┘               │
                                      │
                            ┌─────────┴─────────┐
                            │ Ollama Server     │
                            │ http://localhost: │
                            │ 11434             │
                            └───────────────────┘
```

## Error Handling Flow

```
                        REQUEST
                           │
                           ▼
                  ┌─────────────────┐
                  │ Input Validation│
                  └────────┬────────┘
                           │
              ┌────────────┴────────────┐
              │ Valid?                  │
              │                         │
        YES ──┤ NO                      │
              ▼ ▼                       │
           Error ┌────────────────────┐ │
         Response│ 422 - Validation   │ │
                 │ Error              │ │
                 └────────────────────┘ │
                                        │
                                        ▼
                            ┌───────────────────┐
                            │ SearchService     │
                            │ Retrieve chunks   │
                            └────────┬──────────┘
                                     │
                        ┌────────────┴────────────┐
                        │ Success?                │
                        │                         │
                    YES ┤ NO (empty results)     │
                        ▼ ▼                       │
                    Empty  ┌────────────────────┐ │
                    Context│ Build prompt for   │ │
                           │ missing context    │ │
                           └────────────────────┘ │
                                                  │
                                                  ▼
                            ┌───────────────────────────┐
                            │ PromptService             │
                            │ Build RAG Prompt          │
                            │ - Validate query          │
                            │ - Format chunks           │
                            │ - Truncate if needed      │
                            └────────┬──────────────────┘
                                     │
                        ┌────────────┴────────────┐
                        │ Success?                │
                        │                         │
                    YES ┤ NO                      │
                        ▼ ▼                       │
                    Continue │                   │
                            └────────────────────┘
                                     │
                                     ▼
                            ┌───────────────────────────┐
                            │ LLMService                │
                            │ Generate Response         │
                            │ - Check Ollama available  │
                            │ - Send prompt             │
                            │ - Validate response       │
                            └────────┬──────────────────┘
                                     │
                        ┌────────────┴────────────┐
                        │ Success?                │
                        │                         │
                    YES ┤ NO (connection error)   │
                        ▼ ▼                       │
                    Response │                   │
                             ▼                   │
                     ┌──────────────────────┐    │
                     │ Error Response:      │    │
                     │ "Failed to generate  │    │
                     │  response: [error]"  │    │
                     │ HTTP 200 with        │    │
                     │ success: false        │    │
                     └──────────────────────┘    │
                                                 │
                                                 ▼
                            ┌───────────────────────────┐
                            │ Response Formatting       │
                            │ - Extract citations      │
                            │ - Remove duplicates      │
                            │ - Build metadata         │
                            │ - Create response dict   │
                            └────────┬──────────────────┘
                                     │
                                     ▼
                            ┌───────────────────────────┐
                            │ Validation & Return       │
                            │ - Pydantic schema check   │
                            │ - HTTP 200 response       │
                            │ - JSON serialization      │
                            └────────┬──────────────────┘
                                     │
                                     ▼
                            ┌───────────────────────────┐
                            │ CLIENT RECEIVES           │
                            │ SUCCESS RESPONSE          │
                            │ (with answer or error msg)│
                            └───────────────────────────┘
```

## Service Dependencies

```
┌──────────────────────────────────────────────────────┐
│ ChatService (Main Orchestrator)                      │
│                                                      │
│ Dependencies:                                        │
│ ├─ SearchService                                    │
│ │  └─ EmbeddingService                              │
│ │  └─ QdrantVectorStore                             │
│ ├─ PromptService                                    │
│ │  └─ Settings/Config                               │
│ ├─ LLMService                                       │
│ │  └─ Ollama (external HTTP)                        │
│ └─ Settings/Config                                  │
│                                                      │
│ Dependency Injection:                                │
│ ├─ Constructor parameters for flexibility           │
│ ├─ Lazy loading of expensive resources              │
│ ├─ LRU cache for service instance                   │
│ └─ Testable with mocks                              │
└──────────────────────────────────────────────────────┘
```

## Performance Considerations

```
OPERATION TIMELINE (typical):

User Query
  ├─ Validation: 1ms
  ├─ SearchService:
  │  ├─ Embedding generation: 50-100ms
  │  └─ Vector search: 10-50ms
  ├─ PromptService:
  │  ├─ Chunk formatting: 5-10ms
  │  └─ Prompt building: 10-20ms
  ├─ LLMService:
  │  └─ Ollama generation: 2-10 seconds
  │     (depends on model, hardware)
  ├─ Citation extraction: 1-5ms
  └─ Response formatting: 5-10ms

TOTAL: ~2-10 seconds (dominated by LLM generation)

OPTIMIZATION STRATEGIES:
- Reduce RAG_TOP_K (fewer chunks to process)
- Reduce RAG_MAX_CONTEXT_CHARS (smaller prompts)
- Use smaller LLM model (e.g., 3B instead of 7B)
- Cache common queries
- Increase OLLAMA_TEMPERATURE (faster, less accurate)
```

---

**Visual diagrams help understand the complete flow and architecture of the RAG chat layer implementation.**
