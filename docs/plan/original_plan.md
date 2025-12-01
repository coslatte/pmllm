# Grafos de Conocimiento

> NOTE (project update, 2025-11-13, revised 2025-12-01): The project pivoted away from fine-tuning models and now adopts a Retrieval-Augmented Generation (RAG) approach using Gemma 3 (served via the model gateway container) as the generator. The repository and plans were updated to reflect embeddings + vector DB retrieval plus KG augmentation instead of on-prem fine-tuning.

Un Grafo de Conocimiento (Knowledge Graph) es una base de datos semántica que almacena información en forma de nodos (entidades) y aristas (relaciones), permitiendo representar conocimiento del mundo real de manera estructurada e interconectad. Las tareas de cada sem,ana deben ser hechas por los equipos son evaluativas.

## Etapa 1: Definición del Propósito y Objetivos

### Paso 1.1: Identificar el Problema a Resolver

    ¿Qué problema específico ayudará a resolver nuestro LLM?
    ¿Quiénes serán los usuarios principales?
    ¿Qué tipo de preguntas debería poder responder?

Ejemplo:
Problema: Estudiantes perdidos en elegir cursos
Usuarios: Estudiantes universitarios
Preguntas típicas: "¿Qué cursos necesito para machine learning?"

### Paso 1.2: Establecer Metas Claras

    Objetivos medibles y alcanzables
    Criterios de éxito definidos
    Límites y alcance del proyecto

Metas ejemplo:
Responder 80% de preguntas sobre cursos correctamente
Reducir tiempo de búsqueda de información en 50%
Proporcionar recomendaciones personalizadas

## Fase 2: Construcción del LLM

### Paso 2.1: Selección del Modelo Base

Objetivo: Elegir el modelo pre-entrenado que mejor se adapte a las necesidades de la red social.

Explicación detallada:
La selección del modelo base es crucial porque determina:
Capacidad de comprensión del lenguaje natural
Velocidad de inferencia para respuestas en tiempo real
Requisitos computacionales para despliegue

Criterios de selección:

Comparativa de modelos:
DistilBERT: 40% más rápido que BERT, 97% de su performance
BERT Base: Buen balance, ampliamente probado
RoBERTa: Mejor performance en algunas tareas, más pesado

### Paso 2.2: Diseño RAG y validación

#### Objetivo: Construir un pipeline de Retrieval-Augmented Generation que use embeddings, un vector store y Gemma 3 para generación

Explicación detallada:
En lugar de ajustar (fine-tune) un modelo, el enfoque RAG se apoya en recuperar contexto relevante (pasajes, documentos, hechos del KG) y pasar ese contexto a un generador potente (Gemma 3). Las ventajas incluyen menor gravedad de infraestructura, más fácil mantenimiento y la capacidad de actualizar conocimiento sin volver a entrenar modelos.

#### Pasos para el diseño RAG

- Preparar datos para ingestión (chunking, metadata, KG nodes) y pipeline de embeddings
- Seleccionar un modelo de embeddings y una solución de vector DB apropiada para latencia/costo
- Diseñar estrategias de recuperación (chunk size, overlap, metadata filters, hybrid KG queries)
- Crear templates de prompt que incluyan contexto recuperado, instrucciones claras y esquema de citación
- Validar con experimentos de retrieval+generation: medir recuperación (recall/precision), generación (fidelidad, citation accuracy) y latencia

## Fase 3: Funcionalidades Principales

### Paso 3.1: Asistente de Contenido

Objetivo: Recomendar publicaciones y contenido relevante basado en el perfil e intereses del usuario.

Explicación detallada:
Este sistema combina:
Perfil del usuario (habilidades, industria, intereses)
Comportamiento histórico (qué ha interactuado antes)
Contexto actual (qué está preguntando ahora)
Tendencias (qué es popular en la comunidad)

### Paso 3.2: Conector de Profesionales

Objetivo: Sugerir conexiones profesionales relevantes basado en compatibilidad.

Explicación detallada:
Va más allá de simples coincidencias de habilidades. Considera:

Factores de conexión:
Compatibilidad de habilidades (complementarias o similares)
Intereses profesionales alineados
Nivel de experiencia apropiado para mentoría/collaboración
Patrones de engagement (usuarios activos vs. ocasionales)

### Paso 3.3: Respondedor de Preguntas Técnicas

Objetivo: Proporcionar respuestas precisas y adaptadas al nivel del usuario.

Explicación detallada:
Un buen respondedor técnico debe:
Evaluar la complejidad de la pregunta
Adaptar el nivel de la respuesta
Proporcionar contexto y recursos adicionales
Ser honesto cuando no sabe algo

## Fase 4: Implementación y API

### Paso 4.1: Crear API REST

Objetivo: Exponer las funcionalidades del LLM através de una API robusta y escalable.

Explicación detallada:
La API debe ser:
RESTful para fácil integración
Documentada para desarrolladores
Segura con autenticación y rate limiting
Escalable para manejar múltiples usuario

### Paso 4.2: Sistema de Evaluación

Objetivo: Medir y monitorear el performance del LLM en producción.

Explicación detallada:
La evaluación continua es crucial para:
Detectar degradación en la calidad de respuestas
Identificar nuevos patrones de uso
Medir satisfacción del usuario
Guiar mejoras futuras

ENTREGABLES - Explicación Extendida

Código:
`red_social_llm.py`: El cerebro del sistema, contiene la lógica principal
`pi_server.py`: La interfaz con el mundo exterior
`data_processor.py`: Transforma datos crudos en formato usable
`evaluator.py`: Monitorea y mejora continuamente el sistema
`requirements.txt`: Garantiza consistencia en diferentes entornos

Documentación:
`README.md`: Guía completa desde cero hasta producción
`API_DOCUMENTATION.md`: Especificaciones técnicas para integradores
`DATASET.md`: Transparencia sobre datos y su procedencia
