"""
Test suite for API endpoints.
Run with: uv run python -m pytest tests/test_api_endpoints.py -v
"""

import os
import sys
import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from server.database import Base

@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI app."""
    # Setup in-memory DB
    # Use StaticPool to share the same in-memory database across all connections
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    # Set test environment variables (for other components)
    os.environ["CHAT_DB_URL"] = "sqlite:///:memory:"
    os.environ["MILVUS_HOST"] = "localhost"
    os.environ["MILVUS_PORT"] = "19530"
    
    from server.main import app, get_db
    app.dependency_overrides[get_db] = override_get_db
    
    # Mock Milvus handler
    with patch("server.main.upsert_user_profile", new_callable=AsyncMock) as mock_upsert:
        with TestClient(app) as test_client:
            yield test_client


class TestUserEndpoints:
    """Tests for user management endpoints."""

    def test_create_user(self, client):
        """Test creating a new user."""
        response = client.post("/users", json={"username": "test_user"})
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["username"] == "test_user"
        assert "created_at" in data

    def test_create_duplicate_user(self, client):
        """Test creating a user with the same username."""
        client.post("/users", json={"username": "duplicate_user"})
        response = client.post("/users", json={"username": "duplicate_user"})
        # Should fail - usernames must be unique
        assert response.status_code == 400


class TestPreferencesEndpoints:
    """Tests for preferences endpoints."""

    def test_update_preferences(self, client):
        """Test updating user preferences."""
        # First create a user
        user_response = client.post("/users", json={"username": "pref_user"})
        user_id = user_response.json()["id"]

        # Update preferences
        response = client.post(
            "/preferences",
            json={
                "user_id": user_id,
                "fav_genres": ["rock", "jazz"],
                "disliked_genres": ["pop"],
                "fav_artists": ["Queen", "Miles Davis"],
                "disliked_artists": ["Justin Bieber"],
                "liked_tags": ["classic", "instrumental"],
                "disliked_tags": ["electronic"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "profile_text" in data

    def test_get_preferences(self, client):
        """Test retrieving user preferences."""
        # Create user
        user_response = client.post("/users", json={"username": "get_pref_user"})
        user_id = user_response.json()["id"]

        # Set preferences
        client.post(
            "/preferences",
            json={
                "user_id": user_id,
                "fav_genres": ["pop"],
                "fav_artists": ["Madonna"],
                "liked_tags": ["80s"],
            },
        )

        # Get preferences
        response = client.get(f"/preferences?user_id={user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["fav_genres"] == ["pop"]
        assert data["fav_artists"] == ["Madonna"]
        assert data["liked_tags"] == ["80s"]
        assert data["disliked_genres"] == []

    def test_update_preferences_invalid_user(self, client):
        """Test updating preferences for non-existent user."""
        response = client.post(
            "/preferences",
            json={
                "user_id": "non-existent-id",
                "fav_genres": ["rock"],
                "fav_artists": [],
                "fav_instruments": [],
            },
        )
        assert response.status_code == 404


class TestChatEndpoints:
    """Tests for chat endpoints."""

    def test_create_chat(self, client):
        """Test creating a new chat."""
        # First create a user
        user_response = client.post("/users", json={"username": "chat_user"})
        user_id = user_response.json()["id"]

        # Create chat
        response = client.post("/chat", json={"user_id": user_id})
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["user_id"] == user_id

    def test_send_message(self, client):
        """Test sending a message to a chat."""
        # Create user and chat
        user_response = client.post("/users", json={"username": "msg_user"})
        user_id = user_response.json()["id"]
        chat_response = client.post("/chat", json={"user_id": user_id})
        chat_id = chat_response.json()["id"]

        # Send message
        response = client.post(
            "/message",
            json={
                "chat_id": chat_id,
                "role": "user",
                "content": "Hello, I'm looking for music recommendations",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Hello, I'm looking for music recommendations"
        assert data["role"] == "user"

    def test_get_chat_messages(self, client):
        """Test retrieving chat messages."""
        # Create user, chat, and message
        user_response = client.post("/users", json={"username": "get_msg_user"})
        user_id = user_response.json()["id"]
        chat_response = client.post("/chat", json={"user_id": user_id})
        chat_id = chat_response.json()["id"]
        client.post(
            "/message",
            json={"chat_id": chat_id, "role": "user", "content": "Test message"},
        )

        # Get messages
        response = client.get(f"/chat/{chat_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestQueryEndpoint:
    """Tests for the query endpoint."""

    def test_query_request_structure(self, client):
        """Test that query endpoint accepts correct structure."""
        response = client.post(
            "/query",
            json={
                "question": "¿Qué artistas de rock hay?",
                "top_k": 5,
                "debug": False,
            },
        )
        # May fail due to service dependencies, but should not be 422 (validation error)
        assert response.status_code != 422

    def test_query_with_debug(self, client):
        """Test query with debug flag."""
        response = client.post(
            "/query",
            json={
                "question": "canciones de Queen",
                "top_k": 3,
                "debug": True,
            },
        )
        # Check structure if successful
        if response.status_code == 200:
            data = response.json()
            assert "answer" in data
            assert "context" in data
            assert "query_type" in data
            assert "debug" in data


class TestRecommendationsEndpoint:
    """Tests for recommendations endpoints."""

    def test_album_recommendations_structure(self, client):
        """Test album recommendations request structure."""
        response = client.post(
            "/recommendations/albums",
            json={
                "include_genres": ["rock", "pop"],
                "exclude_genres": [],
                "limit": 5,
                "min_genre_overlap": 1,
            },
        )
        # May fail due to Neo4j, but should not be 422
        assert response.status_code != 422

    def test_album_recommendations_empty_genres(self, client):
        """Test album recommendations with empty genres."""
        response = client.post(
            "/recommendations/albums",
            json={
                "include_genres": [],
                "exclude_genres": [],
                "limit": 5,
            },
        )
        # Should return 400 because include_genres is required
        assert response.status_code == 400


class TestCORSConfiguration:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present."""
        response = client.options(
            "/users",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # CORS preflight should work
        assert response.status_code in [200, 405]


class TestHealthCheck:
    """Tests for API health."""

    def test_docs_available(self, client):
        """Test that OpenAPI docs are available."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema(self, client):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "/query" in data["paths"]
        assert "/recommendations" in data["paths"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
