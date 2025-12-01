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
