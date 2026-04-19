"""Quick smoke test - test 3 questions to verify retrieval works."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

from query_system import get_relevant_articles, generate_answer, generate_text

# Smoke test just retrieval (no LLM needed for this part)
questions = [
    "How many minutes late can a student be before they are barred from the exam?",
    "What is the fee for replacing a lost EasyCard student ID?",
    "What is the passing score for undergraduate students?",
]

for q in questions:
    print(f"\nQ: {q}")
    results = get_relevant_articles(q)
    print(f"  Found {len(results)} results:")
    for r in results[:3]:
        rtype = r.get("type", "?")
        if rtype == "article_context":
            print(f"    [{r['reg_name']} - {r['art_ref']}] (article) {r['result'][:120]}...")
        else:
            print(f"    [{r['reg_name']} - {r['art_ref']}] {r['action'][:60]} -> {r['result'][:60]}")
    print()
