"""
Data processors for various data transformation tasks.
"""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer, KNNImputer
from scipy import stats
import warnings

from ..logger import get_logger

logger = get_logger(__name__)


class DataProcessor:
    """
    Comprehensive data processor for clinical trial data.
    
    Handles missing values, outliers, scaling, encoding, and feature selection.
    """
    
    def __init__(self):
        """Initialize the data processor."""
        self.scalers = {}
        self.encoders = {}
        self.imputers = {}
        logger.info("Data processor initialized")
    
    def handle_missing_values(
        self, 
        data: pd.DataFrame, 
        strategy: str = 'median',
        threshold: float = 0.5
    ) -> pd.DataFrame:
        """
        Handle missing values in the dataset.
        
        Args:
            data: Input DataFrame
            strategy: Imputation strategy ('mean', 'median', 'mode', 'knn', 'drop')
            threshold: Threshold for dropping columns with too many missing values
            
        Returns:
            DataFrame with handled missing values
        """
        logger.info(f"Handling missing values with strategy: {strategy}")
        
        # Drop columns with too many missing values
        missing_percentages = data.isnull().sum() / len(data)
        columns_to_drop = missing_percentages[missing_percentages > threshold].index
        
        if len(columns_to_drop) > 0:
            logger.info(f"Dropping columns with >{threshold*100}% missing: {list(columns_to_drop)}")
            data = data.drop(columns=columns_to_drop)
        
        # Separate numeric and categorical columns
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        categorical_columns = data.select_dtypes(exclude=[np.number]).columns
        
        # Handle numeric columns
        if len(numeric_columns) > 0:
            if strategy == 'knn':
                imputer = KNNImputer(n_neighbors=5)
                data[numeric_columns] = imputer.fit_transform(data[numeric_columns])
                self.imputers['numeric'] = imputer
            else:
                imputer = SimpleImputer(strategy=strategy)
                data[numeric_columns] = imputer.fit_transform(data[numeric_columns])
                self.imputers['numeric'] = imputer
        
        # Handle categorical columns
        if len(categorical_columns) > 0:
            imputer = SimpleImputer(strategy='most_frequent')
            data[categorical_columns] = imputer.fit_transform(data[categorical_columns])
            self.imputers['categorical'] = imputer
        
        logger.info("Missing value handling completed")
        return data
    
    def remove_outliers(
        self, 
        data: pd.DataFrame, 
        method: str = 'iqr',
        threshold: float = 3.0
    ) -> pd.DataFrame:
        """
        Remove outliers from the dataset.
        
        Args:
            data: Input DataFrame
            method: Outlier detection method ('iqr', 'zscore', 'isolation_forest')
            threshold: Threshold for outlier detection
            
        Returns:
            DataFrame with outliers removed
        """
        logger.info(f"Removing outliers using {method} method")
        initial_count = len(data)
        
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        
        if method == 'iqr':
            # Interquartile Range method
            for column in numeric_columns:
                Q1 = data[column].quantile(0.25)
                Q3 = data[column].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                data = data[(data[column] >= lower_bound) & (data[column] <= upper_bound)]
        
        elif method == 'zscore':
            # Z-score method
            z_scores = np.abs(stats.zscore(data[numeric_columns]))
            data = data[(z_scores < threshold).all(axis=1)]
        
        elif method == 'isolation_forest':
            from sklearn.ensemble import IsolationForest
            
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            outlier_labels = iso_forest.fit_predict(data[numeric_columns])
            data = data[outlier_labels == 1]
        
        removed_count = initial_count - len(data)
        logger.info(f"Removed {removed_count} outliers ({removed_count/initial_count*100:.2f}%)")
        
        return data
    
    def scale_features(
        self, 
        data: pd.DataFrame, 
        method: str = 'standard',
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Scale numerical features.
        
        Args:
            data: Input DataFrame
            method: Scaling method ('standard', 'minmax', 'robust')
            columns: Specific columns to scale (if None, scale all numeric)
            
        Returns:
            DataFrame with scaled features
        """
        logger.info(f"Scaling features using {method} method")
        
        if columns is None:
            columns = data.select_dtypes(include=[np.number]).columns.tolist()
        
        if method == 'standard':
            scaler = StandardScaler()
        elif method == 'minmax':
            scaler = MinMaxScaler()
        elif method == 'robust':
            scaler = RobustScaler()
        else:
            raise ValueError(f"Unsupported scaling method: {method}")
        
        data_scaled = data.copy()
        data_scaled[columns] = scaler.fit_transform(data[columns])
        
        self.scalers[method] = scaler
        logger.info(f"Scaled {len(columns)} features")
        
        return data_scaled
    
    def encode_categorical(
        self, 
        data: pd.DataFrame, 
        method: str = 'onehot',
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Encode categorical variables.
        
        Args:
            data: Input DataFrame
            method: Encoding method ('onehot', 'label', 'target')
            columns: Specific columns to encode (if None, encode all categorical)
            
        Returns:
            DataFrame with encoded features
        """
        logger.info(f"Encoding categorical variables using {method} method")
        
        if columns is None:
            columns = data.select_dtypes(exclude=[np.number]).columns.tolist()
        
        data_encoded = data.copy()
        
        if method == 'onehot':
            for column in columns:
                # Create dummy variables
                dummies = pd.get_dummies(data[column], prefix=column)
                data_encoded = pd.concat([data_encoded, dummies], axis=1)
                data_encoded = data_encoded.drop(columns=[column])
        
        elif method == 'label':
            for column in columns:
                encoder = LabelEncoder()
                data_encoded[column] = encoder.fit_transform(data[column].astype(str))
                self.encoders[column] = encoder
        
        logger.info(f"Encoded {len(columns)} categorical features")
        return data_encoded
    
    def select_features(
        self, 
        X: pd.DataFrame, 
        y: pd.Series,
        method: str = 'k_best',
        k: int = 10
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Select the most important features.
        
        Args:
            X: Feature DataFrame
            y: Target Series
            method: Feature selection method ('k_best', 'mutual_info', 'pca')
            k: Number of features to select
            
        Returns:
            Tuple of (selected features DataFrame, feature names)
        """
        logger.info(f"Selecting {k} features using {method} method")
        
        if method == 'k_best':
            selector = SelectKBest(score_func=f_classif, k=k)
            X_selected = selector.fit_transform(X, y)
            selected_features = X.columns[selector.get_support()].tolist()
            
        elif method == 'mutual_info':
            selector = SelectKBest(score_func=mutual_info_classif, k=k)
            X_selected = selector.fit_transform(X, y)
            selected_features = X.columns[selector.get_support()].tolist()
            
        elif method == 'pca':
            pca = PCA(n_components=k)
            X_selected = pca.fit_transform(X)
            selected_features = [f'PC_{i+1}' for i in range(k)]
            X_selected = pd.DataFrame(X_selected, columns=selected_features, index=X.index)
            
        else:
            raise ValueError(f"Unsupported feature selection method: {method}")
        
        if method != 'pca':
            X_selected = pd.DataFrame(X_selected, columns=selected_features, index=X.index)
        
        logger.info(f"Selected features: {selected_features}")
        return X_selected, selected_features
    
    def create_interaction_features(
        self, 
        data: pd.DataFrame, 
        max_interactions: int = 5
    ) -> pd.DataFrame:
        """
        Create interaction features between numerical variables.
        
        Args:
            data: Input DataFrame
            max_interactions: Maximum number of interaction features to create
            
        Returns:
            DataFrame with interaction features
        """
        logger.info("Creating interaction features")
        
        numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_columns) < 2:
            logger.warning("Not enough numeric columns for interaction features")
            return data
        
        data_with_interactions = data.copy()
        interaction_count = 0
        
        for i in range(len(numeric_columns)):
            for j in range(i + 1, len(numeric_columns)):
                if interaction_count >= max_interactions:
                    break
                
                col1, col2 = numeric_columns[i], numeric_columns[j]
                interaction_name = f"{col1}_x_{col2}"
                
                # Create multiplicative interaction
                data_with_interactions[interaction_name] = data[col1] * data[col2]
                interaction_count += 1
        
        logger.info(f"Created {interaction_count} interaction features")
        return data_with_interactions
    
    def create_polynomial_features(
        self, 
        data: pd.DataFrame, 
        degree: int = 2,
        max_features: int = 10
    ) -> pd.DataFrame:
        """
        Create polynomial features for numerical variables.
        
        Args:
            data: Input DataFrame
            degree: Polynomial degree
            max_features: Maximum number of polynomial features to create
            
        Returns:
            DataFrame with polynomial features
        """
        logger.info(f"Creating polynomial features (degree={degree})")
        
        numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        data_with_poly = data.copy()
        
        feature_count = 0
        for column in numeric_columns[:max_features]:
            if feature_count >= max_features:
                break
                
            for d in range(2, degree + 1):
                poly_name = f"{column}_poly_{d}"
                data_with_poly[poly_name] = data[column] ** d
                feature_count += 1
        
        logger.info(f"Created {feature_count} polynomial features")
        return data_with_poly
    
    def detect_data_drift(
        self, 
        reference_data: pd.DataFrame, 
        current_data: pd.DataFrame,
        threshold: float = 0.05
    ) -> Dict[str, Any]:
        """
        Detect data drift between reference and current datasets.
        
        Args:
            reference_data: Reference dataset
            current_data: Current dataset to compare
            threshold: P-value threshold for drift detection
            
        Returns:
            Dictionary with drift detection results
        """
        logger.info("Detecting data drift")
        
        drift_results = {
            'has_drift': False,
            'drifted_features': [],
            'drift_scores': {},
            'summary': {}
        }
        
        common_columns = set(reference_data.columns) & set(current_data.columns)
        numeric_columns = reference_data[list(common_columns)].select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            try:
                # Kolmogorov-Smirnov test
                ks_statistic, p_value = stats.ks_2samp(
                    reference_data[column].dropna(),
                    current_data[column].dropna()
                )
                
                drift_results['drift_scores'][column] = {
                    'ks_statistic': ks_statistic,
                    'p_value': p_value,
                    'has_drift': p_value < threshold
                }
                
                if p_value < threshold:
                    drift_results['drifted_features'].append(column)
                    drift_results['has_drift'] = True
                    
            except Exception as e:
                logger.warning(f"Could not test drift for column {column}: {str(e)}")
        
        drift_results['summary'] = {
            'total_features_tested': len(numeric_columns),
            'features_with_drift': len(drift_results['drifted_features']),
            'drift_percentage': len(drift_results['drifted_features']) / len(numeric_columns) * 100
        }
        
        logger.info(f"Data drift detection completed. Drift detected: {drift_results['has_drift']}")
        return drift_results
