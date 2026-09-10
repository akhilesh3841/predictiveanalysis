"""
Predictive Analytics Module

Provides:
- Multivariate PCA
- Multivariate correlation
- Multivariate regression
- ARIMA
- SARIMA
- Holt-Winters
- Forecast evaluation
"""

import logging
import warnings
import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error
)

from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)


# ============================================================
# MULTIVARIATE ANALYSIS
# ============================================================

class MultivariatePredictor:

    @staticmethod
    def correlation(df):
        """
        Calculate correlation matrix
        for numeric variables.
        """

        numeric_df = df.select_dtypes(
            include=[np.number]
        )

        if numeric_df.empty:
            raise ValueError(
                "No numeric variables available."
            )

        return numeric_df.corr()

    @staticmethod
    def pca(df, n_components=2):
        """
        Perform Principal Component Analysis.
        """

        numeric_df = df.select_dtypes(
            include=[np.number]
        ).copy()

        numeric_df = numeric_df.replace(
            [np.inf, -np.inf],
            np.nan
        ).dropna()

        if len(numeric_df) < 2:
            raise ValueError(
                "Not enough data for PCA."
            )

        if numeric_df.shape[1] < 2:
            raise ValueError(
                "At least two numeric variables "
                "are required for PCA."
            )

        n_components = min(
            int(n_components),
            numeric_df.shape[1]
        )

        scaler = StandardScaler()

        scaled_data = scaler.fit_transform(
            numeric_df
        )

        pca_model = PCA(
            n_components=n_components
        )

        transformed = pca_model.fit_transform(
            scaled_data
        )

        transformed_data = []

        for index, row in enumerate(
            transformed
        ):

            item = {
                "index": index
            }

            for i, value in enumerate(row):

                item[
                    f"PC{i + 1}"
                ] = float(value)

            transformed_data.append(item)

        return {

            "features": list(
                numeric_df.columns
            ),

            "n_components": n_components,

            "explained_variance_ratio": [
                float(x)
                for x in
                pca_model.explained_variance_ratio_
            ],

            "cumulative_explained_variance": [
                float(x)
                for x in
                np.cumsum(
                    pca_model.explained_variance_ratio_
                )
            ],

            "components": [
                [
                    float(x)
                    for x in component
                ]
                for component in
                pca_model.components_
            ],

            "transformed_data":
                transformed_data[-100:]

        }

    @staticmethod
    def regression(df, target="Revenue", features=None):
        """
        Multiple Linear Regression.

        Args:
            df: DataFrame with numeric columns
            target: Target variable name
            features: List of feature variable names (auto-detected if None)
        """

        if features is None:
            features = [
                c for c in df.select_dtypes(include=[np.number]).columns
                if c != target
            ]

        if not features:
            raise ValueError("No feature variables provided.")

        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found.")

        required_columns = features + [target]

        for column in required_columns:
            if column not in df.columns:
                raise ValueError(f"Missing column: {column}")

        data = df[required_columns].copy()

        data = data.replace(
            [np.inf, -np.inf],
            np.nan
        ).dropna()

        if len(data) < 10:
            raise ValueError("Not enough data for regression.")

        X = data[features]
        y = data[target]

        split_index = int(len(data) * 0.8)

        X_train = X.iloc[:split_index]
        X_test = X.iloc[split_index:]

        y_train = y.iloc[:split_index]
        y_test = y.iloc[split_index:]

        model = LinearRegression()
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)

        mae = mean_absolute_error(y_test, predictions)
        rmse = np.sqrt(mean_squared_error(y_test, predictions))

        coefficients = {}
        for i, feat in enumerate(features):
            coefficients[feat] = float(model.coef_[i])

        return {
            "model": "Multiple Linear Regression",
            "features": features,
            "target": target,
            "coefficients": coefficients,
            "intercept": float(model.intercept_),
            "r_squared": float(model.score(X_test, y_test)),
            "mae": float(mae),
            "rmse": float(rmse),
            "actual_vs_predicted": [
                {
                    "actual": float(actual),
                    "predicted": float(predicted)
                }
                for actual, predicted
                in zip(
                    y_test.tail(50),
                    predictions[-50:]
                )
            ]
        }


# ============================================================
# TIME SERIES
# ============================================================

class TimeSeriesPredictor:

    @staticmethod
    def prepare_series(
        dates,
        values
    ):
        """
        Prepare daily time series.
        """

        df = pd.DataFrame({
            "Date": pd.to_datetime(dates),
            "Value": pd.to_numeric(
                values,
                errors="coerce"
            )
        })

        df = df.dropna()

        df = df.sort_values(
            "Date"
        )

        # If duplicate dates exist,
        # aggregate them.
        df = (
            df.groupby("Date")["Value"]
            .sum()
            .sort_index()
        )

        if len(df) < 30:

            raise ValueError(
                "At least 30 observations "
                "are required for forecasting."
            )

        # Convert to daily frequency.
        # Missing days = zero sales.
        df = df.asfreq(
            "D",
            fill_value=0
        )

        return df.astype(float)

    # ========================================================
    # ARIMA
    # ========================================================

    @staticmethod
    def arima(
        series,
        forecast_days=30,
        order=(1, 1, 1)
    ):

        forecast_days = max(
            1,
            min(int(forecast_days), 180)
        )

        model = ARIMA(
            series,
            order=order
        )

        fitted = model.fit()

        forecast = fitted.forecast(
            steps=forecast_days
        )

        return {

            "model": "ARIMA",

            "order": list(order),

            "forecast_days":
                forecast_days,

            "predictions": [
                max(0, float(x))
                for x in forecast
            ],

            "aic": float(
                fitted.aic
            ),

            "bic": float(
                fitted.bic
            )

        }

    # ========================================================
    # SARIMA
    # ========================================================

    @staticmethod
    def sarima(
        series,
        forecast_days=30,
        order=(1, 1, 1),
        seasonal_order=(1, 1, 1, 7)
    ):

        forecast_days = max(
            1,
            min(int(forecast_days), 180)
        )

        model = SARIMAX(

            series,

            order=order,

            seasonal_order=seasonal_order,

            enforce_stationarity=False,

            enforce_invertibility=False

        )

        fitted = model.fit(
            disp=False
        )

        forecast = fitted.forecast(
            steps=forecast_days
        )

        return {

            "model": "SARIMA",

            "order": list(order),

            "seasonal_order":
                list(seasonal_order),

            "forecast_days":
                forecast_days,

            "predictions": [
                max(0, float(x))
                for x in forecast
            ],

            "aic": float(
                fitted.aic
            ),

            "bic": float(
                fitted.bic
            )

        }

    # ========================================================
    # HOLT-WINTERS
    # ========================================================

    @staticmethod
    def holt_winters(
        series,
        forecast_days=30,
        seasonal_periods=7
    ):

        forecast_days = max(
            1,
            min(int(forecast_days), 180)
        )

        seasonal_periods = max(
            2,
            min(int(seasonal_periods), 30)
        )

        if len(series) < (
            seasonal_periods * 2
        ):

            raise ValueError(
                "Not enough observations "
                "for Holt-Winters."
            )

        model = ExponentialSmoothing(

            series,

            trend="add",

            seasonal="add",

            seasonal_periods=
                seasonal_periods,

            initialization_method=
                "estimated"

        )

        fitted = model.fit(
            optimized=True
        )

        forecast = fitted.forecast(
            forecast_days
        )

        return {

            "model": "Holt-Winters",

            "seasonal_periods":
                seasonal_periods,

            "forecast_days":
                forecast_days,

            "predictions": [
                max(0, float(x))
                for x in forecast
            ],

            "aic": float(
                fitted.aic
            ),

            "bic": float(
                fitted.bic
            )

        }


# ============================================================
# FORECAST EVALUATION
# ============================================================

def calculate_mape(actual, predicted):

    actual = np.array(
        actual,
        dtype=float
    )

    predicted = np.array(
        predicted,
        dtype=float
    )

    mask = actual != 0

    if not np.any(mask):
        return 0.0

    return float(
        np.mean(
            np.abs(
                (
                    actual[mask]
                    - predicted[mask]
                )
                /
                actual[mask]
            )
        ) * 100
    )


def evaluate_forecast(
    actual,
    predicted
):

    actual = np.array(
        actual,
        dtype=float
    )

    predicted = np.array(
        predicted,
        dtype=float
    )

    mae = mean_absolute_error(
        actual,
        predicted
    )

    rmse = np.sqrt(
        mean_squared_error(
            actual,
            predicted
        )
    )

    mape = calculate_mape(
        actual,
        predicted
    )

    return {

        "MAE": float(mae),

        "RMSE": float(rmse),

        "MAPE": float(mape)

    }