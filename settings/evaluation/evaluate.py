"""
RAGAS evaluation script for the Enterprise RAG Chatbot.

Metrics measured:
  - faithfulness       : Is the answer grounded in the retrieved context?
  - answer_relevancy   : Does the answer address the question?
  - context_precision  : Are retrieved chunks relevant to the question?
  - context_recall     : Did retrieval capture all necessary information?

Run with: python evaluation/evaluate.py
"""

import os
import json
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.rag_pipeline import generate_answer
from retrieval.retriever import retrieve


# ── Test dataset ──────────────────────────────────────────────────────────────
# In a real project, create 20-30 Q&A pairs from your actual documents.
# ground_truth = the ideal answer you'd expect.

TEST_CASES = [
    {
        "question": "What is the annual leave entitlement for full-time employees?",
        "ground_truth": "Full-time employees are entitled to 21 days of annual leave per year.",
    },
    {
        "question": "What is the notice period for resignation?",
        "ground_truth": "Employees must give 30 days written notice before resigning.",
    },
    {
        "question": "What is the work from home policy?",
        "ground_truth": "Employees may work from home up to 2 days per week with manager approval.",
    },
    {
        "question": "How is overtime compensated?",
        "ground_truth": "Overtime is compensated at 1.5x the regular hourly rate for hours beyond 40 per week.",
    },
    {
        "question": "What is the probation period for new employees?",
        "ground_truth": "New employees serve a 3-month probation period.",
    },
]


# ── Run RAG on each test case ─────────────────────────────────────────────────

def build_eval_dataset() -> Dataset:
    questions, answers, contexts, ground_truths = [], [], [], []

    print("Running RAG on test cases…\n")
    for i, tc in enumerate(TEST_CASES):
        q = tc["question"]
        print(f"[{i+1}/{len(TEST_CASES)}] {q}")

        chunks, _ = retrieve(q, use_hyde=True)
        result = generate_answer(q, use_hyde=True, check_grounding=False)

        questions.append(q)
        answers.append(result["answer"])
        contexts.append([c["text"] for c in chunks])
        ground_truths.append(tc["ground_truth"])

    return Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })


# ── Evaluate ──────────────────────────────────────────────────────────────────

def run_evaluation():
    dataset = build_eval_dataset()

    llm = ChatOpenAI(model="gpt-4o", api_key=os.environ["OPENAI_API_KEY"])
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.environ["OPENAI_API_KEY"],
    )

    print("\nRunning RAGAS evaluation…")
    results = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=llm,
        embeddings=embeddings,
    )

    df = results.to_pandas()

    print("\n" + "=" * 60)
    print("RAGAS EVALUATION RESULTS")
    print("=" * 60)
    print(df[["question", "faithfulness", "answer_relevancy",
              "context_precision", "context_recall"]].to_string(index=False))

    print("\nAVERAGE SCORES:")
    for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        score = df[metric].mean()
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"  {metric:<22} {bar}  {score:.3f}")

    output_path = "evaluation/ragas_results.json"
    df.to_json(output_path, orient="records", indent=2)
    print(f"\nFull results saved to {output_path}")

    return df


if __name__ == "__main__":
    run_evaluation()