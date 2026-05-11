import os
import sys

# Ensure server is on path before importing project modules.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SERVER_PATH = os.path.join(ROOT, "server")
if SERVER_PATH not in sys.path:
    sys.path.insert(0, SERVER_PATH)

from fastapi.testclient import TestClient

from src.app import app
from src.api.search import get_search_service
from src.services.search_service import SimilaritySearchService


class FakeEmbeddingService:
    def __init__(self):
        self.received_texts = []

    def embed_texts(self, texts):
        self.received_texts.extend(texts)
        return [[0.1, 0.2, 0.3]]


class FakeVectorStore:
    def __init__(self):
        self.calls = []

    def search_similar(self, query_vector, top_k=5, repo_filter=None):
        self.calls.append(
            {
                "query_vector": query_vector,
                "top_k": top_k,
                "repo_filter": repo_filter,
            }
        )
        return [
            {
                "score": 0.94,
                "file_path": "src/auth/login.py",
                "payload": {
                    "file_path": "src/auth/login.py",
                    "chunk_index": 0,
                    "start_line": 1,
                    "end_line": 80,
                    "tokens": 210,
                    "repo": "owner/repo",
                    "branch": "main",
                    "language": "Python",
                    "file_type": "source_code",
                    "folder": "auth",
                    "is_entry_point": False,
                    "text": "def authenticate_user(...): return jwt_token",
                },
            },
            {
                "score": 0.82,
                "file_path": "src/middleware/jwt.py",
                "payload": {
                    "file_path": "src/middleware/jwt.py",
                    "chunk_index": 1,
                    "start_line": 1,
                    "end_line": 60,
                    "tokens": 180,
                    "repo": "owner/repo",
                    "branch": "main",
                    "language": "Python",
                    "file_type": "source_code",
                    "folder": "middleware",
                    "is_entry_point": False,
                    "text": "def verify_token(...): pass",
                },
            },
        ]


def test_similarity_search_service_formats_results():
    embedding_service = FakeEmbeddingService()
    vector_store = FakeVectorStore()
    service = SimilaritySearchService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        default_top_k=5,
    )

    response = service.search(
        "how does authentication work?",
        top_k=2,
        repo_filter="owner/repo",
    )

    assert embedding_service.received_texts == ["how does authentication work?"]
    assert vector_store.calls[0]["top_k"] == 2
    assert vector_store.calls[0]["repo_filter"] == "owner/repo"
    assert response["count"] == 2
    assert response["results"][0]["file_path"] == "src/auth/login.py"
    assert response["results"][0]["rank"] == 1
    assert response["results"][0]["snippet"].startswith("def authenticate_user")


def test_similarity_search_service_rejects_empty_query():
    service = SimilaritySearchService(
        embedding_service=FakeEmbeddingService(),
        vector_store=FakeVectorStore(),
        default_top_k=5,
    )

    try:
        service.search("   ")
        assert False, "Expected ValueError for empty query"
    except ValueError as exc:
        assert "Query cannot be empty" in str(exc)


def test_search_endpoint_uses_injected_service():
    class StubService:
        def search(self, query, top_k=None, repo_filter=None):
            return {
                "query": query,
                "top_k": top_k or 5,
                "repo_filter": repo_filter,
                "count": 1,
                "results": [
                    {
                        "rank": 1,
                        "score": 0.99,
                        "file_path": "src/auth/login.py",
                        "chunk_index": 0,
                        "start_line": 1,
                        "end_line": 10,
                        "tokens": 25,
                        "repo": "owner/repo",
                        "branch": "main",
                        "language": "Python",
                        "file_type": "source_code",
                        "folder": "auth",
                        "is_entry_point": False,
                        "text": "def login(...): pass",
                        "snippet": "def login(...): pass",
                        "payload": {},
                    }
                ],
            }

    app.dependency_overrides[get_search_service] = lambda: StubService()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/search",
            json={
                "query": "how does authentication work?",
                "top_k": 1,
                "repo_filter": "owner/repo",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "how does authentication work?"
        assert data["count"] == 1
        assert data["results"][0]["file_path"] == "src/auth/login.py"
    finally:
        app.dependency_overrides.pop(get_search_service, None)