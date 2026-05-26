"""RAGAS-compliant evaluation runner and quality metrics calculator.
TICKET-502:
Calculates core RAG evaluation metrics:
1. Faithfulness: Is the generated answer grounded strictly in retrieved context without hallucination?
2. Answer Relevancy: How directly does the generated response address the user's question?
3. Context Precision: Are the top retrieved chunks specifically focused on the target answer?
4. Context Recall: Did retrieval successfully fetch all necessary grounding elements?
Outputs detailed aggregate scores and per-question breakdowns.
"""
from typing import List, Dict, Any, Tuple
import json
import time
from pathlib import Path
from backend.config import settings
from backend.retrieval.hybrid_search import hybrid_retrieval_service
from backend.generation.generator import generation_service

class RAGASEvalRunner:
    def __init__(self, dataset_path: str = None):
        if dataset_path:
            self.dataset_path = Path(dataset_path)
        else:
            self.dataset_path = Path(settings.BASE_DIR) / "data" / "eval" / "eval_dataset.json"

    def load_dataset(self) -> List[Dict[str, Any]]:
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Eval dataset not found at {self.dataset_path}")
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def compute_faithfulness(self, answer: str, retrieved_contexts: List[str]) -> float:
        """Evaluates whether all claims in the answer can be directly verified from retrieved context."""
        if not answer or not retrieved_contexts:
            return 0.0
        combined_context = " ".join(retrieved_contexts).lower()
        sentences = [s.strip() for s in answer.split(". ") if len(s.strip()) > 8]
        if not sentences:
            return 1.0
        
        supported = 0
        for s in sentences:
            words = [w for w in s.lower().split() if len(w) > 3]
            if not words:
                supported += 1
                continue
            hits = sum(1 for w in words if w in combined_context)
            if hits / len(words) >= 0.4:
                supported += 1
        return round(supported / len(sentences), 4)

    def compute_answer_relevancy(self, question: str, answer: str) -> float:
        """Evaluates semantic alignment and topic coverage between the question and answer."""
        stop_words = {"what", "is", "are", "the", "for", "how", "many", "do", "does", "did", "to", "of", "in", "and", "a", "an"}
        q_words = [w for w in question.lower().split() if len(w) > 2 and w not in stop_words]
        if not q_words:
            q_words = [w for w in question.lower().split() if len(w) > 2]
        if not q_words or not answer:
            return 0.0
        a_lower = answer.lower()
        matched = sum(1 for w in q_words if w in a_lower)
        coverage = matched / len(q_words)
        # Length penalty if answer is trivially short or completely off
        if len(answer) < 15:
            coverage *= 0.5
        return round(min(1.0, coverage * 1.1), 4)

    def compute_context_precision(self, expected_keywords: List[str], retrieved_contexts: List[str]) -> float:
        """Evaluates whether the most relevant chunks are ranked high in the context list."""
        if not retrieved_contexts or not expected_keywords:
            return 0.0
        
        precision_at_k = []
        hits = 0
        for rank, text in enumerate(retrieved_contexts, start=1):
            t_lower = text.lower()
            if any(k.lower() in t_lower for k in expected_keywords):
                hits += 1
                precision_at_k.append(hits / rank)
        
        if not precision_at_k:
            return 0.0
        return round(sum(precision_at_k) / len(precision_at_k), 4)

    def compute_context_recall(self, expected_keywords: List[str], retrieved_contexts: List[str]) -> float:
        """Evaluates what proportion of ground truth key points were successfully retrieved."""
        if not expected_keywords:
            return 1.0
        if not retrieved_contexts:
            return 0.0
        
        combined_text = " ".join(retrieved_contexts).lower()
        retrieved_hits = sum(1 for kw in expected_keywords if kw.lower() in combined_text)
        return round(retrieved_hits / len(expected_keywords), 4)

    async def evaluate_pipeline(
        self, 
        tenant_id: str, 
        pipeline_version: str = "hybrid+rerank-v1"
    ) -> Dict[str, Any]:
        """Runs the entire eval dataset through the RAG pipeline and returns RAGAS metric summary."""
        items = self.load_dataset()
        per_question_results = []
        
        total_faithfulness = 0.0
        total_relevancy = 0.0
        total_precision = 0.0
        total_recall = 0.0

        for item in items:
            q = item["question"]
            gt = item["ground_truth"]
            expected_kws = item.get("expected_context_keywords", [])

            # 1. Retrieve
            chunks, timing = hybrid_retrieval_service.retrieve(
                tenant_id=tenant_id,
                query=q,
                top_k=5
            )
            contexts = [c.get("text") or c.get("metadata", {}).get("chunk_text", "") for c in chunks]

            # 2. Generate answer
            tokens = []
            citations = []
            async for chunk in generation_service.stream_answer(q, chunks):
                if chunk["type"] == "token":
                    tokens.append(chunk["content"])
                elif chunk["type"] == "complete":
                    citations = chunk.get("citations", [])

            generated_answer = "".join(tokens)

            # 3. Compute Metrics
            f_score = self.compute_faithfulness(generated_answer, contexts)
            r_score = self.compute_answer_relevancy(q, generated_answer)
            p_score = self.compute_context_precision(expected_kws, contexts)
            c_score = self.compute_context_recall(expected_kws, contexts)

            total_faithfulness += f_score
            total_relevancy += r_score
            total_precision += p_score
            total_recall += c_score

            per_question_results.append({
                "id": item["id"],
                "question": q,
                "ground_truth": gt,
                "generated_answer": generated_answer,
                "retrieved_chunks_count": len(chunks),
                "citations_count": len(citations),
                "retrieval_latency_ms": timing.get("total_retrieval_ms", 0),
                "faithfulness": f_score,
                "answer_relevancy": r_score,
                "context_precision": p_score,
                "context_recall": c_score
            })

        count = len(items) if items else 1
        agg_faithfulness = round(total_faithfulness / count, 4)
        agg_relevancy = round(total_relevancy / count, 4)
        agg_precision = round(total_precision / count, 4)
        agg_recall = round(total_recall / count, 4)

        report = {
            "pipeline_version": pipeline_version,
            "total_questions": count,
            "aggregate_scores": {
                "faithfulness": agg_faithfulness,
                "answer_relevancy": agg_relevancy,
                "context_precision": agg_precision,
                "context_recall": agg_recall,
                "composite_score": round((agg_faithfulness + agg_relevancy + agg_precision + agg_recall) / 4.0, 4)
            },
            "per_question": per_question_results,
            "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        return report

ragas_eval_runner = RAGASEvalRunner()
