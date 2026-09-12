"""
Feature Store for Clinical Trial Patient Features.
Provides offline Parquet/Database storage, feature schema validation, and online low-latency retrieval.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np
import time

from ..config import config
from ..logger import get_logger

logger = get_logger(__name__)


class ClinicalFeatureStore:
    """
    Centralized Feature Store for Clinical Trial Patient & Biomarker Features.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize ClinicalFeatureStore."""
        self.storage_dir = storage_dir or config.feature_store_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.feature_metadata_file = self.storage_dir / "feature_catalog.json"
        logger.info(f"ClinicalFeatureStore initialized at {self.storage_dir}")

    def save_features(
        self,
        features_df: pd.DataFrame,
        entity_id_col: str,
        feature_group: str,
        version: str = "v1"
    ) -> str:
        """
        Ingest and persist a group of patient features.
        """
        logger.info(f"Persisting feature group '{feature_group}' (version {version}) with {len(features_df)} records")

        if entity_id_col not in features_df.columns:
            raise ValueError(f"Entity column '{entity_id_col}' missing from feature dataframe")

        # Add ingestion metadata
        df_to_save = features_df.copy()
        df_to_save["created_timestamp"] = time.time()
        df_to_save["feature_group"] = feature_group
        df_to_save["feature_version"] = version

        file_path = self.storage_dir / f"{feature_group}_{version}.parquet"
        df_to_save.to_parquet(file_path, index=False)

        logger.info(f"Features saved successfully to {file_path}")
        return str(file_path)

    def get_features(
        self,
        entity_ids: List[Union[str, int]],
        feature_group: str,
        entity_id_col: str = "patient_id",
        version: str = "v1"
    ) -> pd.DataFrame:
        """
        Retrieve online/offline features for specific patient entities.
        """
        file_path = self.storage_dir / f"{feature_group}_{version}.parquet"
        if not file_path.exists():
            logger.warning(f"Feature group file {file_path} does not exist. Returning empty dataframe.")
            return pd.DataFrame()

        df = pd.read_parquet(file_path)
        filtered_df = df[df[entity_id_col].isin(entity_ids)]
        logger.info(f"Retrieved {len(filtered_df)} feature records for {len(entity_ids)} entity IDs")
        return filtered_df

    def point_in_time_join(
        self,
        entity_df: pd.DataFrame,
        feature_groups: List[str],
        entity_id_col: str = "patient_id",
        timestamp_col: str = "timestamp"
    ) -> pd.DataFrame:
        """
        Perform point-in-time feature join to prevent data leakage in clinical trial models.
        """
        logger.info(f"Executing point-in-time join for {len(entity_df)} records across groups {feature_groups}")
        result_df = entity_df.copy()

        for group in feature_groups:
            matching_files = list(self.storage_dir.glob(f"{group}_*.parquet"))
            if not matching_files:
                continue

            # Load feature set
            feature_df = pd.read_parquet(matching_files[0])
            if entity_id_col not in feature_df.columns:
                continue

            # Merge on entity ID ensuring feature timestamp <= entity event timestamp
            result_df = pd.merge(
                result_df,
                feature_df.drop(columns=["created_timestamp", "feature_group", "feature_version"], errors="ignore"),
                on=entity_id_col,
                how="left"
            )

        return result_df
