import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

from query_system import get_relevant_articles, generate_answer
from auto_test import evaluate_with_llm
import json

with open("test_data.json", "r", encoding="utf-8") as f:
    test_cases = json.load(f)

for case in test_cases:
    qid = case["id"]
    if qid in [14, 18]:
        q = case["question"]
        ans = case["answer"]
        print(f"\n--- Q{qid}: {q} ---")
        results = get_relevant_articles(q)
        print(f"Retrieved {len(results)} items.")
        for i, r in enumerate(results):
            print(f"  {i+1}. {r.get('type')}: [{r.get('reg_name')} - {r.get('art_ref')}]")
        
        bot_ans = generate_answer(q, results)
        print(f"\nBot answer:\n{bot_ans}")
