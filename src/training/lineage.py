"""
Model Lineage and Provenance Tracking for Clinical Trial Machine Learning Models.
Captures dataset hashes, code commits, hyperparameters, training metrics, and artifact URIs.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd

from ..config import config
from ..logger import get_logger

logger = get_logger(__name__)


class LineageTracker:
    """
    Model Lineage Tracker providing end-to-end traceability for regulatory compliance (FDA / EMA).
    """

    def __init__(self, lineage_dir: Optional[Path] = None):
        self.lineage_dir = lineage_dir or (config.model_dir / "lineage")
        self.lineage_dir.mkdir(parents=True, exist_ok=True)

    def calculate_data_hash(self, df: pd.DataFrame) -> str:
        """Calculate SHA256 hash of a dataframe for data provenance."""
        try:
            data_bytes = pd.util.hash_pandas_object(df, index=True).values.tobytes()
            return hashlib.sha256(data_bytes).hexdigest()
        except Exception:
            return hashlib.sha256(str(len(df)).encode()).hexdigest()

    def record_lineage(
        self,
        model_id: str,
        model_name: str,
        version: str,
        training_data: pd.DataFrame,
        hyperparameters: Dict[str, Any],
        metrics: Dict[str, float],
        artifact_uri: str,
        git_commit_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create and persist a complete lineage record.
        """
        data_hash = self.calculate_data_hash(training_data)

        lineage_record = {
            "model_id": model_id,
            "model_name": model_name,
            "version": version,
            "timestamp": pd.Timestamp.now().isoformat(),
            "data_provenance": {
                "num_rows": len(training_data),
                "num_features": len(training_data.columns),
                "data_sha256": data_hash,
                "columns": list(training_data.columns)
            },
            "code_provenance": {
                "git_commit": git_commit_hash or "HEAD",
                "framework": "scikit-learn / xgboost"
            },
            "hyperparameters": hyperparameters,
            "metrics": metrics,
            "artifact_uri": artifact_uri
        }

        record_path = self.lineage_dir / f"{model_name}_{version}_lineage.json"
        with open(record_path, "w") as f:
            json.dump(lineage_record, f, indent=2)

        logger.info(f"Model lineage recorded for {model_name}:{version} -> {record_path}")
        return lineage_record
