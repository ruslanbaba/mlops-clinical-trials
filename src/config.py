"""
Configuration management for the MLOps Clinical Trials platform.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseSettings, Field


class Config(BaseSettings):
    """Application configuration with environment variable support."""
    
    # Project settings
    project_name: str = Field(default="mlops-clinical-trials", env="PROJECT_NAME")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Data settings
    data_dir: Path = Field(default=Path("data"), env="DATA_DIR")
    raw_data_dir: Path = Field(default=Path("data/raw"), env="RAW_DATA_DIR")
    processed_data_dir: Path = Field(default=Path("data/processed"), env="PROCESSED_DATA_DIR")
    feature_store_dir: Path = Field(default=Path("data/features"), env="FEATURE_STORE_DIR")
    
    # Model settings
    model_dir: Path = Field(default=Path("models"), env="MODEL_DIR")
    model_registry_uri: str = Field(default="sqlite:///mlflow.db", env="MODEL_REGISTRY_URI")
    experiment_name: str = Field(default="clinical-trials", env="EXPERIMENT_NAME")
    
    # Training settings
    batch_size: int = Field(default=32, env="BATCH_SIZE")
    learning_rate: float = Field(default=0.001, env="LEARNING_RATE")
    epochs: int = Field(default=100, env="EPOCHS")
    early_stopping_patience: int = Field(default=10, env="EARLY_STOPPING_PATIENCE")
    
    # Validation settings
    validation_split: float = Field(default=0.2, env="VALIDATION_SPLIT")
    test_split: float = Field(default=0.2, env="TEST_SPLIT")
    cross_validation_folds: int = Field(default=5, env="CV_FOLDS")
    
    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=4, env="API_WORKERS")
    
    # Database settings
    database_url: str = Field(default="postgresql://user:password@localhost:5432/clinical_trials", env="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Storage settings
    minio_endpoint: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", env="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="clinical-trials", env="MINIO_BUCKET")
    
    # Monitoring settings
    prometheus_gateway: str = Field(default="localhost:9091", env="PROMETHEUS_GATEWAY")
    grafana_url: str = Field(default="http://localhost:3000", env="GRAFANA_URL")
    
    # Kubernetes settings
    kubernetes_namespace: str = Field(default="clinical-trials", env="K8S_NAMESPACE")
    istio_enabled: bool = Field(default=True, env="ISTIO_ENABLED")
    
    # A/B Testing settings
    ab_test_traffic_split: float = Field(default=0.1, env="AB_TEST_TRAFFIC_SPLIT")
    ab_test_duration_hours: int = Field(default=24, env="AB_TEST_DURATION_HOURS")
    ab_test_min_samples: int = Field(default=1000, env="AB_TEST_MIN_SAMPLES")
    
    # Model serving settings
    model_serving_replicas: int = Field(default=3, env="MODEL_SERVING_REPLICAS")
    model_serving_cpu_request: str = Field(default="100m", env="MODEL_SERVING_CPU_REQUEST")
    model_serving_memory_request: str = Field(default="256Mi", env="MODEL_SERVING_MEMORY_REQUEST")
    model_serving_cpu_limit: str = Field(default="500m", env="MODEL_SERVING_CPU_LIMIT")
    model_serving_memory_limit: str = Field(default="1Gi", env="MODEL_SERVING_MEMORY_LIMIT")
    
    # Security settings
    jwt_secret_key: str = Field(default="your-secret-key", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Feature flags
    enable_data_drift_detection: bool = Field(default=True, env="ENABLE_DATA_DRIFT_DETECTION")
    enable_model_explainability: bool = Field(default=True, env="ENABLE_MODEL_EXPLAINABILITY")
    enable_bias_detection: bool = Field(default=True, env="ENABLE_BIAS_DETECTION")
    enable_performance_monitoring: bool = Field(default=True, env="ENABLE_PERFORMANCE_MONITORING")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @classmethod
    def load_from_yaml(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
        return cls(**config_data)
    
    def save_to_yaml(self, config_path: str) -> None:
        """Save configuration to YAML file."""
        config_dict = self.dict()
        # Convert Path objects to strings for YAML serialization
        for key, value in config_dict.items():
            if isinstance(value, Path):
                config_dict[key] = str(value)
        
        with open(config_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=True)
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get model-specific configuration."""
        model_configs = {
            "breast_cancer": {
                "model_type": "xgboost",
                "features": ["age", "tumor_size", "lymph_nodes", "grade"],
                "target": "malignant",
                "hyperparameters": {
                    "n_estimators": 100,
                    "max_depth": 6,
                    "learning_rate": 0.1,
                }
            },
            "lung_cancer": {
                "model_type": "neural_network",
                "features": ["age", "smoking_history", "ct_scan_features"],
                "target": "cancer_probability",
                "hyperparameters": {
                    "hidden_layers": [128, 64, 32],
                    "dropout": 0.3,
                    "activation": "relu",
                }
            },
            "prostate_cancer": {
                "model_type": "random_forest",
                "features": ["psa_level", "age", "family_history"],
                "target": "cancer_risk",
                "hyperparameters": {
                    "n_estimators": 200,
                    "max_depth": 10,
                    "min_samples_split": 5,
                }
            }
        }
        return model_configs.get(model_name, {})


# Global configuration instance
config = Config()
