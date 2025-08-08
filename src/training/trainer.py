"""
Model trainer for cancer prediction models with MLflow tracking.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
from sklearn.model_selection import cross_val_score, StratifiedKFold
import mlflow
import mlflow.sklearn
import mlflow.pytorch
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

from ..config import config
from ..logger import get_logger
from .models import CancerModelFactory
from .hyperparameter_tuning import HyperparameterTuner

logger = get_logger(__name__)


class ModelTrainer:
    """
    Comprehensive model trainer for cancer prediction models.
    
    Supports various ML algorithms with automated hyperparameter tuning,
    cross-validation, and MLflow experiment tracking.
    """
    
    def __init__(self, experiment_name: str = "clinical-trials"):
        """
        Initialize the model trainer.
        
        Args:
            experiment_name: MLflow experiment name
        """
        self.experiment_name = experiment_name
        self.model_factory = CancerModelFactory()
        self.tuner = HyperparameterTuner()
        
        # Setup MLflow
        mlflow.set_tracking_uri(config.model_registry_uri)
        self.experiment_id = self._setup_experiment()
        
        logger.info(f"Model trainer initialized with experiment: {experiment_name}")
    
    def _setup_experiment(self) -> str:
        """Setup MLflow experiment and return experiment ID."""
        try:
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(self.experiment_name)
            else:
                experiment_id = experiment.experiment_id
            
            logger.info(f"Using MLflow experiment: {self.experiment_name} (ID: {experiment_id})")
            return experiment_id
            
        except Exception as e:
            logger.error(f"Failed to setup MLflow experiment: {str(e)}")
            raise
    
    def train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        model_type: str,
        model_name: str,
        hyperparameters: Optional[Dict[str, Any]] = None,
        tune_hyperparameters: bool = True,
        cross_validate: bool = True,
        save_model: bool = True
    ) -> Dict[str, Any]:
        """
        Train a cancer prediction model.
        
        Args:
            X_train: Training features
            y_train: Training targets
            X_val: Validation features
            y_val: Validation targets
            model_type: Type of model ('xgboost', 'random_forest', 'neural_network', etc.)
            model_name: Name for the model
            hyperparameters: Model hyperparameters
            tune_hyperparameters: Whether to perform hyperparameter tuning
            cross_validate: Whether to perform cross-validation
            save_model: Whether to save the trained model
            
        Returns:
            Dictionary with training results
        """
        logger.info(f"Training {model_type} model: {model_name}")
        
        with mlflow.start_run(experiment_id=self.experiment_id, run_name=model_name):
            try:
                # Log parameters
                mlflow.log_param("model_type", model_type)
                mlflow.log_param("model_name", model_name)
                mlflow.log_param("train_samples", len(X_train))
                mlflow.log_param("val_samples", len(X_val))
                mlflow.log_param("features", X_train.shape[1])
                
                # Hyperparameter tuning
                if tune_hyperparameters:
                    logger.info("Starting hyperparameter tuning")
                    best_params = self.tuner.tune_hyperparameters(
                        X_train, y_train, model_type, n_trials=50
                    )
                    hyperparameters = best_params
                    mlflow.log_params(best_params)
                
                # Create and train model
                model = self.model_factory.create_model(model_type, hyperparameters)
                
                if model_type == 'neural_network':
                    # Train neural network with PyTorch
                    model, training_history = self._train_neural_network(
                        model, X_train, y_train, X_val, y_val
                    )
                    # Log training history
                    for epoch, metrics in enumerate(training_history):
                        mlflow.log_metrics(metrics, step=epoch)
                else:
                    # Train sklearn model
                    model.fit(X_train, y_train)
                
                # Cross-validation
                if cross_validate and model_type != 'neural_network':
                    cv_scores = self._perform_cross_validation(model, X_train, y_train)
                    mlflow.log_metrics({
                        "cv_accuracy_mean": cv_scores['accuracy'].mean(),
                        "cv_accuracy_std": cv_scores['accuracy'].std(),
                        "cv_f1_mean": cv_scores['f1'].mean(),
                        "cv_f1_std": cv_scores['f1'].std(),
                    })
                
                # Evaluate model
                evaluation_results = self._evaluate_model(model, X_val, y_val, model_type)
                mlflow.log_metrics(evaluation_results['metrics'])
                
                # Save model artifacts
                if save_model:
                    model_path = self._save_model(model, model_name, model_type)
                    mlflow.log_param("model_path", model_path)
                    
                    # Log model to MLflow
                    if model_type == 'neural_network':
                        mlflow.pytorch.log_model(model, "model")
                    else:
                        mlflow.sklearn.log_model(model, "model")
                
                # Prepare results
                results = {
                    'model': model,
                    'model_type': model_type,
                    'model_name': model_name,
                    'hyperparameters': hyperparameters,
                    'evaluation': evaluation_results,
                    'run_id': mlflow.active_run().info.run_id
                }
                
                if cross_validate and model_type != 'neural_network':
                    results['cross_validation'] = cv_scores
                
                logger.info(f"Model training completed successfully: {model_name}")
                return results
                
            except Exception as e:
                logger.error(f"Model training failed: {str(e)}")
                mlflow.log_param("status", "failed")
                mlflow.log_param("error", str(e))
                raise
    
    def _train_neural_network(
        self,
        model: nn.Module,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        epochs: int = 100,
        batch_size: int = 32,
        learning_rate: float = 0.001
    ) -> Tuple[nn.Module, List[Dict[str, float]]]:
        """Train a PyTorch neural network model."""
        logger.info("Training neural network")
        
        # Convert to tensors
        X_train_tensor = torch.FloatTensor(X_train.values)
        y_train_tensor = torch.LongTensor(y_train.values)
        X_val_tensor = torch.FloatTensor(X_val.values)
        y_val_tensor = torch.LongTensor(y_val.values)
        
        # Create data loaders
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        # Setup optimizer and loss function
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)
        criterion = nn.CrossEntropyLoss()
        
        # Training loop
        training_history = []
        best_val_loss = float('inf')
        patience = config.early_stopping_patience
        patience_counter = 0
        
        for epoch in range(epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            correct_train = 0
            total_train = 0
            
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total_train += batch_y.size(0)
                correct_train += (predicted == batch_y).sum().item()
            
            # Validation phase
            model.eval()
            with torch.no_grad():
                val_outputs = model(X_val_tensor)
                val_loss = criterion(val_outputs, y_val_tensor).item()
                _, val_predicted = torch.max(val_outputs.data, 1)
                val_accuracy = (val_predicted == y_val_tensor).sum().item() / len(y_val_tensor)
            
            train_accuracy = correct_train / total_train
            avg_train_loss = train_loss / len(train_loader)
            
            # Log metrics
            epoch_metrics = {
                'train_loss': avg_train_loss,
                'train_accuracy': train_accuracy,
                'val_loss': val_loss,
                'val_accuracy': val_accuracy
            }
            training_history.append(epoch_metrics)
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"Early stopping at epoch {epoch}")
                    break
            
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}: Train Loss: {avg_train_loss:.4f}, "
                           f"Val Loss: {val_loss:.4f}, Val Acc: {val_accuracy:.4f}")
        
        return model, training_history
    
    def _perform_cross_validation(
        self,
        model,
        X: pd.DataFrame,
        y: pd.Series,
        cv_folds: int = 5
    ) -> Dict[str, np.ndarray]:
        """Perform cross-validation and return scores."""
        logger.info(f"Performing {cv_folds}-fold cross-validation")
        
        cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        
        # Calculate various metrics
        accuracy_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
        f1_scores = cross_val_score(model, X, y, cv=cv, scoring='f1_weighted')
        precision_scores = cross_val_score(model, X, y, cv=cv, scoring='precision_weighted')
        recall_scores = cross_val_score(model, X, y, cv=cv, scoring='recall_weighted')
        
        cv_results = {
            'accuracy': accuracy_scores,
            'f1': f1_scores,
            'precision': precision_scores,
            'recall': recall_scores
        }
        
        logger.info(f"CV Accuracy: {accuracy_scores.mean():.4f} (+/- {accuracy_scores.std() * 2:.4f})")
        return cv_results
    
    def _evaluate_model(
        self,
        model,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        model_type: str
    ) -> Dict[str, Any]:
        """Evaluate model performance and return comprehensive metrics."""
        logger.info("Evaluating model performance")
        
        # Make predictions
        if model_type == 'neural_network':
            model.eval()
            with torch.no_grad():
                X_test_tensor = torch.FloatTensor(X_test.values)
                outputs = model(X_test_tensor)
                _, y_pred = torch.max(outputs, 1)
                y_pred = y_pred.numpy()
                # Get probabilities for binary classification
                y_pred_proba = torch.softmax(outputs, dim=1)[:, 1].numpy()
        else:
            y_pred = model.predict(X_test)
            try:
                y_pred_proba = model.predict_proba(X_test)[:, 1]
            except:
                y_pred_proba = None
        
        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted'),
            'recall': recall_score(y_test, y_pred, average='weighted'),
            'f1_score': f1_score(y_test, y_pred, average='weighted')
        }
        
        # Add AUC if probabilities available
        if y_pred_proba is not None:
            try:
                metrics['auc_roc'] = roc_auc_score(y_test, y_pred_proba)
            except:
                logger.warning("Could not calculate AUC-ROC score")
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        
        # Classification report
        class_report = classification_report(y_test, y_pred, output_dict=True)
        
        evaluation_results = {
            'metrics': metrics,
            'confusion_matrix': cm.tolist(),
            'classification_report': class_report,
            'predictions': y_pred.tolist(),
            'true_labels': y_test.tolist()
        }
        
        if y_pred_proba is not None:
            evaluation_results['prediction_probabilities'] = y_pred_proba.tolist()
        
        logger.info(f"Model evaluation completed. Accuracy: {metrics['accuracy']:.4f}")
        return evaluation_results
    
    def _save_model(self, model, model_name: str, model_type: str) -> str:
        """Save trained model to disk."""
        model_dir = Path(config.model_dir) / model_name
        model_dir.mkdir(parents=True, exist_ok=True)
        
        if model_type == 'neural_network':
            model_path = model_dir / "model.pth"
            torch.save(model.state_dict(), model_path)
        else:
            model_path = model_dir / "model.joblib"
            joblib.dump(model, model_path)
        
        # Save metadata
        metadata = {
            'model_name': model_name,
            'model_type': model_type,
            'timestamp': pd.Timestamp.now().isoformat(),
            'framework': 'pytorch' if model_type == 'neural_network' else 'sklearn'
        }
        
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {model_path}")
        return str(model_path)
    
    def load_model(self, model_path: str, model_type: str) -> Any:
        """Load a trained model from disk."""
        logger.info(f"Loading model from {model_path}")
        
        if model_type == 'neural_network':
            # Load PyTorch model (would need model architecture)
            raise NotImplementedError("PyTorch model loading requires architecture definition")
        else:
            model = joblib.load(model_path)
        
        logger.info("Model loaded successfully")
        return model
    
    def compare_models(self, run_ids: List[str]) -> pd.DataFrame:
        """Compare multiple model runs and return comparison DataFrame."""
        logger.info(f"Comparing {len(run_ids)} model runs")
        
        comparison_data = []
        
        for run_id in run_ids:
            try:
                run = mlflow.get_run(run_id)
                metrics = run.data.metrics
                params = run.data.params
                
                comparison_data.append({
                    'run_id': run_id,
                    'model_name': params.get('model_name', 'unknown'),
                    'model_type': params.get('model_type', 'unknown'),
                    'accuracy': metrics.get('accuracy', 0),
                    'f1_score': metrics.get('f1_score', 0),
                    'precision': metrics.get('precision', 0),
                    'recall': metrics.get('recall', 0),
                    'auc_roc': metrics.get('auc_roc', 0),
                    'timestamp': run.info.start_time
                })
            except Exception as e:
                logger.warning(f"Could not retrieve run {run_id}: {str(e)}")
        
        comparison_df = pd.DataFrame(comparison_data)
        comparison_df = comparison_df.sort_values('accuracy', ascending=False)
        
        logger.info("Model comparison completed")
        return comparison_df
