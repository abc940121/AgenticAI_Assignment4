"""Run a specific question to debug the latest pipeline."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

from query_system import get_relevant_articles, generate_answer
from auto_test import evaluate_with_llm

questions = [
    {"id": 8, "q": "What is the fee for replacing a lost EasyCard student ID?", "ans": "200 NTD."},
    {"id": 11, "q": "What is the minimum total credits required for undergraduate graduation?", "ans": "128 credits."},
]

for item in questions:
    q = item["q"]
    ans = item["ans"]
    print(f"\n--- Q{item['id']}: {q} ---")
    results = get_relevant_articles(q)
    print(f"Retrieved {len(results)} items.")
    for i, r in enumerate(results):
        print(f"  {i+1}. {r.get('type')}: [{r.get('reg_name')} - {r.get('art_ref')}] Score: {r.get('score'):.2f}")
    
    bot_ans = generate_answer(q, results)
    print(f"\nBot answer:\n{bot_ans}")
    judge = evaluate_with_llm(q, ans, bot_ans)
    print(f"\nJudge: {judge}")
