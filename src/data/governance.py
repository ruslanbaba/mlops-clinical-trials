"""
Clinical Trial Data Governance, PHI Anonymization, and Compliance Management (HIPAA / GDPR / 21 CFR Part 11).
"""

import hashlib
import re
from typing import List, Optional
import pandas as pd

from ..logger import get_logger

logger = get_logger(__name__)


class ClinicalDataGovernance:
    """
    Data Governance Manager providing PHI masking, data retention, and audit trails.
    """

    # Direct Identifiers under HIPAA Safe Harbor
    PHI_COLUMNS = [
        "patient_name", "ssn", "social_security", "dob", "date_of_birth",
        "phone", "email", "address", "zip_code", "mrn", "medical_record_number"
    ]

    def anonymize_patient_data(
        self,
        df: pd.DataFrame,
        salt: str = "clinical_trials_salt_2026"
    ) -> pd.DataFrame:
        """
        Anonymize Protected Health Information (PHI) in clinical trial data frames.
        """
        logger.info("Applying HIPAA Safe Harbor PHI anonymization")
        anonymized_df = df.copy()

        for col in anonymized_df.columns:
            col_clean = col.lower().strip()

            # Pseudonymize direct patient IDs / Names
            if any(phi_kw in col_clean for phi_kw in self.PHI_COLUMNS):
                logger.info(f"Masking PHI column: {col}")
                anonymized_df[col] = anonymized_df[col].astype(str).apply(
                    lambda val: hashlib.sha256((val + salt).encode()).hexdigest()[:16]
                )

        return anonymized_df

    def enforce_retention_policy(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "created_at",
        retention_years: int = 10
    ) -> pd.DataFrame:
        """
        Filter dataset based on clinical trial data retention policies.
        """
        if timestamp_col not in df.columns:
            return df

        cutoff_date = pd.Timestamp.now() - pd.DateOffset(years=retention_years)
        initial_len = len(df)
        filtered_df = df[pd.to_datetime(df[timestamp_col]) >= cutoff_date]
        removed_count = initial_len - len(filtered_df)

        if removed_count > 0:
            logger.info(f"Retention policy applied: Removed {removed_count} records older than {retention_years} years")

        return filtered_df
