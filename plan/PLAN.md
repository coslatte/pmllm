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

milestones: - id: stage-1
name: Define purpose & requirements
tasks: - id: 1.1
title: Identify problem and users
output: "Problem statement, primary user personas, representative questions" - id: 1.2
title: Set measurable goals
output: "List of KPIs and acceptance criteria" - id: stage-2
name: Model selection & RAG design
tasks: - id: 2.1
title: Select embeddings, vector DB, and generator
criteria: ["embedding quality (semantic recall)", "vector-db latency & cost", "Gemma 3 API latency and cost", "deployment constraints"] - id: 2.2
title: Design retrieval & prompt pipeline (RAG)
steps: ["prepare document/KG ingestion and embedding pipeline", "define retrieval strategy (chunking, metadata filters, hybrid KG queries)", "design prompt templates and grounding format for Gemma 3", "validate with retrieval+generation experiments"] - id: stage-3
name: Core features
name: Core features
tasks: - id: 3.1
title: Content recommender
contract:
input: "user profile, engagement history, current query"
output: "ranked content list + explanation" - id: 3.2
title: Professional connector
contract:
input: "user profile, connection goals"
output: "ranked candidate list + matching rationale" - id: 3.3
title: Technical QA responder
contract:
input: "user question"
output: "answer + cited sources + confidence" - id: stage-4
name: API & evaluation
tasks: - id: 4.1
title: Build REST API
endpoints: ["/recommend", "/connect", "/ask"] - id: 4.2
title: Monitoring and evaluation pipeline
metrics: ["accuracy", "latency", "user_satisfaction"]

data_and_privacy:
data_sources: ["university catalogs", "course descriptions", "user profiles", "interaction logs"]
privacy: "Anonymize PII, follow institutional data policies, keep provenance metadata"
quality_checks: - "schema validation" - "deduplication" - "source trust scoring"

deliverables:
code_files: - {name: red_social_llm.py, purpose: "main model orchestration and business logic"} - {name: pi_server.py, purpose: "API server exposing endpoints"} - {name: data_processor.py, purpose: "ETL & dataset preparation"} - {name: evaluator.py, purpose: "evaluation metrics & monitoring"} - {name: requirements.txt, purpose: "Python dependencies"}
docs: - README.md - API_DOCUMENTATION.md - DATASET.md

agent_instructions:
priority_order: ["milestones.stage-1", "milestones.stage-2", "milestones.stage-3", "milestones.stage-4"]
behavior_guidelines: - "When unsure, return 'I don't know' and provide suggested data collection steps." - "Always include data provenance and confidence score in answers."
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
