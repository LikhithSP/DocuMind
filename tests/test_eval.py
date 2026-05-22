"""Unit test for RAGAS evaluation runner and regression tracker.
TICKET-502 / TICKET-503:
- Tests Faithfulness, Relevancy, Precision, and Recall formulas
- Tests regression comparison and alert detection
"""
import pytest
from backend.evaluation.ragas_eval import ragas_eval_runner
from backend.evaluation.regression_tracker import regression_tracker

def test_ragas_metrics_computation():
    answer = "Contractors receive 10 flex days per calendar year."
    contexts = [
        "Section 4.2 states contractors receive 10 flex days per calendar year instead of PTO.",
        "General company policies on leave."
    ]
    
    # Faithfulness
    f = ragas_eval_runner.compute_faithfulness(answer, contexts)
    assert f >= 0.8, f"Expected faithfulness >= 0.8, got {f}"

    # Answer Relevancy
    r = ragas_eval_runner.compute_answer_relevancy(
        question="How many flex days do contractors receive?",
        answer=answer
    )
    assert r >= 0.7, f"Expected relevancy >= 0.7, got {r}"

    # Context Precision
    p = ragas_eval_runner.compute_context_precision(
        expected_keywords=["contractors", "10 flex days"],
        retrieved_contexts=contexts
    )
    assert p >= 0.8

    # Context Recall
    c = ragas_eval_runner.compute_context_recall(
        expected_keywords=["contractors", "10 flex days"],
        retrieved_contexts=contexts
    )
    assert c == 1.0

def test_regression_detection():
    baseline_report = {
        "pipeline_version": "v1-baseline",
        "aggregate_scores": {
            "faithfulness": 0.90,
            "answer_relevancy": 0.88,
            "context_precision": 0.85,
            "context_recall": 0.82
        }
    }
    regression_tracker.save_run(baseline_report)

    # Simulated degraded run
    degraded_report = {
        "pipeline_version": "v2-regressed",
        "aggregate_scores": {
            "faithfulness": 0.75, # Dropped by 0.15 (> 0.05 threshold)
            "answer_relevancy": 0.87,
            "context_precision": 0.84,
            "context_recall": 0.81
        }
    }

    has_reg, notes = regression_tracker.check_regression(degraded_report, drop_threshold=0.05)
    assert has_reg is True
    assert any("faithfulness" in n for n in notes)
