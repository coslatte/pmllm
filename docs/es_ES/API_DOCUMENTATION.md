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

#### Recomendaciones de Álbumes por Género

`POST /recommendations/albums`

Devuelve una lista determinista de álbumes (lanzamientos) calculada directamente desde Neo4j. Este endpoint expone cómo cada álbum se conecta con los géneros proporcionados, ideal para el componente del frontend que muestra "música que te podría gustar" sin invocar al LLM.

**Cuerpo de la Petición:**

```json
{
  "user_id": "uuid (opcional)",
  "include_genres": ["rock", "britpop"],
  "exclude_genres": ["metal"],
  "limit": 12,
  "min_genre_overlap": 2
}
```

- Si `include_genres` está vacío y se envía `user_id`, la API usa las preferencias almacenadas para ese usuario.
- `exclude_genres` filtra cualquier álbum conectado a esos géneros.
- `min_genre_overlap` define cuántos géneros favoritos debe compartir un álbum para ser incluido (por defecto 1).

**Respuesta:**

```json
{
  "generated_from": ["rock", "britpop"],
  "exclude_filters": ["metal"],
  "recommendations": [
    {
      "release_id": "Release:123",
      "release_name": "(What's the Story) Morning Glory?",
      "release_group_name": "Morning Glory",
      "artists": ["Oasis"],
      "matched_genres": ["rock", "britpop"],
      "tags": ["classic", "90s"],
      "connections": ["L_RELEASE_GENRE:rock", "L_RELEASE_GENRE:britpop"],
      "matched_count": 2,
      "score": 2.4
    }
  ]
}
```

Cada elemento incluye:

- `matched_genres`: géneros favoritos que originaron la recomendación.
- `connections`: tipos de relación en Neo4j que justifican la sugerencia (útil para tooltips o explicaciones).
- `score`: métrica simple basada en el solapamiento de géneros más señales de artistas/tags.

### Consultas Conversacionales

#### Preguntar al Asistente

`POST /query`

Envía una pregunta en lenguaje natural desde el frontend, ejecuta el pipeline RAG (Milvus + Neo4j + LLM) y devuelve la respuesta generada junto con coincidencias estructuradas. El endpoint soporta múltiples tipos de consultas incluyendo canciones, álbumes, artistas, colaboraciones y más.

**Cuerpo de la Petición:**

```json
{
  "question": "¿Cuáles son las canciones de Queen?",
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
  "query_type": "song|album|artist_detail|collaboration|similar|area|popular|tag|general",
  "artist_tag_search": {
    "term": "rock",
    "match_count": 3,
    "items": [
      {
        "node_id": "Artist:123",
        "artist_name": "Queen",
        "matched_terms": ["rock"],
        "tags": ["classic rock", "british"],
        "genres": ["rock"]
      }
    ]
  },
  "songs": [
    {
      "node_id": "Recording:456",
      "song_name": "Bohemian Rhapsody",
      "artist_name": "Queen",
      "album_name": "A Night at the Opera",
      "duration_ms": 354000,
      "duration_formatted": "5:54",
      "tags": ["classic", "opera"]
    }
  ],
  "albums": [
    {
      "node_id": "Release:789",
      "album_name": "A Night at the Opera",
      "artist_name": "Queen",
      "release_date": "1975-11-21",
      "track_count": 12,
      "tags": ["classic rock"]
    }
  ],
  "artists": [
    {
      "node_id": "Artist:123",
      "artist_name": "Queen",
      "area": "United Kingdom",
      "begin_date": "1970",
      "end_date": null,
      "artist_type": "Group",
      "tags": ["british", "legendary"],
      "genres": ["rock", "glam rock"],
      "album_count": 15,
      "song_count": 180
    }
  ],
  "collaborations": [
    {
      "artist1_name": "Queen",
      "artist2_name": "David Bowie",
      "recording_name": "Under Pressure",
      "recording_id": "Recording:999"
    }
  ],
  "debug": {
    "prompt": "...prompt completo...",
    "context_sections": ["contexto 1", "contexto 2"],
    "graph_context": ["Artist A HAS_TAG Tag B"],
    "vector_hits": [{"id": 123, "label": "Artist", "score": 0.12}],
    "tag_term": "rock"
  }
}
```

**Tipos de Consulta:**

El campo `query_type` indica qué tipo de consulta fue detectada:

| Tipo | Descripción | Ejemplos de Preguntas |
|------|-------------|----------------------|
| `song` | Búsqueda de canciones | "canciones de Queen", "temas de The Beatles" |
| `album` | Búsqueda de álbumes | "álbumes de Coldplay", "discos de rock" |
| `artist_detail` | Información de artista | "¿quién es Adele?", "información sobre Queen" |
| `collaboration` | Colaboraciones | "colaboraciones de Drake", "feat de Eminem" |
| `similar` | Artistas similares | "artistas similares a Metallica" |
| `area` | Artistas por ubicación | "artistas de México", "músicos de España" |
| `popular` | Populares/Top | "artistas más populares", "mejores bandas" |
| `tag` | Búsqueda por tag/género | "artistas de rock", "músicos de jazz" |
| `general` | Pregunta general | Cualquier otra pregunta |

**Arrays de Respuesta:**

- `songs`: Se llena al buscar canciones/grabaciones
- `albums`: Se llena al buscar álbumes/lanzamientos
- `artists`: Se llena para detalles de artista, artistas similares, consultas por área o populares
- `collaborations`: Se llena para consultas de colaboraciones
- `artist_tag_search`: Se llena para búsquedas de artistas por tag/género

Cuando no se encuentran coincidencias para una categoría, el array correspondiente está vacío. El bloque `debug` solo aparece cuando `debug=true` en la petición.

Si no se detecta una intención vinculada a tags o géneros, `artist_tag_search` se omite. El bloque `debug` solo aparece cuando `debug=true` en la petición, y el arreglo `context` replica las secciones enviadas al prompt del LLM para facilitar la depuración desde el frontend.
