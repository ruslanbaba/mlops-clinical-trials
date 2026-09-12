"""
Statistical Data & Model Drift Detector for Clinical Trial ML Models.
Implements KS-test, Chi-Square, PSI (Population Stability Index), and Wasserstein Distance.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from ..logger import get_logger

logger = get_logger(__name__)


class DriftDetector:
    """
    Advanced statistical drift detector for tabular clinical trial data.
    """

    def __init__(self, psi_threshold: float = 0.25, ks_alpha: float = 0.05):
        """
        Initialize DriftDetector.

        Args:
            psi_threshold: PSI threshold for significant drift (>0.25 indicates action needed)
            ks_alpha: Significance level for Kolmogorov-Smirnov test (p-value threshold)
        """
        self.psi_threshold = psi_threshold
        self.ks_alpha = ks_alpha
        logger.info("DriftDetector initialized")

    def calculate_psi(
        self,
        reference: np.ndarray,
        current: np.ndarray,
        num_buckets: int = 10
    ) -> float:
        """
        Calculate Population Stability Index (PSI) between reference and current distribution.
        """
        try:
            # Handle empty or invalid arrays
            reference = np.asarray(reference).astype(float)
            current = np.asarray(current).astype(float)

            reference = reference[~np.isnan(reference)]
            current = current[~np.isnan(current)]

            if len(reference) == 0 or len(current) == 0:
                return 0.0

            # Generate bucket quantiles based on reference distribution
            quantiles = np.linspace(0, 100, num_buckets + 1)
            buckets = np.percentile(reference, quantiles)
            buckets[0] -= 1e-5
            buckets[-1] += 1e-5

            # Deduplicate buckets in case of constant features
            buckets = np.unique(buckets)
            if len(buckets) < 2:
                return 0.0

            ref_counts, _ = np.histogram(reference, bins=buckets)
            curr_counts, _ = np.histogram(current, bins=buckets)

            # Convert to percentages with smoothing
            ref_pct = (ref_counts + 1e-4) / (len(reference) + 1e-4 * len(ref_counts))
            curr_pct = (curr_counts + 1e-4) / (len(current) + 1e-4 * len(curr_counts))

            psi = np.sum((curr_pct - ref_pct) * np.log(curr_pct / ref_pct))
            return float(psi)
        except Exception as e:
            logger.warning(f"Error calculating PSI: {e}")
            return 0.0

    def detect_feature_drift(
        self,
        reference_df: pd.DataFrame,
        current_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Detect feature drift across all columns using statistical tests.
        """
        logger.info("Detecting feature drift across reference and current datasets")
        drift_results = {}
        drifted_columns = []
        overall_severity = "LOW"

        common_cols = [col for col in reference_df.columns if col in current_df.columns]

        for col in common_cols:
            ref_col = reference_df[col].dropna()
            curr_col = current_df[col].dropna()

            if len(ref_col) == 0 or len(curr_col) == 0:
                continue

            # Numerical feature drift check
            if pd.api.types.is_numeric_dtype(ref_col):
                ks_stat, p_value = stats.ks_2samp(ref_col, curr_col)
                wasserstein_dist = stats.wasserstein_distance(ref_col, curr_col)
                psi_score = self.calculate_psi(ref_col.values, curr_col.values)

                is_drifted = (p_value < self.ks_alpha) or (psi_score > self.psi_threshold)

                drift_results[col] = {
                    "type": "numerical",
                    "ks_stat": float(ks_stat),
                    "p_value": float(p_value),
                    "wasserstein_distance": float(wasserstein_dist),
                    "psi_score": float(psi_score),
                    "is_drifted": is_drifted
                }

                if is_drifted:
                    drifted_columns.append(col)

            # Categorical feature drift check
            else:
                ref_counts = ref_col.value_counts(normalize=True)
                curr_counts = curr_col.value_counts(normalize=True)

                all_cats = list(set(ref_counts.index).union(set(curr_counts.index)))
                ref_freqs = [ref_counts.get(cat, 1e-5) for cat in all_cats]
                curr_freqs = [curr_counts.get(cat, 1e-5) for cat in all_cats]

                chi2_stat, p_value = stats.chisquare(f_obs=curr_freqs, f_exp=ref_freqs)
                is_drifted = p_value < self.ks_alpha

                drift_results[col] = {
                    "type": "categorical",
                    "chi2_stat": float(chi2_stat),
                    "p_value": float(p_value),
                    "is_drifted": is_drifted
                }

                if is_drifted:
                    drifted_columns.append(col)

        drift_ratio = len(drifted_columns) / max(len(common_cols), 1)
        if drift_ratio > 0.4:
            overall_severity = "CRITICAL"
        elif drift_ratio > 0.2:
            overall_severity = "HIGH"
        elif drift_ratio > 0.05:
            overall_severity = "MEDIUM"

        summary = {
            "total_features": len(common_cols),
            "drifted_features_count": len(drifted_columns),
            "drifted_features": drifted_columns,
            "drift_ratio": float(drift_ratio),
            "severity": overall_severity,
            "requires_retraining": drift_ratio > 0.15,
            "details": drift_results
        }

        logger.info(f"Drift detection complete. Drifted features: {len(drifted_columns)}/{len(common_cols)}. Severity: {overall_severity}")
        return summary
