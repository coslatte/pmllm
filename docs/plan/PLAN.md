---
title: Knowledge Graph & LLM Project Plan
version: 1.0
format: agent-friendly
summary: |
  Structured plan to build a Knowledge-Graph-backed LLM for a professional social
  network. This file contains a machine-readable YAML metadata block followed by
  concise, human-friendly sections. Agents should read the YAML block first for
  priorities, contracts, and tasks.
---

## Machine-readable plan (YAML)

metadata:
purpose: "Help university students and professionals find courses, content, and connections using an LLM augmented with a knowledge graph."
primary_users: - "university_students" - "professionals" - "platform_developers"
scope:
include: - "course recommendation" - "professional connection suggestions" - "technical question answering"
exclude: - "direct financial or medical advice"
success_criteria: - ">=80% accuracy on curated Q&A test set" - "50% reduction in average information-search time" - "recommendations are personalized and explainable"

milestones:

- id: stage-1
  name: Data Preparation (Completed)
  tasks:

  - id: 1.1
    title: Extract and Normalize Data
    status: done
    output: "CSV files extracted from tarballs (Ok)"
  - id: 1.2
    title: Generate Headers and Schemas
    status: done
    output: "Headers created for table joining and data construction (Ok)"

- id: stage-2
  name: Database Construction (Vector & Graph)
  tasks:

  - id: 2.1
    title: Knowledge Graph Construction (Neo4j)
    description: "Import structured data to handle precise relationship queries (e.g., Artist-Release connections)."
    status: completed
    progress: "Metadata verification complete: 7 node types + 9 relationship types validated. Graph architecture confirmed with 100% schema integrity. Neo4j import pipeline ready for comprehensive music relationship data."
  - id: 2.2
    title: Vector Database Construction
    description: "Generate embeddings using 'text-embedding-embeddinggemma-300m-qat' (Gemma Embedding 300M, Q4_0, 229.09 MB) and index in Milvus."
    status: pending

- id: stage-3
  name: RAG Consolidation
  tasks:
  - id: 3.1
    title: Build RAG Pipeline
    description: "Integrate Vector Search (Milvus) and Graph Query (Neo4j) to provide context to Gemma 3 (google/gemma-3-1b, Q4_0, 720.50 MB)."
  - id: 3.2
    title: API & Interface
    description: "Expose the consolidated RAG via REST API."

data_and_privacy:
data_sources: ["university catalogs", "course descriptions", "user profiles", "interaction logs"]
privacy: "Anonymize PII, follow institutional data policies, keep provenance metadata"
quality_checks: - "schema validation" - "deduplication" - "source trust scoring"

deliverables:
code_files: - {name: main.py, purpose: "tabular tools and Neo4j import orchestration"} - {name: db/neo4j/neo4j_importer.py, purpose: "helpers to run Neo4j bulk import and verification queries"} - {name: utils/files_manager/csv_helper.py, purpose: "MusicBrainz data preparation for Neo4j"} - {name: db/vector/rag_pipeline.py, purpose: "RAG orchestration with Gemma 3 LLM"} - {name: db/vector/milvus_store.py, purpose: "Milvus connection and collection management"} - {name: requirements.txt, purpose: "Python dependencies"}
docs: - README.md - API_DOCUMENTATION.md - DATASET.md - docs/CHANGELOG.md - docs/CHANGELOG_es.md

agent_instructions:
priority_order: ["milestones.stage-1", "milestones.stage-2", "milestones.stage-3", "milestones.stage-4"]
behavior_guidelines: - "When unsure, return 'I don't know' and provide suggested data collection steps." - "Always include data provenance and confidence score in answers." - "Document all changes made by agents in \`docs/CHANGELOG.md\` and \`docs/CHANGELOG_es.md\` simultaneously when appropriate." - "Use 'uv run python' instead of 'python' for all Python command executions."
task_format: - input_schema: "JSON object matching the task contract" - expected_output: "JSON with 'result', 'explanation', 'confidence', 'sources'"
error_handling: - "If an external data source is missing, flag data dependency and fall back to conservative default."

next_steps: - "Create small dataset and test harness for stage-1 acceptance tests" - "Prototype model selection experiments and record latency/accuracy"

## Human-friendly summary

This document defines a concise plan to build a Knowledge-Graph-enabled LLM for educational and professional recommendation tasks. It aims to be both machine-parsable (YAML metadata) and readable by humans. Agents should follow the 'agent_instructions' section for expected I/O and priorities.

### Key contracts (short)

- Content recommender: input = {user_profile, history, query} -> output = {items[], explanations[], confidence}
- Connector: input = {user_profile, goals} -> output = {candidates[], matching_reasons[], confidence}
- QA responder: input = {question} -> output = {answer, sources[], confidence}

### Minimal acceptance criteria

- Test set Q&A accuracy >= 80%
- API endpoints respond within acceptable latency (define per infra)
- Recommendations must include an explainability field

## Files referenced

- `plan/PLAN.md` (this file): structured plan for agents and humans
- Implementation files (see deliverables)

End of plan.
