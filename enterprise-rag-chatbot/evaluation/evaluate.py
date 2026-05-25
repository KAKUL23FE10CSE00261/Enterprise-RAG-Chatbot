"""
evaluation/evaluate.py
Run RAGAS evaluation against the HR policy test suite.
Usage: python -m evaluation.evaluate
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.rag_pipeline import generate_answer   # ← now correctly calls generate_answer()
from retrieval.retriever import retrieve

# ── Test cases (extend with your own docs) ────────────────────────────────────
TEST_CASES = [
    {
        "question":    "What is the annual leave entitlement?",
        "ground_truth": "Full-time employees are entitled to 21 days of annual leave per year.",
    },
    {
        "question":    "What is the notice period for resignation?",
        "ground_truth": "Employees must give 30 days written notice before resigning.",
    },
    {
        "question":    "What is the work from home policy?",
        "ground_truth": "Employees may work from home up to 2 days per week with manager approval.",
    },
    {
        "question":    "How is overtime compensated?",
        "ground_truth": "Overtime is compensated at 1.5x the regular hourly rate.",
    },
    {
        "question":    "What is the probation period for new employees?",
        "ground_truth": "New employees serve a 3-month probation period.",
    },
    {
        "question":    "What is the health insurance coverage limit?",
        "ground_truth": "Coverage limit is Rs. 5,00,000 per family per year.",
    },
    {
        "question":    "When are performance reviews conducted?",
        "ground_truth": "Annual performance reviews are held in December.",
    },
]

# ── Runner ────────────────────────────────────────────────────────────────────

def run_evaluation(use_hybrid: bool = True, use_hyde: bool = True) -> dict:
    """
    Run RAGAS evaluation and return results as a dict.
    Also saves results to evaluation/ragas_results.json.
    """
    print(f"\n{'='*55}")
    print(f"  RAGAS Evaluation  |  hybrid={use_hybrid}  hyde={use_hyde}")
    print(f"{'='*55}")

    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("  ✗  OPENAI_API_KEY not set — RAGAS requires OpenAI for scoring.")
        print("     Set it with: export OPENAI_API_KEY=sk-...")
        return {}

    questions, answers, contexts, ground_truths = [], [], [], []

    for tc in TEST_CASES:
        q = tc["question"]
        print(f"  ▸ {q}")
        try:
            chunks, _ = retrieve(q, use_hyde=use_hyde, use_hybrid=use_hybrid)
            result    = generate_answer(q, use_hyde=use_hyde, use_hybrid=use_hybrid,
                                        check_grounding=False)
            questions.append(q)
            answers.append(result.get("answer", ""))
            contexts.append([c["text"] for c in chunks])
            ground_truths.append(tc["ground_truth"])
        except Exception as e:
            print(f"  ✗  Skipping '{q}': {e}")

    if not questions:
        print("  No questions evaluated successfully.")
        return {}

    dataset = Dataset.from_dict({
        "question":    questions,
        "answer":      answers,
        "contexts":    contexts,
        "ground_truth": ground_truths,
    })

    llm = ChatOpenAI(model="gpt-4o",               api_key=openai_key)
    emb = OpenAIEmbeddings(model="text-embedding-3-small", api_key=openai_key)

    results = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=llm,
        embeddings=emb,
    )

    df = results.to_pandas()

    print(f"\n{'─'*40}")
    print("  RAGAS Results")
    print(f"{'─'*40}")
    scores = {}
    for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        val = df[metric].mean()
        bar = "█" * int(val * 20)
        print(f"  {metric:<25} {val:.3f}  {bar}")
        scores[metric] = round(float(val), 3)
    print(f"{'─'*40}")

    out_dir  = os.path.join(os.path.dirname(__file__))
    out_path = os.path.join(out_dir, "ragas_results.json")
    df.to_json(out_path, orient="records", indent=2)
    print(f"\n  Saved → {out_path}\n")

    return scores


if __name__ == "__main__":
    run_evaluation()
