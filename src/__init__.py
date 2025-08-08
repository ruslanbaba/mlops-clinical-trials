"""
MLOps Clinical Trial Analytics Platform

A comprehensive platform for cancer research model training,
validation, and deployment with automated MLOps pipelines.
"""

__version__ = "1.0.0"
__author__ = "MLOps Clinical Trials Team"
__email__ = "team@mlops-clinical-trials.com"

from .config import Config
from .logger import get_logger

__all__ = ["Config", "get_logger"]
