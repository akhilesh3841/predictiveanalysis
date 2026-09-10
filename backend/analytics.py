"""
Analytics Module for Statistical Analysis
Provides univariate, bivariate, and multivariate analysis functions
"""
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class UnivariateAnalyzer:
    """Univariate statistical analysis"""
    
    @staticmethod
    def get_statistical_summary(data):
        """Calculate statistical summary for a numeric series"""
        try:
            data = np.array([x for x in data if isinstance(x, (int, float))])
            if len(data) == 0:
                return None
            
            return {
                'count': int(len(data)),
                'mean': float(np.mean(data)),
                'median': float(np.median(data)),
                'std': float(np.std(data)),
                'variance': float(np.var(data)),
                'min': float(np.min(data)),
                'max': float(np.max(data)),
                'q1': float(np.percentile(data, 25)),
                'q3': float(np.percentile(data, 75)),
                'iqr': float(np.percentile(data, 75) - np.percentile(data, 25)),
                'skewness': float(stats.skew(data)),
                'kurtosis': float(stats.kurtosis(data))
            }
        except Exception as e:
            logger.error(f"Error calculating statistical summary: {e}")
            return None
    
    @staticmethod
    def get_distribution(data, bins=20):
        """Get distribution data for histogram"""
        try:
            data = np.array([x for x in data if isinstance(x, (int, float))])
            if len(data) == 0:
                return None
            
            counts, bin_edges = np.histogram(data, bins=bins)
            bin_centers = [(bin_edges[i] + bin_edges[i+1])/2 for i in range(len(bin_edges)-1)]
            
            return [
                {
                    'bin': float(bin_centers[i]),
                    'count': int(counts[i]),
                    'range': f"{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}"
                }
                for i in range(len(counts))
            ]
        except Exception as e:
            logger.error(f"Error calculating distribution: {e}")
            return None
    
    @staticmethod
    def detect_outliers(data):
        """Detect outliers using IQR method"""
        try:
            data = np.array([x for x in data if isinstance(x, (int, float))])
            if len(data) < 4:
                return []
            
            q1 = np.percentile(data, 25)
            q3 = np.percentile(data, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outliers = []
            for val in data:
                if val < lower_bound or val > upper_bound:
                    outliers.append({
                        'value': float(val),
                        'type': 'lower' if val < lower_bound else 'upper',
                        'threshold': float(lower_bound) if val < lower_bound else float(upper_bound)
                    })
            
            return sorted(outliers, key=lambda x: abs(x['value'] - (q1 if x['type'] == 'lower' else q3)))
        except Exception as e:
            logger.error(f"Error detecting outliers: {e}")
            return []
    
    @staticmethod
    def normality_test(data):
        """Test normality using Shapiro-Wilk test"""
        try:
            data = np.array([x for x in data if isinstance(x, (int, float))])
            if len(data) < 3:
                return None
            
            statistic, p_value = stats.shapiro(data)
            
            return {
                'test': 'Shapiro-Wilk',
                'statistic': float(statistic),
                'p_value': float(p_value),
                'is_normal': p_value > 0.05,
                'interpretation': 'Data is normally distributed' if p_value > 0.05 else 'Data is NOT normally distributed'
            }
        except Exception as e:
            logger.error(f"Error in normality test: {e}")
            return None
    
    @staticmethod
    def get_qq_plot_data(data, sample_size=100):
        """Get Q-Q plot data for normality visualization"""
        try:
            data = np.array([x for x in data if isinstance(x, (int, float))])
            if len(data) < 3:
                return None
            
            # Sample if data is too large
            if len(data) > sample_size:
                data = np.random.choice(data, sample_size, replace=False)
            
            # Standardize the data
            standardized = (data - np.mean(data)) / np.std(data)
            standardized = np.sort(standardized)
            
            # Theoretical quantiles
            n = len(standardized)
            theoretical = np.sort(stats.norm.ppf(np.arange(1, n+1) / (n+1)))
            
            return [
                {
                    'theoretical': float(theoretical[i]),
                    'sample': float(standardized[i])
                }
                for i in range(len(theoretical))
            ]
        except Exception as e:
            logger.error(f"Error generating Q-Q plot data: {e}")
            return None


class BivariateAnalyzer:
    """Bivariate statistical analysis"""
    
    @staticmethod
    def correlation_matrix(data_dict):
        """Calculate correlation matrix for multiple variables"""
        try:
            # Convert dict of lists to numpy array
            data_array = np.array([data_dict[key] for key in sorted(data_dict.keys())]).T
            corr_matrix = np.corrcoef(data_array.T)
            
            keys = sorted(data_dict.keys())
            return {
                'variables': keys,
                'correlations': [[float(corr_matrix[i][j]) for j in range(len(keys))] for i in range(len(keys))]
            }
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return None
    
    @staticmethod
    def linear_regression(x_data, y_data):
        """Perform simple linear regression"""
        try:
            x = np.array([v for v in x_data if isinstance(v, (int, float))])
            y = np.array([v for v in y_data if isinstance(v, (int, float))])
            
            if len(x) < 2:
                return None
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            return {
                'slope': float(slope),
                'intercept': float(intercept),
                'r_squared': float(r_value ** 2),
                'p_value': float(p_value),
                'std_error': float(std_err),
                'equation': f"y = {slope:.4f}x + {intercept:.4f}"
            }
        except Exception as e:
            logger.error(f"Error in linear regression: {e}")
            return None
