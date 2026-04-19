import json
import sys
import os

from auto_test import ask_bot_no_metadata, evaluate_with_llm

def main():
    with open("test_data.json", "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    with open("eval_report.md", "w", encoding="utf-8") as f:
        f.write("# Final Evaluation Report\n\n")
        f.write("| ID | Question | Expected | Bot Answer | Result |\n")
        f.write("|----|----------|----------|------------|--------|\n")
        
        passed = 0
        for case in test_cases:
            qid = case["id"]
            question = case["question"]
            expected = case["answer"]
            
            print(f"Running Q{qid}...")
            bot_answer = ask_bot_no_metadata(question)
            verdict = evaluate_with_llm(question, expected, bot_answer)
            
            # replace newlines in bot_answer for table formatting
            flat_bot_answer = bot_answer.replace("\n", " ")
            f.write(f"| {qid} | {question} | {expected} | {flat_bot_answer} | {verdict} |\n")
            
            if "PASS" in verdict:
                passed += 1

        f.write(f"\n**Total Accuracy: {passed}/{len(test_cases)} ({(passed/len(test_cases))*100:.1f}%)**\n")

if __name__ == "__main__":
    main()
