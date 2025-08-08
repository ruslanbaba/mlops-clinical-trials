"""
Automated validation gates for model deployment pipeline.
"""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import joblib
from pathlib import Path

from ..config import config
from ..logger import get_logger
from .bias_detector import BiasDetector
from .regulatory_compliance import RegulatoryCompliance

logger = get_logger(__name__)


class ValidationGates:
    """
    Automated validation gates for safe model deployment.
    
    Implements multiple validation checks to ensure model quality,
    fairness, compliance, and safety before production deployment.
    """
    
    def __init__(self):
        """Initialize validation gates."""
        self.bias_detector = BiasDetector()
        self.compliance_checker = RegulatoryCompliance()
        self.validation_history = []
        
        # Define validation thresholds
        self.thresholds = {
            'min_accuracy': 0.85,
            'min_precision': 0.80,
            'min_recall': 0.80,
            'min_f1_score': 0.80,
            'max_bias_score': 0.1,
            'min_sample_size': 1000,
            'max_feature_drift': 0.15,
            'max_prediction_drift': 0.10
        }
        
        logger.info("Validation gates initialized")
    
    def run_all_gates(
        self,
        model: Any,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        model_metadata: Dict[str, Any],
        baseline_model: Optional[Any] = None,
        reference_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Run all validation gates and return comprehensive results.
        
        Args:
            model: Trained model to validate
            X_test: Test features
            y_test: Test targets
            model_metadata: Model metadata and configuration
            baseline_model: Baseline model for comparison
            reference_data: Reference data for drift detection
            
        Returns:
            Dictionary with all validation results
        """
        logger.info("Running all validation gates")
        
        validation_results = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'model_info': model_metadata,
            'gates': {},
            'overall_status': 'UNKNOWN',
            'failed_gates': [],
            'warnings': []
        }
        
        try:
            # Gate 1: Data Quality Validation
            logger.info("Running Gate 1: Data Quality Validation")
            validation_results['gates']['data_quality'] = self._validate_data_quality(
                X_test, y_test
            )
            
            # Gate 2: Model Performance Validation
            logger.info("Running Gate 2: Model Performance Validation")
            validation_results['gates']['performance'] = self._validate_model_performance(
                model, X_test, y_test, baseline_model
            )
            
            # Gate 3: Bias Detection
            logger.info("Running Gate 3: Bias Detection")
            validation_results['gates']['bias'] = self._validate_bias(
                model, X_test, y_test
            )
            
            # Gate 4: Data Drift Detection
            if reference_data is not None:
                logger.info("Running Gate 4: Data Drift Detection")
                validation_results['gates']['drift'] = self._validate_data_drift(
                    X_test, reference_data
                )
            
            # Gate 5: Regulatory Compliance
            logger.info("Running Gate 5: Regulatory Compliance")
            validation_results['gates']['compliance'] = self._validate_regulatory_compliance(
                model, model_metadata
            )
            
            # Gate 6: Security Validation
            logger.info("Running Gate 6: Security Validation")
            validation_results['gates']['security'] = self._validate_security(
                model, model_metadata
            )
            
            # Gate 7: Explainability Validation
            logger.info("Running Gate 7: Explainability Validation")
            validation_results['gates']['explainability'] = self._validate_explainability(
                model, X_test.head(100)
            )
            
            # Determine overall status
            validation_results = self._determine_overall_status(validation_results)
            
            # Store validation history
            self.validation_history.append(validation_results)
            
            logger.info(f"Validation gates completed. Status: {validation_results['overall_status']}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Validation gates failed: {str(e)}")
            validation_results['overall_status'] = 'ERROR'
            validation_results['error'] = str(e)
            return validation_results
    
    def _validate_data_quality(
        self, 
        X_test: pd.DataFrame, 
        y_test: pd.Series
    ) -> Dict[str, Any]:
        """Validate data quality metrics."""
        logger.info("Validating data quality")
        
        quality_results = {
            'status': 'UNKNOWN',
            'checks': {},
            'issues': []
        }
        
        # Check sample size
        sample_size = len(X_test)
        quality_results['checks']['sample_size'] = {
            'value': sample_size,
            'threshold': self.thresholds['min_sample_size'],
            'passed': sample_size >= self.thresholds['min_sample_size']
        }
        
        if not quality_results['checks']['sample_size']['passed']:
            quality_results['issues'].append(f"Insufficient sample size: {sample_size}")
        
        # Check missing values
        missing_percentage = X_test.isnull().sum().sum() / (len(X_test) * len(X_test.columns))
        quality_results['checks']['missing_values'] = {
            'percentage': missing_percentage,
            'threshold': 0.05,
            'passed': missing_percentage < 0.05
        }
        
        if not quality_results['checks']['missing_values']['passed']:
            quality_results['issues'].append(f"High missing value percentage: {missing_percentage:.2%}")
        
        # Check target distribution
        target_distribution = y_test.value_counts(normalize=True)
        min_class_proportion = target_distribution.min()
        quality_results['checks']['class_balance'] = {
            'min_class_proportion': min_class_proportion,
            'threshold': 0.1,
            'passed': min_class_proportion >= 0.1
        }
        
        if not quality_results['checks']['class_balance']['passed']:
            quality_results['issues'].append(f"Imbalanced classes: {min_class_proportion:.2%}")
        
        # Check feature variance
        numeric_features = X_test.select_dtypes(include=[np.number])
        zero_variance_features = (numeric_features.var() == 0).sum()
        quality_results['checks']['feature_variance'] = {
            'zero_variance_features': zero_variance_features,
            'threshold': 0,
            'passed': zero_variance_features == 0
        }
        
        if not quality_results['checks']['feature_variance']['passed']:
            quality_results['issues'].append(f"Features with zero variance: {zero_variance_features}")
        
        # Determine overall status
        all_passed = all(check['passed'] for check in quality_results['checks'].values())
        quality_results['status'] = 'PASSED' if all_passed else 'FAILED'
        
        return quality_results
    
    def _validate_model_performance(
        self,
        model: Any,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        baseline_model: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Validate model performance against thresholds and baseline."""
        logger.info("Validating model performance")
        
        performance_results = {
            'status': 'UNKNOWN',
            'metrics': {},
            'comparisons': {},
            'issues': []
        }
        
        # Get predictions
        y_pred = model.predict(X_test)
        
        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted'),
            'recall': recall_score(y_test, y_pred, average='weighted'),
            'f1_score': f1_score(y_test, y_pred, average='weighted')
        }
        
        # Check against thresholds
        for metric_name, value in metrics.items():
            threshold_key = f'min_{metric_name}'
            if threshold_key in self.thresholds:
                threshold = self.thresholds[threshold_key]
                passed = value >= threshold
                
                performance_results['metrics'][metric_name] = {
                    'value': value,
                    'threshold': threshold,
                    'passed': passed
                }
                
                if not passed:
                    performance_results['issues'].append(
                        f"{metric_name.title()} below threshold: {value:.3f} < {threshold}"
                    )
        
        # Compare with baseline model if provided
        if baseline_model is not None:
            baseline_pred = baseline_model.predict(X_test)
            baseline_accuracy = accuracy_score(y_test, baseline_pred)
            
            improvement = metrics['accuracy'] - baseline_accuracy
            performance_results['comparisons']['baseline'] = {
                'baseline_accuracy': baseline_accuracy,
                'current_accuracy': metrics['accuracy'],
                'improvement': improvement,
                'passed': improvement >= 0
            }
            
            if improvement < 0:
                performance_results['issues'].append(
                    f"Performance regression vs baseline: {improvement:.3f}"
                )
        
        # Determine overall status
        all_passed = all(
            metric['passed'] for metric in performance_results['metrics'].values()
        )
        if baseline_model and not performance_results['comparisons']['baseline']['passed']:
            all_passed = False
            
        performance_results['status'] = 'PASSED' if all_passed else 'FAILED'
        
        return performance_results
    
    def _validate_bias(
        self,
        model: Any,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict[str, Any]:
        """Validate model for bias and fairness."""
        logger.info("Validating model bias")
        
        bias_results = {
            'status': 'UNKNOWN',
            'bias_metrics': {},
            'issues': []
        }
        
        try:
            # Run bias detection
            bias_report = self.bias_detector.detect_bias(model, X_test, y_test)
            
            # Extract key metrics
            overall_bias_score = bias_report.get('overall_bias_score', 0)
            bias_results['bias_metrics']['overall_score'] = {
                'value': overall_bias_score,
                'threshold': self.thresholds['max_bias_score'],
                'passed': overall_bias_score <= self.thresholds['max_bias_score']
            }
            
            if not bias_results['bias_metrics']['overall_score']['passed']:
                bias_results['issues'].append(
                    f"High bias score detected: {overall_bias_score:.3f}"
                )
            
            # Check protected attributes
            protected_attributes = bias_report.get('protected_attributes', {})
            for attr, bias_score in protected_attributes.items():
                bias_results['bias_metrics'][f'{attr}_bias'] = {
                    'value': bias_score,
                    'threshold': self.thresholds['max_bias_score'],
                    'passed': bias_score <= self.thresholds['max_bias_score']
                }
                
                if bias_score > self.thresholds['max_bias_score']:
                    bias_results['issues'].append(
                        f"Bias detected for {attr}: {bias_score:.3f}"
                    )
            
            # Store full bias report
            bias_results['full_report'] = bias_report
            
        except Exception as e:
            logger.warning(f"Bias validation failed: {str(e)}")
            bias_results['issues'].append(f"Bias validation error: {str(e)}")
            bias_results['status'] = 'ERROR'
            return bias_results
        
        # Determine overall status
        all_passed = all(
            metric['passed'] for metric in bias_results['bias_metrics'].values()
        )
        bias_results['status'] = 'PASSED' if all_passed else 'FAILED'
        
        return bias_results
    
    def _validate_data_drift(
        self,
        current_data: pd.DataFrame,
        reference_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Validate for data drift between reference and current data."""
        logger.info("Validating data drift")
        
        drift_results = {
            'status': 'UNKNOWN',
            'drift_metrics': {},
            'issues': []
        }
        
        try:
            from ..data.processors import DataProcessor
            processor = DataProcessor()
            
            # Detect data drift
            drift_report = processor.detect_data_drift(reference_data, current_data)
            
            # Check overall drift
            drift_percentage = drift_report['summary']['drift_percentage']
            drift_results['drift_metrics']['overall_drift'] = {
                'percentage': drift_percentage,
                'threshold': self.thresholds['max_feature_drift'] * 100,
                'passed': drift_percentage <= self.thresholds['max_feature_drift'] * 100
            }
            
            if not drift_results['drift_metrics']['overall_drift']['passed']:
                drift_results['issues'].append(
                    f"High feature drift detected: {drift_percentage:.1f}%"
                )
            
            # Store drifted features
            drift_results['drifted_features'] = drift_report['drifted_features']
            drift_results['drift_scores'] = drift_report['drift_scores']
            
        except Exception as e:
            logger.warning(f"Drift validation failed: {str(e)}")
            drift_results['issues'].append(f"Drift validation error: {str(e)}")
            drift_results['status'] = 'ERROR'
            return drift_results
        
        # Determine overall status
        all_passed = all(
            metric['passed'] for metric in drift_results['drift_metrics'].values()
        )
        drift_results['status'] = 'PASSED' if all_passed else 'FAILED'
        
        return drift_results
    
    def _validate_regulatory_compliance(
        self,
        model: Any,
        model_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate regulatory compliance requirements."""
        logger.info("Validating regulatory compliance")
        
        compliance_results = {
            'status': 'UNKNOWN',
            'compliance_checks': {},
            'issues': []
        }
        
        try:
            # Run compliance checks
            compliance_report = self.compliance_checker.check_compliance(
                model, model_metadata
            )
            
            # Extract compliance status
            compliance_results['compliance_checks'] = compliance_report['checks']
            
            # Check for failed compliance
            failed_checks = [
                check_name for check_name, check_result in compliance_report['checks'].items()
                if not check_result.get('passed', False)
            ]
            
            if failed_checks:
                compliance_results['issues'].extend([
                    f"Failed compliance check: {check}" for check in failed_checks
                ])
            
            compliance_results['full_report'] = compliance_report
            
        except Exception as e:
            logger.warning(f"Compliance validation failed: {str(e)}")
            compliance_results['issues'].append(f"Compliance validation error: {str(e)}")
            compliance_results['status'] = 'ERROR'
            return compliance_results
        
        # Determine overall status
        compliance_results['status'] = 'PASSED' if not compliance_results['issues'] else 'FAILED'
        
        return compliance_results
    
    def _validate_security(
        self,
        model: Any,
        model_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate security aspects of the model."""
        logger.info("Validating security")
        
        security_results = {
            'status': 'UNKNOWN',
            'security_checks': {},
            'issues': []
        }
        
        # Check model serialization safety
        try:
            model_path = model_metadata.get('model_path')
            if model_path:
                # Basic security checks on model file
                model_file = Path(model_path)
                if model_file.exists():
                    file_size = model_file.stat().st_size
                    security_results['security_checks']['file_size'] = {
                        'size_mb': file_size / (1024 * 1024),
                        'threshold': 100,  # 100 MB limit
                        'passed': file_size < 100 * 1024 * 1024
                    }
                    
                    if not security_results['security_checks']['file_size']['passed']:
                        security_results['issues'].append(
                            f"Model file too large: {file_size / (1024 * 1024):.1f} MB"
                        )
        except Exception as e:
            logger.warning(f"Security validation failed: {str(e)}")
            security_results['issues'].append(f"Security validation error: {str(e)}")
        
        # Check for sensitive information in model metadata
        sensitive_keywords = ['password', 'key', 'token', 'secret']
        metadata_str = str(model_metadata).lower()
        for keyword in sensitive_keywords:
            if keyword in metadata_str:
                security_results['issues'].append(
                    f"Potential sensitive information in metadata: {keyword}"
                )
        
        # Determine overall status
        security_results['status'] = 'PASSED' if not security_results['issues'] else 'WARNING'
        
        return security_results
    
    def _validate_explainability(
        self,
        model: Any,
        X_sample: pd.DataFrame
    ) -> Dict[str, Any]:
        """Validate model explainability requirements."""
        logger.info("Validating explainability")
        
        explainability_results = {
            'status': 'UNKNOWN',
            'explainability_checks': {},
            'issues': []
        }
        
        try:
            # Check if model has feature importance
            has_feature_importance = hasattr(model, 'feature_importances_')
            explainability_results['explainability_checks']['feature_importance'] = {
                'available': has_feature_importance,
                'passed': has_feature_importance
            }
            
            if not has_feature_importance:
                explainability_results['issues'].append("Model lacks feature importance")
            
            # Try to generate SHAP explanations (simplified check)
            try:
                import shap
                explainer_available = True
            except ImportError:
                explainer_available = False
            
            explainability_results['explainability_checks']['shap_available'] = {
                'available': explainer_available,
                'passed': True  # Not required, just nice to have
            }
            
        except Exception as e:
            logger.warning(f"Explainability validation failed: {str(e)}")
            explainability_results['issues'].append(f"Explainability validation error: {str(e)}")
        
        # Determine overall status (lenient for explainability)
        explainability_results['status'] = 'PASSED' if len(explainability_results['issues']) <= 1 else 'WARNING'
        
        return explainability_results
    
    def _determine_overall_status(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Determine overall validation status based on individual gate results."""
        gate_statuses = [gate['status'] for gate in validation_results['gates'].values()]
        failed_gates = [
            gate_name for gate_name, gate_result in validation_results['gates'].items()
            if gate_result['status'] == 'FAILED'
        ]
        
        validation_results['failed_gates'] = failed_gates
        
        # Determine overall status
        if 'FAILED' in gate_statuses:
            validation_results['overall_status'] = 'FAILED'
        elif 'ERROR' in gate_statuses:
            validation_results['overall_status'] = 'ERROR'
        elif 'WARNING' in gate_statuses:
            validation_results['overall_status'] = 'WARNING'
        else:
            validation_results['overall_status'] = 'PASSED'
        
        return validation_results
    
    def get_validation_summary(self) -> pd.DataFrame:
        """Get summary of validation history."""
        if not self.validation_history:
            return pd.DataFrame()
        
        summary_data = []
        for validation in self.validation_history:
            summary_data.append({
                'timestamp': validation['timestamp'],
                'model_name': validation['model_info'].get('model_name', 'unknown'),
                'model_type': validation['model_info'].get('model_type', 'unknown'),
                'overall_status': validation['overall_status'],
                'failed_gates': len(validation['failed_gates']),
                'total_issues': sum(
                    len(gate.get('issues', [])) for gate in validation['gates'].values()
                )
            })
        
        return pd.DataFrame(summary_data)
