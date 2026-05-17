import os
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.rag_pipeline import generate_answer
from retrieval.retriever import retrieve

TEST_CASES = [
    {"question": "What is the annual leave entitlement?",
     "ground_truth": "Full-time employees are entitled to 21 days of annual leave per year."},
    {"question": "What is the notice period for resignation?",
     "ground_truth": "Employees must give 30 days written notice before resigning."},
    {"question": "What is the work from home policy?",
     "ground_truth": "Employees may work from home up to 2 days per week with manager approval."},
    {"question": "How is overtime compensated?",
     "ground_truth": "Overtime is compensated at 1.5x the regular hourly rate."},
    {"question": "What is the probation period?",
     "ground_truth": "New employees serve a 3-month probation period."},
]

def run_evaluation():
    questions, answers, contexts, ground_truths = [], [], [], []
    for tc in TEST_CASES:
        q = tc["question"]
        print(f"Running: {q}")
        chunks, _ = retrieve(q, use_hyde=True)
        result = generate_answer(q, use_hyde=True, check_grounding=False)
        questions.append(q)
        answers.append(result["answer"])
        contexts.append([c["text"] for c in chunks])
        ground_truths.append(tc["ground_truth"])
    dataset = Dataset.from_dict({"question": questions, "answer": answers,
                                  "contexts": contexts, "ground_truth": ground_truths})
    llm = ChatOpenAI(model="gpt-4o", api_key=os.environ["OPENAI_API_KEY"])
    emb = OpenAIEmbeddings(model="text-embedding-3-small", api_key=os.environ["OPENAI_API_KEY"])
    results = evaluate(dataset=dataset,
                       metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                       llm=llm, embeddings=emb)
    df = results.to_pandas()
    print("\n===== RAGAS RESULTS =====")
    for m in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        print(f"  {m:<25} {df[m].mean():.3f}")
    df.to_json("evaluation/ragas_results.json", orient="records", indent=2)
    print("Saved to evaluation/ragas_results.json")

if __name__ == "__main__":
    run_evaluation()
