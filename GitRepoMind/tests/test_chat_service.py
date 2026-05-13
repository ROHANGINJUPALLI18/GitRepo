"""Tests for the RAG chat services and endpoints."""

import os
import sys
from unittest.mock import MagicMock, patch

# Ensure server is on path before importing project modules
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SERVER_PATH = os.path.join(ROOT, "server")
if SERVER_PATH not in sys.path:
    sys.path.insert(0, SERVER_PATH)

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.api.chat import get_chat_service
from src.services.chat_service import ChatService
from src.services.prompt_service import PromptService
from src.services.llm_service import LLMService


# ── Test Prompt Service ──────────────────────────────────────────────

class TestPromptService:
    """Test suite for PromptService."""

    @pytest.fixture
    def service(self):
        return PromptService()

    def test_build_rag_prompt_with_chunks(self, service):
        """Test building a RAG prompt with code chunks."""
        query = "How does authentication work?"
        chunks = [
            {
                "file_path": "src/auth/login.py",
                "text": "def authenticate(user, password):\n    return jwt_token",
                "start_line": 10,
                "end_line": 12,
                "language": "python",
                "score": 0.95,
            }
        ]

        prompt = service.build_rag_prompt(query, chunks)

        assert query in prompt
        assert "src/auth/login.py" in prompt
        assert "authenticate" in prompt
        assert "Instructions:" in prompt
        assert len(prompt) > 100

    def test_build_rag_prompt_empty_chunks(self, service):
        """Test building a RAG prompt with no chunks."""
        query = "How does authentication work?"
        chunks = []

        prompt = service.build_rag_prompt(query, chunks)

        assert query in prompt
        assert "not available" in prompt.lower() or "no relevant" in prompt.lower()

    def test_build_rag_prompt_empty_query_raises(self, service):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            service.build_rag_prompt("", [])

    def test_build_rag_prompt_multiple_chunks(self, service):
        """Test building a prompt with multiple chunks."""
        query = "Authentication flow"
        chunks = [
            {
                "file_path": "src/auth/login.py",
                "text": "login code",
                "start_line": 10,
                "end_line": 20,
                "language": "python",
                "score": 0.95,
            },
            {
                "file_path": "src/auth/token.py",
                "text": "token code",
                "start_line": 1,
                "end_line": 15,
                "language": "python",
                "score": 0.85,
            },
        ]

        prompt = service.build_rag_prompt(query, chunks)

        assert "src/auth/login.py" in prompt
        assert "src/auth/token.py" in prompt
        assert "login code" in prompt
        assert "token code" in prompt

    def test_truncate_context(self, service):
        """Test context truncation."""
        text = "a" * 1000
        truncated = service.truncate_context(text, 100)

        assert len(truncated) <= 104  # 100 + "..."
        assert truncated.endswith("...")

    def test_format_chunks_with_payload(self, service):
        """Test formatting chunks that have payload nesting."""
        chunks = [
            {
                "payload": {
                    "file_path": "src/auth.py",
                    "text": "code here",
                    "start_line": 1,
                    "end_line": 10,
                    "language": "python",
                }
            }
        ]

        formatted = service._format_chunks(chunks)

        assert len(formatted) == 1
        assert formatted[0]["file_path"] == "src/auth.py"
        assert formatted[0]["text"] == "code here"


# ── Test LLM Service ────────────────────────────────────────────────

class TestLLMService:
    """Test suite for LLMService."""

    @pytest.fixture
    def service(self):
        return LLMService()

    def test_llm_service_initialization(self, service):
        """Test LLM service initializes correctly."""
        assert service.host == "http://localhost:11434"
        assert service.model == "qwen2.5-coder:7b"
        assert service.temperature == 0.2
        assert service.top_p == 0.9

    def test_generate_response_empty_prompt_raises(self, service):
        """Test that empty prompt raises ValueError."""
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            service.generate_response("")

    @patch("src.services.llm_service.ollama")
    def test_generate_response_success(self, mock_ollama, service):
        """Test successful response generation."""
        # Mock ollama response
        mock_ollama.generate.return_value = {
            "response": "This is the generated answer",
            "total_duration": 1e9,
        }
        service._client = mock_ollama

        response = service.generate_response("What is this code?")

        assert response == "This is the generated answer"
        assert len(response) > 0

    @patch("src.services.llm_service.ollama")
    def test_generate_response_empty_response_raises(self, mock_ollama, service):
        """Test that empty model response raises RuntimeError."""
        mock_ollama.generate.return_value = {"response": ""}
        service._client = mock_ollama

        with pytest.raises(RuntimeError, match="empty response"):
            service.generate_response("What is this code?")

    def test_health_check_returns_bool(self, service):
        """Test that health check returns boolean."""
        result = service.health_check()
        assert isinstance(result, bool)


# ── Test Chat Service ──────────────────────────────────────────────

class TestChatService:
    """Test suite for ChatService."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        search_service = MagicMock()
        prompt_service = MagicMock()
        llm_service = MagicMock()

        search_service.search.return_value = {
            "query": "test",
            "results": [
                {
                    "file_path": "src/auth.py",
                    "text": "auth code",
                    "start_line": 1,
                    "end_line": 10,
                    "language": "python",
                    "score": 0.95,
                }
            ],
        }

        prompt_service.build_rag_prompt.return_value = "Built prompt"
        llm_service.generate_response.return_value = "Generated answer"

        return search_service, prompt_service, llm_service

    def test_chat_service_initialization(self, mock_services):
        """Test chat service initializes correctly."""
        search, prompt, llm = mock_services
        service = ChatService(
            search_service=search,
            prompt_service=prompt,
            llm_service=llm,
        )

        assert service.search_service is search
        assert service.prompt_service is prompt
        assert service.llm_service is llm

    def test_chat_empty_query_raises(self, mock_services):
        """Test that empty query raises ValueError."""
        search, prompt, llm = mock_services
        service = ChatService(
            search_service=search,
            prompt_service=prompt,
            llm_service=llm,
        )

        with pytest.raises(ValueError, match="Query cannot be empty"):
            service.chat("")

    def test_chat_success(self, mock_services):
        """Test successful chat interaction."""
        search, prompt, llm = mock_services
        service = ChatService(
            search_service=search,
            prompt_service=prompt,
            llm_service=llm,
        )

        result = service.chat("How does auth work?", top_k=5)

        assert result["success"] is True
        assert result["query"] == "How does auth work?"
        assert result["answer"] == "Generated answer"
        assert "src/auth.py" in result["sources"]
        assert result["chunks_used"] == 1

    def test_chat_no_chunks_retrieved(self, mock_services):
        """Test chat when no chunks are retrieved."""
        search, prompt, llm = mock_services
        search.search.return_value = {
            "query": "test",
            "results": [],
        }

        service = ChatService(
            search_service=search,
            prompt_service=prompt,
            llm_service=llm,
        )

        result = service.chat("Obscure question")

        assert result["success"] is True
        assert result["chunks_used"] == 0

    def test_extract_citations(self, mock_services):
        """Test citation extraction from chunks."""
        search, prompt, llm = mock_services
        service = ChatService(
            search_service=search,
            prompt_service=prompt,
            llm_service=llm,
        )

        chunks = [
            {"file_path": "src/auth.py"},
            {"file_path": "src/auth.py"},  # Duplicate
            {"file_path": "src/token.py"},
        ]

        citations = service._extract_citations(chunks)

        assert len(citations) == 2
        assert "src/auth.py" in citations
        assert "src/token.py" in citations

    def test_health_check(self, mock_services):
        """Test health check returns dict."""
        search, prompt, llm = mock_services
        llm.health_check.return_value = True

        service = ChatService(
            search_service=search,
            prompt_service=prompt,
            llm_service=llm,
        )

        result = service.health_check()

        assert isinstance(result, dict)
        assert "llm_service" in result


# ── Test Chat API Endpoint ────────────────────────────────────────

class TestChatAPI:
    """Test suite for FastAPI chat endpoint."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_chat_service(self):
        """Create mock chat service for endpoint tests."""
        service = MagicMock()
        service.chat.return_value = {
            "success": True,
            "query": "test query",
            "answer": "test answer",
            "sources": ["src/test.py"],
            "chunks_used": 1,
            "chunks_metadata": [],
        }
        return service

    def test_chat_endpoint_success(self, client, mock_chat_service):
        """Test successful chat endpoint call."""
        app.dependency_overrides[get_chat_service] = lambda: mock_chat_service

        response = client.post(
            "/api/chat",
            json={
                "query": "How does auth work?",
                "top_k": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["query"] == "test query"
        assert data["answer"] == "test answer"

        app.dependency_overrides.clear()

    def test_chat_endpoint_with_repo_filter(self, client, mock_chat_service):
        """Test chat endpoint with repository filter."""
        app.dependency_overrides[get_chat_service] = lambda: mock_chat_service

        response = client.post(
            "/api/chat",
            json={
                "query": "How does auth work?",
                "top_k": 5,
                "repo_filter": "owner/repo",
            },
        )

        assert response.status_code == 200
        mock_chat_service.chat.assert_called_once_with(
            query="How does auth work?",
            top_k=5,
            repo_filter="owner/repo",
        )

        app.dependency_overrides.clear()

    def test_chat_endpoint_invalid_query(self, client, mock_chat_service):
        """Test chat endpoint with invalid query."""
        app.dependency_overrides[get_chat_service] = lambda: mock_chat_service

        response = client.post(
            "/api/chat",
            json={
                "query": "",  # Empty query
                "top_k": 5,
            },
        )

        assert response.status_code == 422  # Validation error

        app.dependency_overrides.clear()

    def test_chat_endpoint_default_top_k(self, client, mock_chat_service):
        """Test chat endpoint uses default top_k when not provided."""
        app.dependency_overrides[get_chat_service] = lambda: mock_chat_service

        response = client.post(
            "/api/chat",
            json={
                "query": "How does auth work?",
            },
        )

        assert response.status_code == 200
        # Should use default top_k=5
        mock_chat_service.chat.assert_called_once()

        app.dependency_overrides.clear()

    def test_health_endpoint_success(self, client, mock_chat_service):
        """Test health check endpoint."""
        app.dependency_overrides[get_chat_service] = lambda: mock_chat_service
        mock_chat_service.health_check.return_value = {
            "search_service": "healthy",
            "llm_service": True,
            "prompt_service": "healthy",
        }

        response = client.get("/api/chat/health")

        assert response.status_code == 200
        data = response.json()
        assert "llm_service" in data

        app.dependency_overrides.clear()


# ── Integration Tests ────────────────────────────────────────────

class TestRAGIntegration:
    """Integration tests for the complete RAG pipeline."""

    def test_rag_pipeline_with_mock_services(self):
        """Test complete RAG pipeline with mocked services."""
        # Create services
        search_service = MagicMock()
        prompt_service = PromptService()
        llm_service = MagicMock()

        search_service.search.return_value = {
            "results": [
                {
                    "file_path": "src/auth/login.py",
                    "text": "def authenticate(user, password):\n    return jwt_token",
                    "start_line": 10,
                    "end_line": 15,
                    "language": "python",
                    "score": 0.95,
                }
            ]
        }

        llm_service.generate_response.return_value = (
            "Authentication is done using JWT tokens. "
            "The authenticate function in src/auth/login.py handles this."
        )

        chat_service = ChatService(
            search_service=search_service,
            prompt_service=prompt_service,
            llm_service=llm_service,
        )

        # Run chat
        result = chat_service.chat("How does authentication work?")

        # Verify result
        assert result["success"] is True
        assert "JWT" in result["answer"]
        assert "src/auth/login.py" in result["sources"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
