# Documentación de la API

## Resumen

El sistema pmllm proporciona una API REST para recomendaciones musicales y preguntas y respuestas utilizando Generación Aumentada por Recuperación (RAG). La API está construida con FastAPI y sirve como backend para el frontend en React.

## URL Base

`http://localhost:8000`

## Conexión con el Frontend (React)

El frontend es una aplicación React que se comunica con esta API a través de peticiones HTTP.

### Detalles de la Conexión

- **Protocolo**: HTTP/1.1
- **Formato**: JSON
- **Autenticación**: Actualmente, la API utiliza `user_id` pasado en las peticiones para la identificación.
- **CORS**: La API debe estar configurada para permitir peticiones desde el origen del frontend (ej. `http://localhost:3000`).

### Guía de Integración para Desarrolladores Frontend

1. **Gestión de Usuarios**:

    - En la primera visita, crear un usuario vía `POST /users`. Almacenar el `id` (UUID) devuelto en local storage o estado.
    - Usar este `user_id` para todas las peticiones subsiguientes.

2. **Onboarding/Preferencias**:

    - Recolectar preferencias del usuario (géneros, artistas, instrumentos).
    - Enviar a `POST /preferences` con el `user_id`.

3. **Interfaz de Chat**:

    - Crear una nueva sesión de chat vía `POST /chat`.
    - Enviar mensajes del usuario vía `POST /message`.
    - Consultar el historial de mensajes vía `GET /chat/{chat_id}/messages`.

4. **Recomendaciones**:
    - Llamar a `POST /recommendations` con `user_id` para obtener sugerencias personalizadas basadas en el perfil almacenado.

## Endpoints

### Gestión de Usuarios

#### Crear Usuario

`POST /users`

Crea un nuevo perfil de usuario.

**Cuerpo de la Petición:**

```json
{
  "username": "string"
}
```

**Respuesta:**

```json
{
  "id": "uuid",
  "username": "string",
  "created_at": "datetime"
}
```

### Preferencias

#### Actualizar Preferencias

`POST /preferences`

Actualiza las preferencias musicales del usuario y regenera el perfil vectorial.

**Cuerpo de la Petición:**

```json
{
  "user_id": "uuid",
  "fav_genres": ["string"],
  "fav_artists": ["string"],
  "fav_instruments": ["string"]
}
```

**Respuesta:**

```json
{
  "status": "success",
  "message": "Preferences updated and vector store synchronized",
  "profile_text": "User likes rock music..."
}
```

#### Obtener Vector de Perfil

`GET /get_profile_vector?user_id={user_id}`

Recupera los datos del embedding vectorial para un usuario.

**Respuesta:**

```json
{
  "id": "uuid",
  "vector": [...],
  "text": "User profile description..."
}
```

### Sistema de Chat

#### Crear Chat

`POST /chat`

Inicia una nueva sesión de chat.

**Cuerpo de la Petición:**

```json
{
  "user_id": "uuid"
}
```

**Respuesta:**

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "created_at": "datetime"
}
```

#### Enviar Mensaje

`POST /message`

Envía un mensaje al chat.

**Cuerpo de la Petición:**

```json
{
  "chat_id": "uuid",
  "role": "user",
  "content": "string"
}
```

**Respuesta:**

```json
{
  "id": "uuid",
  "chat_id": "uuid",
  "role": "user",
  "content": "string",
  "created_at": "datetime"
}
```

#### Obtener Mensajes del Chat

`GET /chat/{chat_id}/messages`

Recupera el historial para un chat específico.

**Respuesta:**

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

### Recomendaciones

#### Obtener Recomendaciones

`POST /recommendations`

Genera recomendaciones musicales basadas en el perfil del usuario y RAG.

**Parámetros de la Petición:**

- `user_id`: UUID (parámetro de consulta)

**Respuesta:**

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

### Consultas Conversacionales

#### Preguntar al Asistente

`POST /query`

Envía una pregunta en lenguaje natural desde el frontend, ejecuta el pipeline RAG (Milvus + Neo4j + LLM) y devuelve la respuesta generada junto con coincidencias estructuradas para tags o géneros de artistas.

**Cuerpo de la Petición:**

```json
{
  "question": "tags de todos los artistas que son Jesus",
  "chat_id": "uuid (opcional)",
  "top_k": 8,
  "debug": false
}
```

- `chat_id` es opcional; si se envía, la pregunta y la respuesta se almacenan en el historial del chat.
- `top_k` controla cuántos vectores se recuperan desde Milvus (mínimo 1, máximo 20).
- `debug` (por defecto `false`) activa un bloque detallado con el prompt construido, los hits vectoriales y las relaciones Cypher usadas durante la recuperación.

**Respuesta:**

```json
{
  "answer": "string",
  "context": ["fragmento recuperado", "..."],
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
    "prompt": "...prompt completo...",
    "context_sections": ["contexto 1", "contexto 2"],
    "graph_context": ["Artist A HAS_TAG Tag B"],
    "vector_hits": [
      {"id": 123, "label": "Artist", "score": 0.12}
    ],
    "tag_term": "jesus"
  }
}
```

Si no se detecta una intención vinculada a tags o géneros, `artist_tag_search` se omite. El bloque `debug` solo aparece cuando `debug=true` en la petición, y el arreglo `context` replica las secciones enviadas al prompt del LLM para facilitar la depuración desde el frontend.
