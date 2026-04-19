"""Minimal KG builder template for Assignment 4.

Keep this contract unchanged:
- Graph: (Regulation)-[:HAS_ARTICLE]->(Article)-[:CONTAINS_RULE]->(Rule)
- Article: number, content, reg_name, category
- Rule: rule_id, type, action, result, art_ref, reg_name
- Fulltext indexes: article_content_idx, rule_idx
- SQLite file: ncu_regulations.db
"""

import os
import sqlite3
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase

from llm_loader import load_local_llm, get_tokenizer, get_raw_pipeline


# ========== 0) Initialization ==========
load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (
    os.getenv("NEO4J_USER", "neo4j"),
    os.getenv("NEO4J_PASSWORD", "password"),
)


def extract_entities(article_number: str, reg_name: str, content: str) -> dict[str, Any]:
    """Extract structured rules from article content using the local LLM."""
    prompt = f"""
Extract internal regulatory rules from the following academic regulation article.
A "Rule" must contain an 'action' (what is done/happened) and a 'result' (the consequence/penalty/status).

Article Info: {reg_name} - {article_number}
Content: {content}

Return the rules in valid JSON format only:
{{
  "rules": [
    {{
      "type": "requirement|penalty|rights|exception",
      "action": "short description of the condition or trigger",
      "result": "short description of the consequence",
      "art_ref": "{article_number}"
    }}
  ]
}}
"""
    messages = [{"role": "user", "content": prompt}]
    
    # Simple wrapper for generate_text in build_kg (reusing query_system patterns)
    tok = get_tokenizer()
    pipe = get_raw_pipeline()
    chat_prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    raw_output = pipe(chat_prompt, max_new_tokens=400)[0]["generated_text"].strip()
    
    # Try to extract JSON from the output
    import json
    try:
        # Basic cleanup in case of markdown blocks
        if "```json" in raw_output:
            raw_output = raw_output.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_output:
             raw_output = raw_output.split("```")[1].split("```")[0].strip()
        
        data = json.loads(raw_output)
        return data
    except Exception as e:
        print(f"      [Warning] Failed to parse LLM output for {article_number}: {e}")
        return {"rules": []}


def build_fallback_rules(article_number: str, content: str) -> list[dict[str, str]]:
    """TODO(student, optional): add deterministic fallback rules."""
    return []


# SQLite tables used:
# - regulations(reg_id, name, category)
# - articles(reg_id, article_number, content)


def build_graph() -> None:
    """Build KG from SQLite into Neo4j using the fixed assignment schema."""
    sql_conn = sqlite3.connect("ncu_regulations.db")
    cursor = sql_conn.cursor()
    driver = GraphDatabase.driver(URI, auth=AUTH)

    # Optional: warm up local LLM
    load_local_llm()

    with driver.session() as session:
        # Fixed strategy: clear existing graph data before rebuilding.
        session.run("MATCH (n) DETACH DELETE n")

        # 1) Read regulations and create Regulation nodes.
        cursor.execute("SELECT reg_id, name, category FROM regulations")
        regulations = cursor.fetchall()
        reg_map: dict[int, tuple[str, str]] = {}

        for reg_id, name, category in regulations:
            reg_map[reg_id] = (name, category)
            session.run(
                "MERGE (r:Regulation {id:$rid}) SET r.name=$name, r.category=$cat",
                rid=reg_id,
                name=name,
                cat=category,
            )

        # 2) Read articles and create Article + HAS_ARTICLE.
        cursor.execute("SELECT reg_id, article_number, content FROM articles")
        articles = cursor.fetchall()

        for reg_id, article_number, content in articles:
            reg_name, reg_category = reg_map.get(reg_id, ("Unknown", "Unknown"))
            session.run(
                """
                MATCH (r:Regulation {id: $rid})
                CREATE (a:Article {
                    number:   $num,
                    content:  $content,
                    reg_name: $reg_name,
                    category: $reg_category
                })
                MERGE (r)-[:HAS_ARTICLE]->(a)
                """,
                rid=reg_id,
                num=article_number,
                content=content,
                reg_name=reg_name,
                reg_category=reg_category,
            )

        # 3) Create full-text index on Article content.
        session.run(
            """
            CREATE FULLTEXT INDEX article_content_idx IF NOT EXISTS
            FOR (a:Article) ON EACH [a.content]
            """
        )

        # 4) Extract Rules and link via CONTAINS_RULE.
        print(f"[Build] Starting Rule Extraction for {len(articles)} articles...")
        rule_counter = 0
        for reg_id, article_number, content in articles:
            reg_name, _ = reg_map.get(reg_id, ("Unknown", "Unknown"))
            
            # Step 1: Extract structured rules
            extracted = extract_entities(article_number, reg_name, content)
            
            # Step 2: Create nodes and relationships
            for rule in extracted.get("rules", []):
                action = rule.get("action")
                result = rule.get("result")
                
                # Basic validation
                if not action or not result:
                    continue
                
                rule_id = f"R{rule_counter:04d}"
                session.run(
                    """
                    MATCH (a:Article {number: $art_num, reg_name: $reg_name})
                    CREATE (r:Rule {
                        rule_id:  $rule_id,
                        type:     $type,
                        action:   $action,
                        result:   $result,
                        art_ref:  $art_num,
                        reg_name: $reg_name
                    })
                    MERGE (a)-[:CONTAINS_RULE]->(r)
                    """,
                    art_num=article_number,
                    reg_name=reg_name,
                    rule_id=rule_id,
                    type=rule.get("type", "general"),
                    action=action,
                    result=result
                )
                rule_counter += 1
            
            if rule_counter % 20 == 0 and rule_counter > 0:
                print(f"   Processed {rule_counter} rules...")

        # 5) Create full-text index on Rule fields.
        session.run(
            """
            CREATE FULLTEXT INDEX rule_idx IF NOT EXISTS
            FOR (r:Rule) ON EACH [r.action, r.result]
            """
        )

        # 5) Coverage audit (provided scaffold).
        coverage = session.run(
            """
            MATCH (a:Article)
            OPTIONAL MATCH (a)-[:CONTAINS_RULE]->(r:Rule)
            WITH a, count(r) AS rule_count
            RETURN count(a) AS total_articles,
                   sum(CASE WHEN rule_count > 0 THEN 1 ELSE 0 END) AS covered_articles,
                   sum(CASE WHEN rule_count = 0 THEN 1 ELSE 0 END) AS uncovered_articles
            """
        ).single()

        total_articles = int((coverage or {}).get("total_articles", 0) or 0)
        covered_articles = int((coverage or {}).get("covered_articles", 0) or 0)
        uncovered_articles = int((coverage or {}).get("uncovered_articles", 0) or 0)

        print(
            f"[Coverage] covered={covered_articles}/{total_articles}, "
            f"uncovered={uncovered_articles}"
        )

    driver.close()
    sql_conn.close()


if __name__ == "__main__":
    build_graph()
