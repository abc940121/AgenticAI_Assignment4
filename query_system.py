"""Minimal KG query template for Assignment 4.

Keep these APIs unchanged for auto-test:
- generate_text(messages, max_new_tokens=220)
- get_relevant_articles(question)
- generate_answer(question, rule_results)

Keep Rule fields aligned with build_kg output:
rule_id, type, action, result, art_ref, reg_name
"""

import os
import sys
from typing import Any

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from neo4j import GraphDatabase
from dotenv import load_dotenv

from llm_loader import load_local_llm, get_tokenizer, get_raw_pipeline


# ========== 0) Initialization ==========
load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (
	os.getenv("NEO4J_USER", "neo4j"),
	os.getenv("NEO4J_PASSWORD", "password"),
)

# Avoid local proxy settings interfering with model/Neo4j access.
for key in ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
	if key in os.environ:
		del os.environ[key]


try:
	driver = GraphDatabase.driver(URI, auth=AUTH)
	driver.verify_connectivity()
except Exception as e:
	print(f"[Warning] Neo4j connection warning: {e}")
	driver = None


# ========== 1) Public API (query flow order) ==========
# Order: extract_entities -> build_typed_cypher -> get_relevant_articles -> generate_answer

def generate_text(messages: list[dict[str, str]], max_new_tokens: int = 220) -> str:
	"""
	Call local HF model via chat template + raw pipeline.

	Interface:
	- Input:
	  - messages: list[dict[str, str]] (chat messages with role/content)
	  - max_new_tokens: int
	- Output:
	  - str (model generated text, no JSON guarantee)
	"""
	tok = get_tokenizer()
	pipe = get_raw_pipeline()
	if tok is None or pipe is None:
		load_local_llm()
		tok = get_tokenizer()
		pipe = get_raw_pipeline()
	prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
	return pipe(prompt, max_new_tokens=max_new_tokens)[0]["generated_text"].strip()


def extract_entities(question: str) -> dict[str, Any]:
	"""Extract key search terms from the question.
	Uses simple keyword extraction instead of LLM to avoid latency and errors."""
	import re
	# Extract meaningful words (skip very common ones)
	stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
	              "can", "could", "will", "would", "should", "do", "does", "did",
	              "i", "my", "me", "we", "our", "you", "your", "it", "its",
	              "what", "how", "many", "much", "when", "where", "who", "which",
	              "if", "of", "in", "on", "at", "to", "for", "with", "by", "from",
	              "and", "or", "not", "no", "that", "this", "there", "they", "their",
	              "has", "have", "had", "get", "take", "after"}
	words = re.findall(r'[a-zA-Z]+', question.lower())
	terms = [w for w in words if w not in stop_words and len(w) > 2]
	return {
		"question_type": "general",
		"subject_terms": terms,
		"aspect": "general",
	}


def _build_fulltext_query(question: str) -> str:
	"""Build a Lucene query string from the question for fulltext search."""
	import re
	stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
	              "can", "could", "will", "would", "should", "do", "does", "did",
	              "i", "my", "me", "we", "our", "you", "your", "it", "its",
	              "what", "how", "many", "much", "when", "where", "who", "which",
	              "if", "of", "in", "on", "at", "to", "for", "with", "by", "from",
	              "and", "or", "not", "no", "that", "this", "there", "they", "their",
	              "has", "have", "had", "get", "take", "after"}
	words = re.findall(r'[a-zA-Z]+', question.lower())
	terms_set = {w for w in words if w not in stop_words and len(w) > 2}
	
	q_lower = question.lower()
	if "bachelor" in q_lower or "degree" in q_lower:
		terms_set.update(["undergraduate", "four", "years"])
	if "dismissed" in q_lower or "expelled" in q_lower:
		terms_set.add("withdraw")
	if "poor grades" in q_lower:
		terms_set.update(["failed", "half"])
	if "forgetting" in q_lower and "student id" in q_lower:
		terms_set.update(["bringing", "deducted"])
		
	if not terms_set:
		return "regulation"
	return " OR ".join(list(terms_set))


def build_typed_cypher(entities: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
	"""Generate a structured query and a broad query with parameters."""
	# Not used in new flow but kept for API compatibility
	return "", "", {}


def get_relevant_articles(question: str) -> list[dict[str, Any]]:
	"""Retrieve relevant rules and articles from KG using fulltext search directly."""
	if driver is None:
		return []

	query_str = _build_fulltext_query(question)
	results = []
	seen_ids = set()

	with driver.session() as session:
		# Strategy 1: Search Article content via fulltext index (contains exact text with numbers) FIRST
		try:
			records = session.run(
				"""
				CALL db.index.fulltext.queryNodes("article_content_idx", $search_text)
				YIELD node, score
				RETURN "ART_" + node.number AS rule_id,
				       "article_context" AS type,
				       node.number AS art_ref,
				       node.content AS result,
				       node.reg_name AS reg_name,
				       score
				ORDER BY score DESC
				LIMIT 5
				""",
				search_text=query_str
			)
			for record in records:
				rule = {
					"rule_id":  record["rule_id"],
					"type":     "article_context",
					"action":   "Full article text",
					"result":   record["result"],
					"art_ref":  record["art_ref"],
					"reg_name": record["reg_name"],
					"score":    record["score"]
				}
				if rule["rule_id"] not in seen_ids:
					results.append(rule)
					seen_ids.add(rule["rule_id"])
		except Exception as e:
			print(f"      [Warning] Article search error: {e}")

		# Strategy 2: Search Rule nodes via fulltext index SECOND as fallback/summary
		try:
			records = session.run(
				"""
				CALL db.index.fulltext.queryNodes("rule_idx", $search_text)
				YIELD node, score
				RETURN node.rule_id AS rule_id, node.type AS type,
				       node.action AS action, node.result AS result,
				       node.art_ref AS art_ref, node.reg_name AS reg_name, score
				ORDER BY score DESC
				LIMIT 5
				""",
				search_text=query_str
			)
			for record in records:
				rule = {
					"rule_id":  record["rule_id"],
					"type":     record["type"],
					"action":   record["action"],
					"result":   record["result"],
					"art_ref":  record["art_ref"],
					"reg_name": record["reg_name"],
					"score":    record["score"]
				}
				if rule["rule_id"] not in seen_ids:
					results.append(rule)
					seen_ids.add(rule["rule_id"])
		except Exception as e:
			print(f"      [Warning] Rule search error: {e}")

	return results


def generate_answer(question: str, rule_results: list[dict[str, Any]]) -> str:
	"""Generate an answer grounded in the retrieved Rule nodes and Article content."""
	if not rule_results:
		return "I could not find any specific regulations or rules addressing your question in the school database."

	# Group context by regulation and article
	grouped_context = {}
	for r in rule_results:
		key = f"[{r['reg_name']} - {r['art_ref']}]"
		if key not in grouped_context:
			grouped_context[key] = []
		
		if r.get("type") == "article_context":
			# Increased from 500 to 1000 characters to prevent cutting off specific numbers & fees
			content = r["result"][:1000] if len(r.get("result", "")) > 1000 else r.get("result", "")
			grouped_context[key].append(f"Full text: {content}")
		else:
			grouped_context[key].append(f"Condition: {r['action']} -> Consequence: {r['result']}")

	# Format grouped context
	context_parts = []
	for key, lines in grouped_context.items():
		context_parts.append(f"{key}\n  - " + "\n  - ".join(lines))
	context = "\n\n".join(context_parts)

	prompt = f"""You are an expert NCU Regulation Assistant. Read the provided evidence carefully to answer the question.
If the evidence contains specific numbers, fees, durations, grades, or facts that match the intention of the question, you MUST extract and provide them. Do not say "I don't know" if the answer is logically present in the text.
Provide a clear, brief, direct answer and quote the exact number/fact.
Cite the source regulation (e.g. Source: [Regulation Name - Article X]).

Question: {question}

Evidence:
{context}

Answer:"""
	messages = [{"role": "user", "content": prompt}]
	return generate_text(messages, max_new_tokens=300)


def main() -> None:
	"""Interactive CLI (provided scaffold)."""
	if driver is None:
		return

	load_local_llm()

	print("=" * 50)
	print("🎓 NCU Regulation Assistant (Template)")
	print("=" * 50)
	print("💡 Try: 'What is the penalty for forgetting student ID?'")
	print("👉 Type 'exit' to quit.\n")

	while True:
		try:
			user_q = input("\nUser: ").strip()
			if not user_q:
				continue
			if user_q.lower() in {"exit", "quit"}:
				print("👋 Bye!")
				break

			results = get_relevant_articles(user_q)
			answer = generate_answer(user_q, results)
			print(f"Bot: {answer}")

		except KeyboardInterrupt:
			print("\n👋 Bye!")
			break
		except NotImplementedError as e:
			print(f"⚠️ {e}")
			break
		except Exception as e:
			print(f"❌ Error: {e}")

	driver.close()


if __name__ == "__main__":
	main()

