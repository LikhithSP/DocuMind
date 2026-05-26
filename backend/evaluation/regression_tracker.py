"""Regression tracking for RAG pipeline versions.
TICKET-503:
Compares current eval results with baseline or previous runs and flags regressions.
"""
from typing import Dict, Any, List, Tuple
import json
from pathlib import Path
from backend.config import settings

class RegressionTracker:
    def __init__(self):
        self.history_file = Path(settings.BASE_DIR) / "data" / "eval" / "eval_history.json"

    def load_history(self) -> List[Dict[str, Any]]:
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_run(self, report: Dict[str, Any]):
        history = self.load_history()
        history.append(report)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    def check_regression(
        self, 
        current_report: Dict[str, Any], 
        drop_threshold: float = 0.05
    ) -> Tuple[bool, List[str]]:
        """Checks if key metrics dropped compared to previous run."""
        history = self.load_history()
        if not history:
            return False, ["No previous run to compare with. Current run registered as baseline."]

        previous = history[-1]
        prev_agg = previous.get("aggregate_scores", {})
        curr_agg = current_report.get("aggregate_scores", {})
        
        regressions = []
        for metric in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
            prev_val = prev_agg.get(metric, 0.0)
            curr_val = curr_agg.get(metric, 0.0)
            diff = prev_val - curr_val
            if diff > drop_threshold:
                regressions.append(
                    f"Regression detected in {metric}: dropped by {diff:.4f} (from {prev_val} to {curr_val})"
                )

        has_regression = len(regressions) > 0
        return has_regression, regressions

regression_tracker = RegressionTracker()
