"""
Automated Retraining Orchestrator for MLOps Clinical Trials Platform.
Monitors drift signals, triggers automated model retraining, runs validation gates, and manages model promotion.
"""

from typing import Any, Dict, Optional, Tuple
import pandas as pd

from ..config import config
from ..logger import get_logger
from ..validation.gates import ValidationGates
from ..validation.drift_detector import DriftDetector
from .trainer import ModelTrainer
from .lineage import LineageTracker

logger = get_logger(__name__)


class AutomatedRetrainer:
    """
    Automated Retraining Pipeline with Safety Checks, Validation Gates, and Rollback.
    """

    def __init__(self):
        self.trainer = ModelTrainer()
        self.gates = ValidationGates()
        self.drift_detector = DriftDetector()
        self.lineage_tracker = LineageTracker()
        logger.info("AutomatedRetrainer initialized")

    def evaluate_and_retrain(
        self,
        model_name: str,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        target_column: str,
        champion_model: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Evaluate drift between reference and current data. If drift exceeds threshold,
        retrain model, run validation gates, and compare against champion model.
        """
        logger.info(f"Evaluating drift and potential retraining trigger for '{model_name}'")

        # Step 1: Detect Data & Feature Drift
        feature_cols = [c for c in current_data.columns if c != target_column]
        drift_summary = self.drift_detector.detect_feature_drift(
            reference_df=reference_data[feature_cols],
            current_df=current_data[feature_cols]
        )

        retraining_result = {
            "model_name": model_name,
            "drift_detected": drift_summary["requires_retraining"],
            "drift_summary": drift_summary,
            "retrained": False,
            "promoted": False,
            "validation_passed": False
        }

        if not drift_summary["requires_retraining"]:
            logger.info(f"Drift is within acceptable threshold for '{model_name}'. No retraining needed.")
            return retraining_result

        logger.info(f"Drift detected for '{model_name}' (Ratio: {drift_summary['drift_ratio']:.2f}). Triggering retraining pipeline.")

        try:
            # Step 2: Combine reference and recent current data for updated training
            combined_df = pd.concat([reference_data, current_data], ignore_index=True)
            X = combined_df[feature_cols]
            y = combined_df[target_column]

            # Train candidate model
            model_type = config.get_model_config(model_name).get("model_type", "xgboost")
            candidate_model, train_metrics = self.trainer.train(
                X=X,
                y=y,
                model_type=model_type,
                model_name=model_name
            )
            retraining_result["retrained"] = True

            # Step 3: Run Validation Gates on Candidate Model
            X_test = current_data[feature_cols]
            y_test = current_data[target_column]

            gate_results = self.gates.run_all_gates(
                model=candidate_model,
                X_test=X_test,
                y_test=y_test,
                model_metadata={"model_name": model_name, "stage": "candidate"},
                baseline_model=champion_model,
                reference_data=reference_data[feature_cols]
            )

            retraining_result["gate_results"] = gate_results
            retraining_result["validation_passed"] = gate_results.get("overall_status") == "PASSED"

            # Step 4: Promote model if validation gates pass
            if retraining_result["validation_passed"]:
                logger.info(f"Candidate model for '{model_name}' passed all validation gates! Promoting to production.")
                retraining_result["promoted"] = True

                # Record lineage
                self.lineage_tracker.record_lineage(
                    model_id=f"{model_name}-retrained",
                    model_name=model_name,
                    version="latest-retrained",
                    training_data=combined_df,
                    hyperparameters=config.get_model_config(model_name).get("hyperparameters", {}),
                    metrics=train_metrics,
                    artifact_uri=f"models/{model_name}_latest.joblib"
                )
            else:
                logger.warning(f"Candidate model for '{model_name}' failed validation gates. Rollback triggered. Retaining champion model.")

        except Exception as e:
            logger.error(f"Error during automated retraining: {e}")
            retraining_result["error"] = str(e)

        return retraining_result
