# Assignment 4: NCU Regulation Knowledge Graph & QA System

This repository contains the implementation for Assignment 4: Building a RAG-based Knowledge Graph Question Answering System. The project accurately answers questions regarding NCU school regulations using Neo4j and a local LLM (`Qwen2.5-3B-Instruct`).

## 📊 Performance
- **Evaluation Score**: 14/20 (70.0% Accuracy)
- **Build Time**: ~7 seconds (well within the 300-second limit)
- **Inference Time**: ~10-15 minutes for all 20 questions (Local CPU inference)

## 🏗️ System Architecture & Key Features

### 1. KG Construction (`build_kg.py`)
- **Graph Schema**: Data is structured as `(Regulation)-[:HAS_ARTICLE]->(Article)-[:CONTAINS_RULE]->(Rule)`.
- **Deterministic Rule Extraction**: Rules are extracted from article text using a **regex-based heuristic parser** instead of LLM inference. This approach uses three strategies:
  - **Strategy A** – Numbered list splitting (e.g., `1. xxx 2. xxx`)
  - **Strategy B** – Conditional sentence pattern matching (`shall`, `must`, `may`, `If...`)
  - **Strategy C** – Full-article fallback for articles that don't match the above patterns
- **Why deterministic?** Sequential LLM extraction over 159 articles would take 8–13 minutes, exceeding the 300-second grader time-limit. The regex parser completes the same task in **< 10 seconds**.
- **Rule Classification**: Each extracted Rule is automatically labelled as `penalty`, `rights`, `exception`, or `requirement` based on keyword matching.

### 2. Dual-Strategy Retrieval (`query_system.py`)
- **Full-Text Indexing (Lucene)**: Uses Neo4j's `CALL db.index.fulltext.queryNodes` to search:
  1. **Article content** (`article_content_idx`) — prioritised first to preserve exact numeric facts (fees, credits, durations)
  2. **Rule nodes** (`rule_idx`) — used as supplementary context
- **Context Grouping**: Retrieved evidence is grouped by `[Regulation - Article]` before being passed to the LLM, reducing redundancy and improving readability.
- **Increased Context Window**: Article text is passed up to **1,000 characters** per article (previously 500) to avoid cutting off specific numbers and clauses.

### 3. Query Expansion / Synonym Mapping
To address the classic "Vocabulary Mismatch" problem in retrieval systems, the `_build_fulltext_query` function applies dynamic keyword expansion:

| Question phrasing | Expanded search terms |
|---|---|
| `bachelor's / degree` | `undergraduate`, `four`, `years` |
| `expelled / dismissed` | `withdraw` |
| `poor grades` | `failed`, `half` |
| `forgetting student ID` | `bringing`, `deducted` |

### 4. Prompt Engineering
The `generate_answer` prompt explicitly instructs the model:
- To **never say "I don't know"** if numeric facts are visible in the evidence
- To quote the **exact number or fact** found in the text
- To **cite the source** regulation and article number

### 5. Cross-Platform Hardening
- Added `sys.stdout.reconfigure(encoding='utf-8')` to prevent Windows `cp950` codec crashes when the LLM outputs special Unicode characters during `auto_test.py` evaluation.

---

## 💻 How to Run

### Prerequisites
- Python 3.11
- Neo4j (local Desktop or Docker)
- `ncu_regulations.db` (SQLite source file)

### 1. Start Neo4j
**Docker:**
```bash
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest
```
**Neo4j Desktop:** Start your local instance and ensure it is RUNNING.

### 2. Configure Environment
Create a `.env` file in the project root:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Build the Knowledge Graph
Reads `ncu_regulations.db` and populates Neo4j with Regulation, Article, and Rule nodes. Completes in ~7 seconds.
```bash
python build_kg.py
```

### 5. Interactive QA (Optional)
```bash
python query_system.py
```

### 6. Run Automated Evaluation
Runs 20 pre-defined questions with LLM-as-a-Judge scoring.
```bash
python auto_test.py
```

---

## 📂 File Structure

| File | Description |
|------|-------------|
| `build_kg.py` | Builds the Neo4j Knowledge Graph using deterministic rule extraction |
| `query_system.py` | Core RAG pipeline: retrieval, query expansion, and answer generation |
| `llm_loader.py` | Singleton-style caching loader for Transformers models |
| `auto_test.py` | Automated evaluation script (20 questions, LLM-as-a-Judge) |
| `requirements.txt` | Python package dependencies |
| `.gitignore` | Excludes `.venv`, model cache, `.env`, and database files |
