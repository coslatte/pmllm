# Knowledge-Graph + Fine-tuned LLM — Music Recommendation & Relationship Tool

This repository contains a project plan and supporting material for building a Knowledge-Graph-augmented, fine-tuned LLM focused on recommendations and relationship discovery across music-related subjects (courses, genres, artists, topics). The goal is to provide explainable recommendations, surface relationships between music topics, and enable contextual question answering for students, educators, and music professionals.

## Purpose

- Provide personalized recommendations (courses, pieces, playlists, resources) in music education and practice.
- Reveal relationships and paths between related music subjects (e.g., harmony -> counterpoint -> orchestration), genres, or artists using an explicit knowledge graph.
- Support technical and domain-level Q&A with cited sources and confidence scoring.

## High-level architecture

1. Knowledge Graph: structured entities (courses, topics, artists, genres, resources) and relationships (prerequisite_of, related_to, authored_by, exemplar_of).
2. LLM (base model + fine-tuning): a transformer model fine-tuned on domain-specific text (curricula, course descriptions, music theory texts, annotated QA pairs) and augmented by KG retrieval.
3. Orchestration layer: code that combines KG reasoning, LLM prompts, and ranking logic to produce recommendations and explanations.
4. API & UI: REST endpoints (e.g., `/recommend`, `/connect`, `/ask`) and simple UI or CLI to query the system.
5. Evaluator & Monitoring: automated tests and metrics for accuracy, latency, and user satisfaction.

See `plan/PLAN.md` for the structured, agent-friendly plan and task contracts.

## Data sources (examples)

- University/academy course catalogs
- Music theory textbooks and lecture notes
- Artist/genre taxonomies and discographies
- Curated Q&A pairs and annotated datasets for fine-tuning
- User profiles and interaction logs (privacy-preserving, anonymized)

## Deliverables (planned)

- `red_social_llm.py` — orchestration & model logic
- `pi_server.py` — REST API server exposing endpoints
- `data_processor.py` — ETL for datasets and KG ingestion
- `evaluator.py` — evaluation and monitoring code
- `plan/PLAN.md` — structured plan (machine- and human-friendly)
- `requirements.txt` — environment dependencies

## Agent usage notes

- Agents should parse the YAML metadata block in `plan/PLAN.md` first to discover priorities, milestones, and task contracts.
- Use the `agent_instructions` section in `plan/PLAN.md` for expected I/O formats (JSON task inputs and JSON outputs with `result`, `explanation`, `confidence`, and `sources`).
- Always include data provenance and a confidence score with answers. If uncertain, return a conservative fallback and recommend data-collection steps.

## Development / Next steps (suggested)

1. Create a minimal `requirements.txt` and Python virtual environment.
2. Add skeleton files for the deliverables above (stubs for API, processor, evaluator).
3. Prepare a small, representative dataset (courses, topics, and a few QA pairs) and a test harness for stage-1 acceptance tests.
4. Run model selection experiments (small models first) and record latency/accuracy tradeoffs.

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

If you'd like, I can scaffold the repository next: create `requirements.txt`, minimal Python stubs for the deliverables, and a tiny test harness that runs a few acceptance checks against the `plan/PLAN.md` contracts. Which of those would you like me to do now?
