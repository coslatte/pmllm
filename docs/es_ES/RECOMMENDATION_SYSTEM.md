# Especificación del Sistema de Recomendaciones

## 1. Propósito

- Proporcionar recomendaciones explicables para estudiantes universitarios y profesionales mezclando relaciones de grafo y similitudes vectoriales.
- Extender los contratos existentes de curso/contenido/conexión para mostrar **planes de escucha de álbumes** derivados de los gustos declarados de un usuario (por ejemplo, artistas o géneros favoritos).

## 2. Entradas Requeridas

Cada invocación debe suministrar los siguientes bloques contextuales (típicamente obtenidos del orquestador):

- `user_profile`: hechos estáticos como rol, programa académico o artistas favoritos.
- `user_preferences`: gustos dinámicos ("prefiere rock progresivo", "ama álbumes conceptuales").
- `history`: interacciones previas (ítems vistos, sugerencias omitidas, álbumes guardados).
- `current_query`: la solicitud explícita ("Recomienda álbumes como el catálogo de Queen").
- `graph_context`: lista de nodos/relaciones de Neo4j ya recuperados (artista → lanzamiento, grupo_lanzamiento → etiqueta, etc.).
- `vector_hits`: coincidencias de Milvus con puntuaciones de similitud para contenido semánticamente cercano.

## 3. Esqueleto del Prompt

```text
Eres un asistente inteligente especializado en recomendaciones personalizadas para estudiantes universitarios y profesionales. Tu rol es generar recomendaciones para cursos, contenido educativo, conexiones profesionales y álbumes de música basados en un grafo de conocimiento (Neo4j) y similitudes semánticas (Milvus).

<Contexto>
- Perfil de Usuario: {user_profile}
- Preferencias: {user_preferences}
- Historial: {user_history}
- Consulta: {current_query}
- Contexto de Grafo: {graph_context}
- Coincidencias Vectoriales: {vector_hits}
</Contexto>

Instrucciones:
1. Personaliza las recomendaciones al perfil + historial.
2. Combina relaciones lógicas (Neo4j) con pistas semánticas (Milvus).
3. Cuando la consulta haga referencia a gustos musicales, ensambla un **plan de escucha de álbumes** de varios pasos. Cada paso puede citar un álbum, grupo de lanzamiento o lista de reproducción curada derivada de artistas similares.
4. Genera JSON válido coincidiendo exactamente con el esquema descrito a continuación.
5. Prefiere confianza ≥ 0.7. Si no es posible, devuelve "Recomendaciones insuficientes disponibles" y aconseja recopilar más datos.
```

## 4. Contrato de Salida JSON

```json
{
  "recommendations": [
    {
      "type": "course | content | connection | album_plan",
      "title": "Nombre descriptivo corto",
      "description": "Resumen de una oración del ítem o paso del álbum",
      "explanation": "Razonamiento rastreable que cita nodos de grafo o coincidencias vectoriales (por ejemplo, 'Comparte etiquetas de grupo_lanzamiento con Queen y aparece en vecinos de Milvus para glam rock').",
      "confidence": 0.0,
      "sources": ["neo4j:Artist(Queen)", "milvus:vector_id_123"],
      "suggested_actions": ["Escuchar en plataforma", "Conectar con curador"]
    }
  ],
  "general_summary": "Resaltar superposición entre las recomendaciones o pedir aclaración si la consulta fue ambigua."
}
```

- Siempre devuelve **5–10 entradas** cuando los datos sean suficientes. Mezcla tipos si el perfil de usuario abarca cursos/contenido/conexiones junto con planes de álbumes.
- Para planes de álbumes, trata cada recomendación como un paso secuenciado (por ejemplo, "Paso 1 – Revisitar antologías en vivo de Queen"), pero mantén el esquema idéntico etiquetando `type: "album_plan"` e incrustando el orden del paso dentro de `title` o `description`.

## 5. Ensamblaje del Plan de Álbum

1. **Selección de Semilla**: Comienza desde los nodos de artistas favoritos del usuario (por ejemplo, Queen) vía `MATCH (a:Artist {name})-[:PERFORMED_ON]->(r:Recording)`.
2. **Expansión de Grafo**: Atraviesa grupos de lanzamiento relacionados, géneros o centros de colaboración para encontrar álbumes adyacentes.
3. **Impulso Semántico**: Consulta Milvus para embeddings similares al historial del usuario o al artista semilla para captar opciones estilísticamente cercanas pero distantes en el grafo.
4. **Lógica de Curación**:
   - El orden de los pasos debe mostrar flujo narrativo (por ejemplo, "Clásicos fundamentales" → "Era experimental" → "Tributos modernos").
   - Cada paso debe citar al menos un hecho de grafo (etiqueta de género compartida, colaborador común) _y_ opcionalmente una puntuación de similitud ("coseno 0.83 a 'A Night at the Opera'").

## 6. Confianza y Procedencia

- Puntúa la confianza mezclando similitud coseno de Milvus (escalada a 0–1) con impulsos basados en reglas para saltos directos de Neo4j.
- `sources` debe nombrar explícitamente las entidades contribuyentes (por ejemplo, `neo4j:ReleaseGroup(OperaRockSaga)` o `milvus:rec_9876`).

## 7. Manejo de Fallos

- Si hay menos de tres ítems confiables disponibles, responde con `"recommendations": []` y establece `"general_summary": "Recomendaciones insuficientes disponibles. Recopile más preferencias."`
- Nunca inventes álbumes o cursos; confía únicamente en el contexto recuperado.

## 8. Notas de Implementación

- Mantén los prompts deterministas cuando sea posible (establece temperatura vía llamador; predeterminado 0.2 en configuración de Gemma 3).
- Respeta los contratos existentes delineados en `plan/PLAN.md` (recomendador de contenido, conector, respondedor QA). Los planes de álbumes extienden el contrato del **recomendador de contenido**.
- Todo el código de orquestación debe cargar esta especificación para validar salidas antes de devolverlas a los usuarios finales.

## 9. Criterios de Calidad y Salvaguardas

- **Mandato de personalización**: Ancla cada recomendación al `user_profile`, `user_preferences` e `history` proporcionados. Si faltan datos, hazlo evidente en el resumen.
- **Piso de confianza**: Prioriza ítems con puntuación ≥ 0.7; si no hay suficientes, devuelve "Recomendaciones insuficientes disponibles" y solicita más contexto.
- **Cobertura mínima**: Entrega entre 5 y 10 entradas cuando haya información adecuada y mezcla tipos si la consulta cubre múltiples intenciones.
- **Manejo de ambigüedad**: Si la consulta es vaga, solicita aclaraciones dentro de `general_summary` en lugar de improvisar resultados.
