#!/usr/bin/env python
"""
Manual API testing script for pmllm.
Run with: uv run python scripts/test_api_manual.py

This script tests the main API endpoints to verify they work correctly.
Make sure the server is running before executing this script:
  uv run python main.py start
"""

import json
import sys
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests")
    sys.exit(1)


BASE_URL = "http://localhost:8000"


def print_result(name: str, success: bool, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
    """Pretty print test results."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\n{status} - {name}")
    if error:
        print(f"  Error: {error}")
    if data and success:
        print(f"  Response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")


def test_create_user() -> Optional[str]:
    """Test creating a user."""
    try:
        response = requests.post(
            f"{BASE_URL}/users",
            json={"username": "test_user_manual"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print_result("Create User", True, data)
            return data.get("id")
        else:
            print_result("Create User", False, error=f"Status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print_result("Create User", False, error=str(e))
        return None


def test_update_preferences(user_id: str) -> bool:
    """Test updating preferences."""
    try:
        response = requests.post(
            f"{BASE_URL}/preferences",
            json={
                "user_id": user_id,
                "fav_genres": ["rock", "jazz", "classical"],
                "fav_artists": ["Queen", "Miles Davis", "Bach"],
                "fav_instruments": ["guitar", "piano", "saxophone"]
            },
            timeout=10
        )
        if response.status_code == 200:
            print_result("Update Preferences", True, response.json())
            return True
        else:
            print_result("Update Preferences", False, error=f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_result("Update Preferences", False, error=str(e))
        return False


def test_create_chat(user_id: str) -> Optional[str]:
    """Test creating a chat."""
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"user_id": user_id},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print_result("Create Chat", True, data)
            return data.get("id")
        else:
            print_result("Create Chat", False, error=f"Status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print_result("Create Chat", False, error=str(e))
        return None


def test_query_songs():
    """Test querying for songs."""
    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={
                "question": "¿Cuáles son las canciones más populares?",
                "top_k": 5,
                "debug": False
            },
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            print_result("Query Songs", True, {
                "query_type": data.get("query_type"),
                "answer_preview": data.get("answer", "")[:200],
                "songs_count": len(data.get("songs", [])),
                "latency_ms": data.get("latency_ms")
            })
            return True
        else:
            print_result("Query Songs", False, error=f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_result("Query Songs", False, error=str(e))
        return False


def test_query_artist():
    """Test querying for artist details."""
    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={
                "question": "¿Quién es el artista Queen?",
                "top_k": 5,
                "debug": False
            },
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            print_result("Query Artist", True, {
                "query_type": data.get("query_type"),
                "answer_preview": data.get("answer", "")[:200],
                "artists_count": len(data.get("artists", [])),
                "latency_ms": data.get("latency_ms")
            })
            return True
        else:
            print_result("Query Artist", False, error=f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_result("Query Artist", False, error=str(e))
        return False


def test_query_albums():
    """Test querying for albums."""
    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={
                "question": "¿Qué álbumes de rock existen?",
                "top_k": 5,
                "debug": False
            },
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            print_result("Query Albums", True, {
                "query_type": data.get("query_type"),
                "answer_preview": data.get("answer", "")[:200],
                "albums_count": len(data.get("albums", [])),
                "latency_ms": data.get("latency_ms")
            })
            return True
        else:
            print_result("Query Albums", False, error=f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_result("Query Albums", False, error=str(e))
        return False


def test_album_recommendations():
    """Test album recommendations."""
    try:
        response = requests.post(
            f"{BASE_URL}/recommendations/albums",
            json={
                "include_genres": ["rock", "pop"],
                "exclude_genres": [],
                "limit": 5,
                "min_genre_overlap": 1
            },
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            print_result("Album Recommendations", True, {
                "generated_from": data.get("generated_from"),
                "recommendations_count": len(data.get("recommendations", []))
            })
            return True
        else:
            print_result("Album Recommendations", False, error=f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_result("Album Recommendations", False, error=str(e))
        return False


def test_user_recommendations(user_id: str):
    """Test user-based recommendations."""
    try:
        response = requests.post(
            f"{BASE_URL}/recommendations",
            params={"user_id": user_id},
            timeout=120
        )
        if response.status_code == 200:
            data = response.json()
            print_result("User Recommendations", True, {
                "recommendations_count": len(data.get("recommendations", [])),
                "summary_preview": data.get("general_summary", "")[:200]
            })
            return True
        else:
            print_result("User Recommendations", False, error=f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_result("User Recommendations", False, error=str(e))
        return False


def test_cors():
    """Test CORS headers."""
    try:
        response = requests.options(
            f"{BASE_URL}/users",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            },
            timeout=5
        )
        has_cors = "access-control-allow-origin" in {k.lower() for k in response.headers.keys()}
        print_result("CORS Headers", has_cors or response.status_code == 200, 
                    {"headers": dict(response.headers)} if has_cors else None,
                    error=None if has_cors else "CORS headers not found")
        return has_cors
    except Exception as e:
        print_result("CORS Headers", False, error=str(e))
        return False


def test_health():
    """Test API health via docs endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        success = response.status_code == 200
        print_result("API Health (Docs)", success)
        return success
    except Exception as e:
        print_result("API Health (Docs)", False, error=str(e))
        return False


def main():
    print("=" * 60)
    print("PMLLM API Test Suite")
    print("=" * 60)
    print(f"Testing API at: {BASE_URL}")
    
    # Test API health first
    if not test_health():
        print("\n⚠️  API is not responding. Make sure the server is running:")
        print("   uv run python main.py start")
        sys.exit(1)
    
    # Run tests
    results = []
    
    # User management
    user_id = test_create_user()
    results.append(("Create User", user_id is not None))
    
    if user_id:
        results.append(("Update Preferences", test_update_preferences(user_id)))
        
        chat_id = test_create_chat(user_id)
        results.append(("Create Chat", chat_id is not None))
        
        # Recommendations (may fail without full data)
        results.append(("User Recommendations", test_user_recommendations(user_id)))
    
    # CORS
    results.append(("CORS", test_cors()))
    
    # Queries (may fail without embeddings/services)
    results.append(("Query Songs", test_query_songs()))
    results.append(("Query Artist", test_query_artist()))
    results.append(("Query Albums", test_query_albums()))
    
    # Album recommendations
    results.append(("Album Recommendations", test_album_recommendations()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed < total:
        print("\n⚠️  Some tests failed. This may be expected if:")
        print("   - Neo4j is not running or has no data")
        print("   - Milvus is not running")
        print("   - Embedding service is not available")
        print("\nBasic API structure tests should pass regardless of data availability.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
