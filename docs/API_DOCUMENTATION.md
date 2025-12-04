# API Documentation

## Overview

The pmllm system provides a REST API for music recommendation and Q&A using Retrieval-Augmented Generation (RAG). The API is built with FastAPI and serves as the backend for the React frontend.

## Base URL

`http://localhost:8000`

## Frontend Connection (React)

The frontend is a React application that communicates with this API via HTTP requests.

### Connection Details

- **Protocol**: HTTP/1.1
- **Format**: JSON
- **Authentication**: Currently, the API uses `user_id` passed in requests for identification.
- **CORS**: The API should be configured to allow requests from the frontend origin (e.g., `http://localhost:3000`).

### Integration Guide for Frontend Developers

1.  **User Management**:
    -   On first visit, create a user via `POST /users`. Store the returned `id` (UUID) in local storage or state.
    -   Use this `user_id` for all subsequent requests.

2.  **Onboarding/Preferences**:
    -   Collect user preferences (genres, artists, instruments).
    -   Send to `POST /preferences` with the `user_id`.

3.  **Chat Interface**:
    -   Create a new chat session via `POST /chat`.
    -   Send user messages via `POST /message`.
    -   Poll or fetch message history via `GET /chat/{chat_id}/messages`.

4.  **Recommendations**:
    -   Call `POST /recommendations` with `user_id` to get personalized suggestions based on the stored profile.

## Endpoints

### User Management

#### Create User
`POST /users`

Creates a new user profile.

**Request Body:**
```json
{
  "username": "string"
}
```

**Response:**
```json
{
  "id": "uuid",
  "username": "string",
  "created_at": "datetime"
}
```

### Preferences

#### Update Preferences
`POST /preferences`

Updates user musical preferences and regenerates the vector profile.

**Request Body:**
```json
{
  "user_id": "uuid",
  "fav_genres": ["string"],
  "fav_artists": ["string"],
  "fav_instruments": ["string"]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Preferences updated and vector store synchronized",
  "profile_text": "User likes rock music..."
}
```

#### Get Profile Vector
`GET /get_profile_vector?user_id={user_id}`

Retrieves the vector embedding data for a user.

**Response:**
```json
{
  "id": "uuid",
  "vector": [...],
  "text": "User profile description..."
}
```

### Chat System

#### Create Chat
`POST /chat`

Starts a new chat session.

**Request Body:**
```json
{
  "user_id": "uuid"
}
```

**Response:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "created_at": "datetime"
}
```

#### Send Message
`POST /message`

Sends a message to the chat.

**Request Body:**
```json
{
  "chat_id": "uuid",
  "role": "user",
  "content": "string"
}
```

**Response:**
```json
{
  "id": "uuid",
  "chat_id": "uuid",
  "role": "user",
  "content": "string",
  "created_at": "datetime"
}
```

#### Get Chat Messages
`GET /chat/{chat_id}/messages`

Retrieves history for a specific chat.

**Response:**
```json
[
  {
    "id": "uuid",
    "chat_id": "uuid",
    "role": "string",
    "content": "string",
    "created_at": "datetime"
  }
]
```

### Recommendations

#### Get Recommendations
`POST /recommendations`

Generates music recommendations based on user profile and RAG.

**Request Parameters:**
- `user_id`: UUID (query parameter)

**Response:**
```json
{
  "recommendations": [
    {
      "item": "string",
      "score": 0.95,
      "reason": "string"
    }
  ]
}
```

### Conversational Queries

#### Ask the Assistant

`POST /query`

Sends a natural language question from the frontend, runs the RAG pipeline (Milvus + Neo4j + LLM), and returns the generated answer together with any structured matches detected for artist tags/genres.

**Request Body:**

```json
{
  "question": "tags de todos los artistas que son Jesus",
  "chat_id": "uuid (optional)",
  "top_k": 8,
  "debug": false
}
```

- `chat_id` is optional; when provided, both the user question and the assistant response are persisted in the chat history.
- `top_k` controls how many Milvus vectors are retrieved (min 1, max 20).
- `debug` (default `false`) enables a verbose payload that shows the constructed prompt, the retrieved vector hits, and the Cypher snippets used during retrieval—useful for UI instrumentation or QA.

**Response:**

```json
{
  "answer": "string",
  "context": ["retrieved snippet", "..."],
  "latency_ms": 123.4,
  "artist_tag_search": {
    "term": "jesus",
    "match_count": 3,
    "items": [
      {
        "node_id": "Artist:123",
        "artist_name": "Jesus Culture",
        "matched_terms": ["Jesus"],
        "tags": ["christian", "jesus"],
        "genres": ["worship"]
      }
    ]
  },
  "debug": {
    "prompt": "...full prompt...",
    "context_sections": ["context 1", "context 2"],
    "graph_context": ["Artist A HAS_TAG Tag B"],
    "vector_hits": [
      {"id": 123, "label": "Artist", "score": 0.12}
    ],
    "tag_term": "jesus"
  }
}
```

When no tag/genre intent is detected, `artist_tag_search` is omitted. The optional `debug` block appears only when `debug=true` in the request, and the `context` array mirrors the sections sent to the LLM prompt for transparency/debugging on the frontend.
