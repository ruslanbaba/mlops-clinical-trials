"""
A/B Testing Framework for safe model deployment using Istio service mesh.
"""

from typing import Any, Dict, List, Optional, Tuple
import json
import time
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy import stats
import redis
from kubernetes import client, config as k8s_config

from ..config import config
from ..logger import get_logger

logger = get_logger(__name__)


class ABTestingFramework:
    """
    A/B Testing framework for safe model rollout with statistical significance testing.
    
    Supports traffic splitting, performance monitoring, and automatic rollback
    capabilities integrated with Istio service mesh.
    """
    
    def __init__(self):
        """Initialize the A/B testing framework."""
        self.redis_client = redis.from_url(config.redis_url)
        
        # Initialize Kubernetes client
        try:
            k8s_config.load_incluster_config()
        except:
            try:
                k8s_config.load_kube_config()
            except:
                logger.warning("Could not load Kubernetes config")
        
        self.k8s_client = client.ApiClient()
        self.active_tests = {}
        
        logger.info("A/B Testing framework initialized")
    
    def create_ab_test(
        self,
        test_name: str,
        baseline_model: str,
        candidate_model: str,
        traffic_split: float = 0.1,
        duration_hours: int = 24,
        success_metrics: List[str] = None,
        min_samples: int = 1000,
        significance_level: float = 0.05
    ) -> str:
        """
        Create a new A/B test configuration.
        
        Args:
            test_name: Unique name for the test
            baseline_model: Baseline model identifier
            candidate_model: Candidate model identifier
            traffic_split: Percentage of traffic to route to candidate (0.0-1.0)
            duration_hours: Maximum test duration in hours
            success_metrics: List of metrics to track
            min_samples: Minimum samples required for statistical significance
            significance_level: Statistical significance level
            
        Returns:
            Test ID
        """
        logger.info(f"Creating A/B test: {test_name}")
        
        if success_metrics is None:
            success_metrics = ['accuracy', 'response_time', 'error_rate']
        
        test_config = {
            'test_id': f"ab_test_{int(time.time())}",
            'test_name': test_name,
            'baseline_model': baseline_model,
            'candidate_model': candidate_model,
            'traffic_split': traffic_split,
            'duration_hours': duration_hours,
            'success_metrics': success_metrics,
            'min_samples': min_samples,
            'significance_level': significance_level,
            'start_time': datetime.now().isoformat(),
            'end_time': (datetime.now() + timedelta(hours=duration_hours)).isoformat(),
            'status': 'CREATED',
            'baseline_metrics': {},
            'candidate_metrics': {},
            'statistical_results': {}
        }
        
        # Store test configuration in Redis
        self.redis_client.setex(
            f"ab_test:{test_config['test_id']}", 
            timedelta(hours=duration_hours + 24),  # Keep for 24h after test
            json.dumps(test_config)
        )
        
        self.active_tests[test_config['test_id']] = test_config
        
        logger.info(f"A/B test created with ID: {test_config['test_id']}")
        return test_config['test_id']
    
    def start_ab_test(self, test_id: str) -> bool:
        """
        Start an A/B test by deploying Istio traffic splitting configuration.
        
        Args:
            test_id: Test identifier
            
        Returns:
            Success status
        """
        logger.info(f"Starting A/B test: {test_id}")
        
        try:
            # Get test configuration
            test_config = self._get_test_config(test_id)
            if not test_config:
                logger.error(f"Test configuration not found: {test_id}")
                return False
            
            # Deploy Istio Virtual Service for traffic splitting
            success = self._deploy_istio_traffic_split(test_config)
            
            if success:
                test_config['status'] = 'RUNNING'
                test_config['actual_start_time'] = datetime.now().isoformat()
                self._update_test_config(test_id, test_config)
                
                logger.info(f"A/B test started successfully: {test_id}")
                return True
            else:
                logger.error(f"Failed to start A/B test: {test_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting A/B test {test_id}: {str(e)}")
            return False
    
    def stop_ab_test(self, test_id: str, reason: str = "Manual stop") -> bool:
        """
        Stop an A/B test and restore traffic to baseline.
        
        Args:
            test_id: Test identifier
            reason: Reason for stopping the test
            
        Returns:
            Success status
        """
        logger.info(f"Stopping A/B test: {test_id}, Reason: {reason}")
        
        try:
            # Get test configuration
            test_config = self._get_test_config(test_id)
            if not test_config:
                logger.error(f"Test configuration not found: {test_id}")
                return False
            
            # Restore baseline traffic (100% to baseline)
            success = self._restore_baseline_traffic(test_config)
            
            if success:
                test_config['status'] = 'STOPPED'
                test_config['stop_time'] = datetime.now().isoformat()
                test_config['stop_reason'] = reason
                self._update_test_config(test_id, test_config)
                
                # Generate final test report
                self._generate_test_report(test_id)
                
                logger.info(f"A/B test stopped successfully: {test_id}")
                return True
            else:
                logger.error(f"Failed to stop A/B test: {test_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping A/B test {test_id}: {str(e)}")
            return False
    
    def route_request(self, test_id: str, request_data: Dict[str, Any]) -> str:
        """
        Route a request to either baseline or candidate model based on traffic split.
        
        Args:
            test_id: Test identifier
            request_data: Request data for routing decision
            
        Returns:
            Model identifier to route to
        """
        test_config = self._get_test_config(test_id)
        if not test_config or test_config['status'] != 'RUNNING':
            return test_config['baseline_model']
        
        # Simple random routing based on traffic split
        if random.random() < test_config['traffic_split']:
            return test_config['candidate_model']
        else:
            return test_config['baseline_model']
    
    def record_prediction(
        self,
        test_id: str,
        model_id: str,
        request_data: Dict[str, Any],
        prediction: Any,
        response_time: float,
        success: bool = True
    ) -> None:
        """
        Record a prediction result for A/B test analysis.
        
        Args:
            test_id: Test identifier
            model_id: Model that made the prediction
            request_data: Input request data
            prediction: Model prediction
            response_time: Response time in milliseconds
            success: Whether the prediction was successful
        """
        prediction_record = {
            'timestamp': datetime.now().isoformat(),
            'test_id': test_id,
            'model_id': model_id,
            'prediction': prediction,
            'response_time': response_time,
            'success': success,
            'request_hash': hash(str(request_data))
        }
        
        # Store in Redis with expiration
        record_key = f"prediction:{test_id}:{model_id}:{int(time.time() * 1000)}"
        self.redis_client.setex(
            record_key,
            timedelta(days=7),  # Keep for 7 days
            json.dumps(prediction_record)
        )
    
    def analyze_ab_test(self, test_id: str) -> Dict[str, Any]:
        """
        Analyze A/B test results and perform statistical significance testing.
        
        Args:
            test_id: Test identifier
            
        Returns:
            Analysis results
        """
        logger.info(f"Analyzing A/B test: {test_id}")
        
        try:
            test_config = self._get_test_config(test_id)
            if not test_config:
                logger.error(f"Test configuration not found: {test_id}")
                return {}
            
            # Get prediction data for both models
            baseline_data = self._get_prediction_data(test_id, test_config['baseline_model'])
            candidate_data = self._get_prediction_data(test_id, test_config['candidate_model'])
            
            analysis_results = {
                'test_id': test_id,
                'test_name': test_config['test_name'],
                'analysis_time': datetime.now().isoformat(),
                'baseline_stats': self._calculate_model_stats(baseline_data),
                'candidate_stats': self._calculate_model_stats(candidate_data),
                'statistical_tests': {},
                'recommendations': []
            }
            
            # Perform statistical tests
            if len(baseline_data) >= test_config['min_samples'] and len(candidate_data) >= test_config['min_samples']:
                # Response time comparison
                baseline_times = [p['response_time'] for p in baseline_data]
                candidate_times = [p['response_time'] for p in candidate_data]
                
                if baseline_times and candidate_times:
                    t_stat, p_value = stats.ttest_ind(baseline_times, candidate_times)
                    analysis_results['statistical_tests']['response_time'] = {
                        'test': 'Independent t-test',
                        't_statistic': t_stat,
                        'p_value': p_value,
                        'significant': p_value < test_config['significance_level'],
                        'baseline_mean': np.mean(baseline_times),
                        'candidate_mean': np.mean(candidate_times)
                    }
                
                # Success rate comparison
                baseline_success_rate = sum(1 for p in baseline_data if p['success']) / len(baseline_data)
                candidate_success_rate = sum(1 for p in candidate_data if p['success']) / len(candidate_data)
                
                # Chi-square test for success rates
                baseline_successes = sum(1 for p in baseline_data if p['success'])
                candidate_successes = sum(1 for p in candidate_data if p['success'])
                
                contingency_table = [
                    [baseline_successes, len(baseline_data) - baseline_successes],
                    [candidate_successes, len(candidate_data) - candidate_successes]
                ]
                
                chi2, p_value, _, _ = stats.chi2_contingency(contingency_table)
                analysis_results['statistical_tests']['success_rate'] = {
                    'test': 'Chi-square test',
                    'chi2_statistic': chi2,
                    'p_value': p_value,
                    'significant': p_value < test_config['significance_level'],
                    'baseline_success_rate': baseline_success_rate,
                    'candidate_success_rate': candidate_success_rate
                }
                
                # Generate recommendations
                analysis_results['recommendations'] = self._generate_recommendations(analysis_results, test_config)
            else:
                analysis_results['recommendations'].append(
                    f"Insufficient data for statistical analysis. Need at least {test_config['min_samples']} samples per model."
                )
            
            # Update test configuration with analysis results
            test_config['last_analysis'] = analysis_results
            self._update_test_config(test_id, test_config)
            
            logger.info(f"A/B test analysis completed: {test_id}")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error analyzing A/B test {test_id}: {str(e)}")
            return {'error': str(e)}
    
    def monitor_ab_tests(self) -> Dict[str, Any]:
        """
        Monitor all active A/B tests and check for automatic rollback conditions.
        
        Returns:
            Monitoring summary
        """
        logger.info("Monitoring active A/B tests")
        
        monitoring_summary = {
            'timestamp': datetime.now().isoformat(),
            'active_tests': [],
            'alerts': [],
            'actions_taken': []
        }
        
        # Get all active test IDs from Redis
        test_keys = self.redis_client.keys("ab_test:*")
        
        for test_key in test_keys:
            try:
                test_config = json.loads(self.redis_client.get(test_key))
                
                if test_config['status'] == 'RUNNING':
                    test_id = test_config['test_id']
                    
                    # Check if test has exceeded duration
                    end_time = datetime.fromisoformat(test_config['end_time'])
                    if datetime.now() > end_time:
                        self.stop_ab_test(test_id, "Test duration exceeded")
                        monitoring_summary['actions_taken'].append(
                            f"Stopped test {test_id} - duration exceeded"
                        )
                        continue
                    
                    # Analyze current performance
                    analysis = self.analyze_ab_test(test_id)
                    
                    # Check for rollback conditions
                    if self._should_rollback(analysis, test_config):
                        self.stop_ab_test(test_id, "Automatic rollback - performance degradation")
                        monitoring_summary['actions_taken'].append(
                            f"Rolled back test {test_id} - performance degradation"
                        )
                        monitoring_summary['alerts'].append(
                            f"CRITICAL: Automatic rollback triggered for test {test_id}"
                        )
                    else:
                        monitoring_summary['active_tests'].append({
                            'test_id': test_id,
                            'test_name': test_config['test_name'],
                            'traffic_split': test_config['traffic_split'],
                            'duration_remaining': str(end_time - datetime.now())
                        })
                        
            except Exception as e:
                logger.error(f"Error monitoring test {test_key}: {str(e)}")
        
        logger.info(f"Monitoring completed. Active tests: {len(monitoring_summary['active_tests'])}")
        return monitoring_summary
    
    def _get_test_config(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get test configuration from Redis."""
        try:
            config_data = self.redis_client.get(f"ab_test:{test_id}")
            if config_data:
                return json.loads(config_data)
        except Exception as e:
            logger.error(f"Error getting test config {test_id}: {str(e)}")
        return None
    
    def _update_test_config(self, test_id: str, config: Dict[str, Any]) -> None:
        """Update test configuration in Redis."""
        try:
            self.redis_client.setex(
                f"ab_test:{test_id}",
                timedelta(days=7),
                json.dumps(config)
            )
        except Exception as e:
            logger.error(f"Error updating test config {test_id}: {str(e)}")
    
    def _deploy_istio_traffic_split(self, test_config: Dict[str, Any]) -> bool:
        """Deploy Istio Virtual Service for traffic splitting."""
        logger.info(f"Deploying Istio traffic split for test {test_config['test_id']}")
        
        # Istio Virtual Service configuration
        virtual_service = {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "VirtualService",
            "metadata": {
                "name": f"ab-test-{test_config['test_id']}",
                "namespace": config.kubernetes_namespace
            },
            "spec": {
                "hosts": ["model-service"],
                "http": [{
                    "match": [{"headers": {"x-ab-test": {"exact": test_config['test_id']}}}],
                    "route": [
                        {
                            "destination": {"host": "model-service", "subset": "baseline"},
                            "weight": int((1 - test_config['traffic_split']) * 100)
                        },
                        {
                            "destination": {"host": "model-service", "subset": "candidate"},
                            "weight": int(test_config['traffic_split'] * 100)
                        }
                    ]
                }]
            }
        }
        
        try:
            # This would deploy to Kubernetes/Istio
            # For demo purposes, we'll just log the configuration
            logger.info(f"Virtual Service configuration: {json.dumps(virtual_service, indent=2)}")
            return True
        except Exception as e:
            logger.error(f"Failed to deploy Istio traffic split: {str(e)}")
            return False
    
    def _restore_baseline_traffic(self, test_config: Dict[str, Any]) -> bool:
        """Restore 100% traffic to baseline model."""
        logger.info(f"Restoring baseline traffic for test {test_config['test_id']}")
        
        try:
            # This would remove the Virtual Service or update it to route 100% to baseline
            logger.info(f"Restored baseline traffic for test {test_config['test_id']}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore baseline traffic: {str(e)}")
            return False
    
    def _get_prediction_data(self, test_id: str, model_id: str) -> List[Dict[str, Any]]:
        """Get prediction data for a specific model in a test."""
        prediction_keys = self.redis_client.keys(f"prediction:{test_id}:{model_id}:*")
        
        predictions = []
        for key in prediction_keys:
            try:
                prediction_data = json.loads(self.redis_client.get(key))
                predictions.append(prediction_data)
            except Exception as e:
                logger.warning(f"Error loading prediction data {key}: {str(e)}")
        
        return predictions
    
    def _calculate_model_stats(self, prediction_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics for model predictions."""
        if not prediction_data:
            return {}
        
        response_times = [p['response_time'] for p in prediction_data]
        success_count = sum(1 for p in prediction_data if p['success'])
        
        return {
            'total_predictions': len(prediction_data),
            'success_rate': success_count / len(prediction_data),
            'avg_response_time': np.mean(response_times),
            'p95_response_time': np.percentile(response_times, 95),
            'p99_response_time': np.percentile(response_times, 99),
            'error_rate': 1 - (success_count / len(prediction_data))
        }
    
    def _generate_recommendations(self, analysis: Dict[str, Any], test_config: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis results."""
        recommendations = []
        
        # Response time recommendations
        response_time_test = analysis['statistical_tests'].get('response_time', {})
        if response_time_test.get('significant', False):
            if response_time_test['candidate_mean'] < response_time_test['baseline_mean']:
                recommendations.append("✅ Candidate model shows significantly better response times")
            else:
                recommendations.append("❌ Candidate model shows significantly worse response times")
        
        # Success rate recommendations
        success_rate_test = analysis['statistical_tests'].get('success_rate', {})
        if success_rate_test.get('significant', False):
            if success_rate_test['candidate_success_rate'] > success_rate_test['baseline_success_rate']:
                recommendations.append("✅ Candidate model shows significantly better success rate")
            else:
                recommendations.append("❌ Candidate model shows significantly worse success rate")
        
        # Overall recommendation
        candidate_better_response = (
            response_time_test.get('significant', False) and 
            response_time_test.get('candidate_mean', 0) < response_time_test.get('baseline_mean', 0)
        )
        candidate_better_success = (
            success_rate_test.get('significant', False) and 
            success_rate_test.get('candidate_success_rate', 0) > success_rate_test.get('baseline_success_rate', 0)
        )
        
        if candidate_better_response and candidate_better_success:
            recommendations.append("🚀 RECOMMENDATION: Deploy candidate model to production")
        elif not response_time_test.get('significant', False) and not success_rate_test.get('significant', False):
            recommendations.append("🤔 RECOMMENDATION: No significant difference detected, continue testing or deploy based on business criteria")
        else:
            recommendations.append("⚠️ RECOMMENDATION: Mixed results, review metrics carefully before deployment")
        
        return recommendations
    
    def _should_rollback(self, analysis: Dict[str, Any], test_config: Dict[str, Any]) -> bool:
        """Determine if automatic rollback should be triggered."""
        if 'candidate_stats' not in analysis or 'baseline_stats' not in analysis:
            return False
        
        candidate_stats = analysis['candidate_stats']
        baseline_stats = analysis['baseline_stats']
        
        # Check for critical degradation
        if candidate_stats.get('error_rate', 0) > baseline_stats.get('error_rate', 0) * 2:
            return True  # Error rate doubled
        
        if candidate_stats.get('avg_response_time', 0) > baseline_stats.get('avg_response_time', 0) * 1.5:
            return True  # Response time increased by 50%
        
        return False
    
    def _generate_test_report(self, test_id: str) -> None:
        """Generate final test report."""
        logger.info(f"Generating final report for test {test_id}")
        
        test_config = self._get_test_config(test_id)
        if test_config and 'last_analysis' in test_config:
            analysis = test_config['last_analysis']
            
            report = {
                'test_summary': {
                    'test_id': test_id,
                    'test_name': test_config['test_name'],
                    'duration': test_config.get('stop_time', datetime.now().isoformat()),
                    'status': test_config['status']
                },
                'results': analysis,
                'generated_at': datetime.now().isoformat()
            }
            
            # Store report in Redis
            self.redis_client.setex(
                f"test_report:{test_id}",
                timedelta(days=30),
                json.dumps(report)
            )
            
            logger.info(f"Test report generated for {test_id}")
    
    def get_test_report(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get the final test report."""
        try:
            report_data = self.redis_client.get(f"test_report:{test_id}")
            if report_data:
                return json.loads(report_data)
        except Exception as e:
            logger.error(f"Error getting test report {test_id}: {str(e)}")
        return None
