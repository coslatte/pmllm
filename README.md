# Knowledge-Graph + Retrieval-Augmented Generation (RAG) with Gemma 3 — Music Recommendation & Relationship Tool

This repository contains a project plan and supporting material for building a Knowledge-Graph-augmented Retrieval-Augmented Generation (RAG) system that uses Gemma 3 as the LLM for generation. We no longer pursue model fine-tuning. Instead, the system uses embeddings + a vector store for retrieval and Gemma 3 for high-quality, instruction-following generation over retrieved context. The goal remains: explainable recommendations, relationship discovery across music-related subjects (courses, genres, artists, topics), and contextual question answering for students, educators, and music professionals.

## Purpose

- Provide personalized recommendations (courses, pieces, playlists, resources) in music education and practice.
- Reveal relationships and paths between related music subjects (e.g., harmony -> counterpoint -> orchestration), genres, or artists using an explicit knowledge graph.
- Support technical and domain-level Q&A with cited sources and confidence scoring.

## High-level architecture (RAG + KG)

1. Document & KG ingestion: convert documents and KG nodes into embeddings and index them in a vector store (and keep KG for structured queries).
2. Embeddings & Vector Store: an embeddings model (cloud or open-source) creates vectors for documents; a vector DB (e.g., Pinecone, Weaviate, Milvus, or a local FAISS store) provides nearest-neighbor retrieval.
3. Retriever: given a user query, retrieve relevant passages/documents and KG facts from the vector store and KG.
4. Generator (Gemma 3): compose a prompt that includes retrieved context and use Gemma 3 (via API) to generate answers, recommendations, and explanations. No fine-tuning required — rely on prompt engineering and retrieval context.
5. Orchestration & business logic: combine KG reasoning, retrieved passages, prompt templates, and post-processing (citations, confidence scoring, ranking) to produce final outputs.
6. API & UI: REST endpoints (e.g., `/recommend`, `/connect`, `/ask`) and simple UI or CLI to query the system.
7. Evaluator & Monitoring: automated tests and metrics for accuracy, retrieval quality (recall/precision), latency, and user satisfaction.

See `plan/PLAN.md` for the structured, agent-friendly plan and task contracts.

## Data sources (examples)

- University/academy course catalogs
- Music theory textbooks and lecture notes
- Artist/genre taxonomies and discographies
- Curated Q&A pairs and annotated datasets for validation and retrieval testing
- User profiles and interaction logs (privacy-preserving, anonymized)

## Deliverables (planned)

- `red_social_llm.py` — orchestration & RAG logic (retriever + prompt construction + Gemma 3 calls + post-processing)
- `pi_server.py` — REST API server exposing endpoints
- `data_processor.py` — ETL for datasets, embeddings creation, and KG ingestion
- `evaluator.py` — evaluation and monitoring code (retrieval and generation metrics)
- `plan/PLAN.md` — structured plan (machine- and human-friendly)
- `requirements.txt` — environment dependencies and notes about client libraries to call Gemma 3 and vector DB

## Agent usage notes

- Agents should parse the YAML metadata block in `plan/PLAN.md` first to discover priorities, milestones, and task contracts.
- Use the `agent_instructions` section in `plan/PLAN.md` for expected I/O formats (JSON task inputs and JSON outputs with `result`, `explanation`, `confidence`, and `sources`).
- Always include data provenance and a confidence score with answers. When answering, include which retrieved passages or KG facts were used and link to their identifiers.

Note: the project now uses a RAG approach with Gemma 3. Do not add or expect fine-tuning scripts or fine-tuned model artifacts in the repo unless a future decision reintroduces fine-tuning.

## Development / Next steps (suggested)

1. Create a minimal `requirements.txt` and Python virtual environment.
2. Add skeleton files for the deliverables above (stubs for API, processor, evaluator) and include a `scripts/` helper to build embeddings and populate the vector store.
3. Prepare a small, representative dataset (courses, topics, and a few QA pairs) and a test harness for stage-1 acceptance tests. Add retrieval tests (can the system find the passage that contains the answer?) and generation tests (does Gemma 3 produce the expected format when given retrieved context?).
4. Select an embeddings provider and a vector DB. Document API keys and configuration expectations in `README.md` (do not commit secrets).

Example (PowerShell) commands to start a local dev env and run ingestion (replace placeholders):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# run ingestion script that creates embeddings and populates the vector DB
python scripts/ingest.py --data data/ --vector-db local_faiss
```

Example (PowerShell) commands to start a local dev env:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

(If you don't have `requirements.txt` yet, create it with the minimal dependencies you plan to use.)

## Contributing

- Follow the milestones in `plan/PLAN.md`. Open issues for new tasks and attach small, testable PRs.
- Document any external datasets in `DATASET.md` and keep provenance metadata with ingested items.

## License

Choose a license appropriate for your project (e.g., MIT, Apache-2.0) and add a `LICENSE` file.

---

If you'd like, I can scaffold the repository next: create `requirements.txt`, minimal Python stubs for the deliverables, and a tiny test harness that runs a few acceptance checks against the `plan/PLAN.md` contracts. I can also add example scripts to create embeddings and populate a local FAISS vector store as a starting point. Which of those would you like me to do now?
