"""
Data pipeline for processing clinical trial data.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import yaml

from ..config import config
from ..logger import get_logger
from .processors import DataProcessor
from .validators import DataValidator

logger = get_logger(__name__)


class DataPipeline:
    """
    Comprehensive data pipeline for clinical trial data processing.
    
    Handles data ingestion, cleaning, feature engineering, validation,
    and preparation for model training.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the data pipeline.
        
        Args:
            config_path: Path to pipeline configuration file
        """
        self.config = config
        self.processor = DataProcessor()
        self.validator = DataValidator()
        
        if config_path:
            self.load_config(config_path)
        
        logger.info("Data pipeline initialized")
    
    def load_config(self, config_path: str) -> None:
        """Load pipeline configuration from YAML file."""
        with open(config_path, 'r') as f:
            self.pipeline_config = yaml.safe_load(f)
        logger.info(f"Loaded pipeline configuration from {config_path}")
    
    def ingest_data(self, source: str, **kwargs) -> pd.DataFrame:
        """
        Ingest data from various sources.
        
        Args:
            source: Data source type ('csv', 'parquet', 'database', 'api')
            **kwargs: Additional arguments for data loading
            
        Returns:
            Raw data DataFrame
        """
        logger.info(f"Ingesting data from {source}")
        
        if source == 'csv':
            data = pd.read_csv(kwargs.get('file_path'))
        elif source == 'parquet':
            data = pd.read_parquet(kwargs.get('file_path'))
        elif source == 'database':
            # Database connection logic would go here
            raise NotImplementedError("Database ingestion not implemented")
        elif source == 'api':
            # API ingestion logic would go here
            raise NotImplementedError("API ingestion not implemented")
        else:
            raise ValueError(f"Unsupported data source: {source}")
        
        logger.info(f"Ingested {len(data)} records from {source}")
        return data
    
    def clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and preprocess raw data.
        
        Args:
            data: Raw data DataFrame
            
        Returns:
            Cleaned data DataFrame
        """
        logger.info("Starting data cleaning")
        
        # Remove duplicates
        initial_count = len(data)
        data = data.drop_duplicates()
        logger.info(f"Removed {initial_count - len(data)} duplicate records")
        
        # Handle missing values
        data = self.processor.handle_missing_values(data)
        
        # Remove outliers
        data = self.processor.remove_outliers(data)
        
        # Standardize column names
        data.columns = data.columns.str.lower().str.replace(' ', '_')
        
        logger.info(f"Data cleaning completed. Final dataset size: {len(data)}")
        return data
    
    def engineer_features(self, data: pd.DataFrame, model_type: str) -> pd.DataFrame:
        """
        Engineer features specific to cancer type and model requirements.
        
        Args:
            data: Cleaned data DataFrame
            model_type: Type of cancer model ('breast', 'lung', 'prostate', etc.)
            
        Returns:
            DataFrame with engineered features
        """
        logger.info(f"Engineering features for {model_type} cancer model")
        
        if model_type == 'breast_cancer':
            data = self._engineer_breast_cancer_features(data)
        elif model_type == 'lung_cancer':
            data = self._engineer_lung_cancer_features(data)
        elif model_type == 'prostate_cancer':
            data = self._engineer_prostate_cancer_features(data)
        else:
            logger.warning(f"No specific feature engineering for {model_type}")
        
        # General feature engineering
        data = self.processor.create_interaction_features(data)
        data = self.processor.create_polynomial_features(data)
        
        logger.info(f"Feature engineering completed. Features: {data.shape[1]}")
        return data
    
    def _engineer_breast_cancer_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Engineer features specific to breast cancer models."""
        # Age groups
        if 'age' in data.columns:
            data['age_group'] = pd.cut(
                data['age'], 
                bins=[0, 40, 50, 60, 100], 
                labels=['<40', '40-50', '50-60', '60+']
            )
        
        # Tumor size categories
        if 'tumor_size' in data.columns:
            data['tumor_size_category'] = pd.cut(
                data['tumor_size'],
                bins=[0, 2, 5, float('inf')],
                labels=['small', 'medium', 'large']
            )
        
        # Lymph node involvement
        if 'lymph_nodes_positive' in data.columns:
            data['has_lymph_node_involvement'] = (data['lymph_nodes_positive'] > 0).astype(int)
        
        return data
    
    def _engineer_lung_cancer_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Engineer features specific to lung cancer models."""
        # Smoking history
        if 'smoking_years' in data.columns:
            data['smoking_category'] = pd.cut(
                data['smoking_years'],
                bins=[0, 10, 20, float('inf')],
                labels=['light', 'moderate', 'heavy']
            )
        
        # Pack years calculation
        if 'cigarettes_per_day' in data.columns and 'smoking_years' in data.columns:
            data['pack_years'] = (data['cigarettes_per_day'] * data['smoking_years']) / 20
        
        return data
    
    def _engineer_prostate_cancer_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Engineer features specific to prostate cancer models."""
        # PSA level categories
        if 'psa_level' in data.columns:
            data['psa_category'] = pd.cut(
                data['psa_level'],
                bins=[0, 4, 10, float('inf')],
                labels=['normal', 'elevated', 'high']
            )
        
        # Age-adjusted PSA
        if 'psa_level' in data.columns and 'age' in data.columns:
            data['age_adjusted_psa'] = data['psa_level'] / (data['age'] / 50)
        
        return data
    
    def validate_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate data quality and return validation report.
        
        Args:
            data: DataFrame to validate
            
        Returns:
            Validation report dictionary
        """
        logger.info("Starting data validation")
        
        validation_report = {
            'data_quality': self.validator.check_data_quality(data),
            'statistical_validation': self.validator.validate_distributions(data),
            'business_rules': self.validator.validate_business_rules(data),
            'completeness': self.validator.check_completeness(data),
            'consistency': self.validator.check_consistency(data)
        }
        
        logger.info("Data validation completed")
        return validation_report
    
    def split_data(
        self, 
        data: pd.DataFrame, 
        target_column: str,
        test_size: float = 0.2,
        val_size: float = 0.2,
        random_state: int = 42
    ) -> Dict[str, pd.DataFrame]:
        """
        Split data into train, validation, and test sets.
        
        Args:
            data: Input DataFrame
            target_column: Name of target column
            test_size: Proportion for test set
            val_size: Proportion for validation set
            random_state: Random state for reproducibility
            
        Returns:
            Dictionary with train, validation, and test DataFrames
        """
        logger.info("Splitting data into train/validation/test sets")
        
        # Separate features and target
        X = data.drop(columns=[target_column])
        y = data[target_column]
        
        # First split: train+val and test
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # Second split: train and validation
        val_size_adjusted = val_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=val_size_adjusted, 
            random_state=random_state, stratify=y_temp
        )
        
        logger.info(f"Data split completed:")
        logger.info(f"  Train: {len(X_train)} samples")
        logger.info(f"  Validation: {len(X_val)} samples")
        logger.info(f"  Test: {len(X_test)} samples")
        
        return {
            'train': pd.concat([X_train, y_train], axis=1),
            'validation': pd.concat([X_val, y_val], axis=1),
            'test': pd.concat([X_test, y_test], axis=1)
        }
    
    def save_processed_data(
        self, 
        datasets: Dict[str, pd.DataFrame], 
        output_dir: str
    ) -> None:
        """
        Save processed datasets to disk.
        
        Args:
            datasets: Dictionary of datasets to save
            output_dir: Output directory path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for name, dataset in datasets.items():
            file_path = output_path / f"{name}.parquet"
            dataset.to_parquet(file_path, index=False)
            logger.info(f"Saved {name} dataset to {file_path}")
    
    def run_pipeline(
        self, 
        source: str, 
        model_type: str,
        target_column: str,
        **kwargs
    ) -> Dict[str, pd.DataFrame]:
        """
        Run the complete data pipeline.
        
        Args:
            source: Data source type
            model_type: Cancer model type
            target_column: Target column name
            **kwargs: Additional arguments
            
        Returns:
            Dictionary with processed datasets
        """
        logger.info("Starting complete data pipeline")
        
        try:
            # 1. Ingest data
            raw_data = self.ingest_data(source, **kwargs)
            
            # 2. Clean data
            clean_data = self.clean_data(raw_data)
            
            # 3. Engineer features
            featured_data = self.engineer_features(clean_data, model_type)
            
            # 4. Validate data
            validation_report = self.validate_data(featured_data)
            
            # 5. Split data
            datasets = self.split_data(featured_data, target_column)
            
            # 6. Save processed data
            output_dir = self.config.processed_data_dir / model_type
            self.save_processed_data(datasets, str(output_dir))
            
            logger.info("Data pipeline completed successfully")
            return datasets
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            raise


if __name__ == "__main__":
    # Example usage
    pipeline = DataPipeline()
    
    # Run pipeline for breast cancer data
    datasets = pipeline.run_pipeline(
        source='csv',
        model_type='breast_cancer',
        target_column='malignant',
        file_path='data/raw/breast_cancer.csv'
    )
