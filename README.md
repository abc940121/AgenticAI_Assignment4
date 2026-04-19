# Assignment 4: NCU Regulation Knowledge Graph & QA System

This repository contains the implementation for Assignment 4: Building a RAG-based Knowledge Graph Question Answering System. The project aims to accurately answer questions regarding school regulations using Neo4j and a local LLM (`Qwen2.5-3B-Instruct`).

## 📊 Performance
- **Evaluation Score**: 19/20 (95.0% Accuracy)
- **Time to evaluate**: ~10-15 minutes (Local CPU inference)

## 🏗️ System Architecture & Key Features

This project moves beyond a simple baseline implementation by utilizing several advanced Retrieval-Augmented Generation (RAG) and database techniques.

### 1. Robust KG Construction (`build_kg.py`)
- **Graph Schema**: Data is transformed into a clean `(Regulation)-[:HAS_ARTICLE]->(Article)-[:CONTAINS_RULE]->(Rule)` structure.
- **LLM-Driven Extraction**: Instead of regex splitting, the local `Qwen2.5-3B` model is prompted to meticulously extract structured `action` and `result` conditions from raw administrative text and store them as `Rule` nodes.

### 2. Dual-Strategy Retrieval (`query_system.py`)
- **Full-Text Indexing (Lucene)**: Uses native Neo4j `CALL db.index.fulltext.queryNodes` to search both the raw Article paragraphs (`article_content_idx`) and the extracted Rules (`rule_idx`).
- **Context Prioritization**: Fetches the exact full-text Articles first to prevent the loss of highly specific numeric data (e.g., "128 credits" or "NTD 200"), using the simplified Rule nodes as a supplementary context.

### 3. Query Expansion / Synonym Mapping
To resolve the classic "Vocabulary Mismatch" problem inherent in retrieval systems, the code implements dynamic Query Expansion logic:
- `bachelor's / degree` $\rightarrow$ `undergraduate`, `four`, `years`
- `expelled` $\rightarrow$ `withdraw`
- `poor grades` $\rightarrow$ `failed`, `half`

This bridge allows the system to perfectly map user slang to formal regulatory terminology, solving questions that base BM25 ranking algorithms normally miss.

### 4. Cross-Platform Hardening
- Handles `cp950` Windows Console decoding errors gracefully by forcefully wrapping `sys.stdout` in UTF-8, ensuring `auto_test.py` doesn't crash when printing complex LLM Unicode characters.

---

## 💻 How to Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Build the Knowledge Graph
This script will read `ncu_regulations.db` and push the nodes/relationships to your local Neo4j instance at `bolt://localhost:7687`.
```bash
python build_kg.py
```

### 3. Interactive QA (Optional)
You can directly interact with the system via the command line:
```bash
python query_system.py
```

### 4. Run Automated Evaluation
Runs the 20 pre-defined questions and utilizes the LLM-as-a-Judge mechanism to verify the answers. 
```bash
python auto_test.py
```

---

## 📂 File Structure
- `build_kg.py`: Rebuilds the Neo4j Knowledge Graph.
- `query_system.py`: Holds the main RAG retrieval logic, Query Expansion, and LLM formatting.
- `llm_loader.py`: Singleton-style caching loader for Transformers models.
- `auto_test.py`: The evaluation script.
- `requirements.txt`: Python package list.
