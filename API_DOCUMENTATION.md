# API Documentation

## Overview

The pmllm system provides a REST API for music recommendation and Q&A using Retrieval-Augmented Generation (RAG) with Gemma 3.

## Planned Endpoints

### POST /query

Ask a question to the RAG system.

**Request:**

```json
{
  "question": "What artists are similar to Queen?",
  "k": 5
}
```

**Response:**

```json
{
  "answer": "Based on the retrieved context...",
  "sources": ["Artist:Queen", "Recording:Bohemian Rhapsody"],
  "confidence": 0.85
}
```

### POST /recommend

Get personalized music recommendations.

**Request:**

```json
{
  "user_profile": {...},
  "preferences": ["rock", "classic"]
}
```

**Response:**

```json
{
  "recommendations": [
    {
      "item": "Artist:Led Zeppelin",
      "explanation": "Similar guitar-driven rock",
      "confidence": 0.92
    }
  ]
}
```

### POST /connect

Find connections between music entities.

**Request:**

```json
{
  "entity1": "Artist:Queen",
  "entity2": "Genre:Rock"
}
```

**Response:**

```json
{
  "connections": [
    {
      "path": ["Artist:Queen", "HAS_GENRE", "Genre:Rock"],
      "strength": 0.95
    }
  ]
}
```

## Implementation Status

- CLI interface available via `main.py query`
- REST API not yet implemented
- Planned for Stage 3.2
