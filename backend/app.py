"""
Retail Analytics & Demand Intelligence
Flask Backend API

Sections:
    1. Dashboard
    2. Univariate Analysis
    3. Bivariate Analysis
    4. Predictive - Multivariate
    5. Predictive - Time Series
       - ARIMA
       - SARIMA
       - Holt-Winters
"""

# ============================================================
# IMPORTS
# ============================================================

from flask import Flask, app, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

import logging
import os
import math
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats

from db import db as db_instance
from config import config

from analytics import (
    UnivariateAnalyzer,
    BivariateAnalyzer
)

from predictive import (
    MultivariatePredictor,
    TimeSeriesPredictor,
    evaluate_forecast
)

from inventory import (
    calculate_abc,
    calculate_xyz,
    calculate_abc_xyz_matrix,
    get_product_demand_trend,
    load_transactions,
    load_product_daily,
)


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# JSON CLEANER
# ============================================================

def clean_for_json(value):
    """
    Convert NumPy/Pandas/Python values into
    JSON-safe values.
    """

    if isinstance(value, dict):
        return {
            key: clean_for_json(val)
            for key, val in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            clean_for_json(val)
            for val in value
        ]

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.bool_):
        return bool(value)

    if isinstance(value, np.floating):
        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            return None

        return value

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, np.ndarray):
        return value.tolist()

    return value


# ============================================================
# INVENTORY ANALYSIS HELPERS
# ============================================================

def _empty_abc_summary():
    return {
        "total_items": 0,
        "total_value": 0.0,
        "counts": {"A": 0, "B": 0, "C": 0},
        "value_by_class": {"A": 0.0, "B": 0.0, "C": 0.0},
        "value_pct_a": 0.0,
        "value_pct_b": 0.0,
        "value_pct_c": 0.0,
        "value_metric": "Revenue",
        "thresholds": {"a": 0.80, "b": 0.95},
    }


def _empty_xyz_summary():
    return {
        "total_items": 0,
        "counts": {"X": 0, "Y": 0, "Z": 0, "ND": 0, "U": 0},
        "average_cv": 0.0,
        "most_stable": None,
        "most_variable": None,
        "thresholds": {"x": 0.50, "y": 1.00},
        "min_periods": 2,
        "total_periods": 0,
    }


def _xyz_label(xyz_class):
    return {
        "X": "Stable",
        "Y": "Moderately Variable",
        "Z": "Highly Variable",
        "ND": "No Demand",
        "U": "Unclassified",
    }.get(xyz_class, xyz_class)


def _pareto_aggregate(items, top_n=100):
    """
    Aggregate the top-N highest value items for the
    Pareto chart so very large result sets can be
    rendered without loading every bar.

    The aggregation is display-only; it never changes
    the underlying ABC classification.
    """

    if not items:
        return []

    if len(items) <= top_n:
        return [
            {
                "rank": item["rank"],
                "name": item["product_name"],
                "value": item["consumption_value"],
                "contribution_pct": item["contribution_pct"],
                "cumulative_pct": item["cumulative_pct"],
                "class": item["class"],
            }
            for item in items
        ]

    top = items[:top_n]

    remaining_value = sum(
        item["consumption_value"]
        for item in items[top_n:]
    )

    remaining_contribution = sum(
        item["contribution_pct"]
        for item in items[top_n:]
    )

    last_cumulative = top[-1]["cumulative_pct"]

    rows = [
        {
            "rank": item["rank"],
            "name": item["product_name"],
            "value": item["consumption_value"],
            "contribution_pct": item["contribution_pct"],
            "cumulative_pct": item["cumulative_pct"],
            "class": item["class"],
        }
        for item in top
    ]

    rows.append(
        {
            "rank": top_n + 1,
            "name": f"Remaining {len(items) - top_n} items",
            "value": remaining_value,
            "contribution_pct": remaining_contribution,
            "cumulative_pct": last_cumulative
            + remaining_contribution,
            "class": "C",
        }
    )

    return rows


# ============================================================
# DATABASE
# ============================================================

def get_db():
    """
    Return MongoDB database instance.
    """

    return db_instance.get_db()


# ============================================================
# GENERIC NUMERIC DATA HELPER
# ============================================================

NUMERIC_FIELDS = {
    "Revenue",
    "Quantity",
    "UnitPrice",
    "Transactions"
}


def validate_numeric_field(field):
    return field in NUMERIC_FIELDS


def get_numeric_data(
    db,
    collection_name,
    field,
    limit=None
):
    """
    Fetch one numeric field from MongoDB.

    Only the requested field is fetched.
    """

    collection = db[collection_name]

    query = {
        field: {
            "$exists": True,
            "$ne": None
        }
    }

    projection = {
        "_id": 0,
        field: 1
    }

    cursor = collection.find(
        query,
        projection
    )

    if limit:
        cursor = cursor.limit(limit)

    values = []

    for document in cursor:

        value = document.get(field)

        try:

            value = float(value)

            if math.isfinite(value):
                values.append(value)

        except (
            TypeError,
            ValueError
        ):
            continue

    return values


# ============================================================
# PAIRED DATA HELPER
# ============================================================

def get_paired_numeric_data(
    db,
    collection_name,
    x_field,
    y_field,
    limit=None
):
    """
    Fetch two numeric fields as paired arrays.
    """

    collection = db[collection_name]

    query = {
        x_field: {
            "$exists": True,
            "$ne": None
        },
        y_field: {
            "$exists": True,
            "$ne": None
        }
    }

    projection = {
        "_id": 0,
        x_field: 1,
        y_field: 1
    }

    cursor = collection.find(
        query,
        projection
    )

    if limit:
        cursor = cursor.limit(limit)

    x_values = []
    y_values = []

    for document in cursor:

        try:

            x = float(
                document[x_field]
            )

            y = float(
                document[y_field]
            )

            if (
                math.isfinite(x)
                and math.isfinite(y)
            ):
                x_values.append(x)
                y_values.append(y)

        except (
            TypeError,
            ValueError,
            KeyError
        ):
            continue

    return x_values, y_values


# ============================================================
# DAILY DATA FOR PREDICTIVE ANALYSIS
# ============================================================

def get_daily_predictive_data(db):
    """
    Read daily_sales collection.

    Fields:
        Date
        Quantity
        Revenue
        Transactions
    """

    cursor = (
        db["daily_sales"]
        .find(
            {},
            {
                "_id": 0,
                "Date": 1,
                "Quantity": 1,
                "Revenue": 1,
                "Transactions": 1
            }
        )
        .sort(
            "Date",
            1
        )
    )

    rows = []

    for document in cursor:

        try:

            date = pd.to_datetime(
                document.get("Date")
            )

            quantity = float(
                document.get(
                    "Quantity",
                    0
                )
            )

            revenue = float(
                document.get(
                    "Revenue",
                    0
                )
            )

            transactions = float(
                document.get(
                    "Transactions",
                    0
                )
            )

            if pd.isna(date):
                continue

            if not all(
                math.isfinite(x)
                for x in [
                    quantity,
                    revenue,
                    transactions
                ]
            ):
                continue

            rows.append(
                {
                    "Date": date,
                    "Quantity": quantity,
                    "Revenue": revenue,
                    "Transactions": transactions
                }
            )

        except (
            TypeError,
            ValueError,
            KeyError
        ):
            continue

    return rows


# ============================================================
# FORECASTING SERIES
# ============================================================

def get_forecasting_series(
    db,
    metric="Revenue",
    start_date=None,
    end_date=None
):
    """
    Create daily time series.

    Allowed:
        Revenue
        Quantity
        Transactions
    """

    allowed_metrics = {
        "Revenue",
        "Quantity",
        "Transactions"
    }

    if metric not in allowed_metrics:

        raise ValueError(
            "Invalid metric. Allowed metrics: "
            "Revenue, Quantity, Transactions"
        )

    rows = get_daily_predictive_data(db)

    if not rows:

        raise ValueError(
            "No daily sales data found."
        )

    df = pd.DataFrame(rows)

    if start_date:

        try:

            start_dt = pd.to_datetime(start_date)

            df = df[
                df["Date"] >= start_dt
            ]

        except Exception:

            pass

    if end_date:

        try:

            end_dt = pd.to_datetime(end_date)

            df = df[
                df["Date"] <= end_dt
            ]

        except Exception:

            pass

    if df.empty:

        raise ValueError(
            "No data found for the selected "
            "date range."
        )

    series = (
        TimeSeriesPredictor
        .prepare_series(
            df["Date"],
            df[metric]
        )
    )

    return series


# ============================================================
# FORECAST RESPONSE
# ============================================================

def create_forecast_response(
    series,
    result,
    metric
):
    """
    Convert forecasting result into
    frontend-friendly JSON.
    """

    last_date = series.index[-1]

    forecast_days = int(
        result["forecast_days"]
    )

    predictions = result[
        "predictions"
    ]

    forecast_dates = pd.date_range(
        start=(
            last_date
            + pd.Timedelta(days=1)
        ),
        periods=forecast_days,
        freq="D"
    )

    forecast_data = []

    for date, prediction in zip(
        forecast_dates,
        predictions
    ):

        forecast_data.append(
            {
                "date": date.strftime(
                    "%Y-%m-%d"
                ),
                "forecast": float(
                    prediction
                )
            }
        )

    history = []

    for date, value in (
        series.tail(90).items()
    ):

        history.append(
            {
                "date": date.strftime(
                    "%Y-%m-%d"
                ),
                "actual": float(value)
            }
        )

    model_details = {
        key: value
        for key, value in result.items()
        if key not in {
            "model",
            "forecast_days",
            "predictions"
        }
    }

    return clean_for_json(
        {
            "metric": metric,
            "model": result["model"],
            "forecast_days": forecast_days,
            "last_date": last_date.strftime(
                "%Y-%m-%d"
            ),
            "history": history,
            "forecast": forecast_data,
            "model_details": model_details
        }
    )


# ============================================================
# CREATE FLASK APP
# ============================================================

def create_app(
    env="development"
):

    app = Flask(__name__)

    # --------------------------------------------------------
    # Flask configuration
    # --------------------------------------------------------

    app.config.from_object(
        config.get(
            env,
            config["development"]
        )
    )

    # --------------------------------------------------------
    # CORS
    # --------------------------------------------------------

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": "*",
                "methods": [
                    "GET",
                    "POST",
                    "PUT",
                    "DELETE"
                ],
                "allow_headers": [
                    "Content-Type"
                ]
            }
        }
    )

    # ========================================================
    # DATABASE CONNECTION
    # ========================================================

    @app.before_request
    def before_request():

        if db_instance._db is None:

            db_instance.connect()

    @app.teardown_appcontext
    def teardown_db(exception=None):

        pass

    # ========================================================
    # HEALTH CHECK
    # ========================================================

    @app.route(
        "/health",
        methods=["GET"]
    )
    def health():

        try:

            db = get_db()

            db.command("ping")

            return jsonify(
                {
                    "status": "healthy",
                    "timestamp": (
                        datetime.now()
                        .isoformat()
                    ),
                    "database": "connected"
                }
            ), 200

        except Exception as e:

            logger.exception(
                f"Health check error: {e}"
            )

            return jsonify(
                {
                    "status": "unhealthy",
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # DASHBOARD
    # ========================================================

    @app.route(
        '/api/dashboard/kpis', methods=['GET']
    )
    def get_dashboard_kpis():

        try:

            db = get_db()

            transactions = db[
                "transactions"
            ]

            products = db[
                "products"
            ]

            customers = db[
                "customers"
            ]

            total_products = (
                products.count_documents({})
            )

            total_customers = (
                customers.count_documents({})
            )

            total_transactions = (
                transactions.count_documents({})
            )

            revenue_result = list(
                transactions.aggregate(
                    [
                        {
                            "$group": {
                                "_id": None,
                                "total": {
                                    "$sum": "$Revenue"
                                }
                            }
                        }
                    ]
                )
            )

            total_revenue = (
                revenue_result[0]["total"]
                if revenue_result
                else 0
            )

            units_result = list(
                transactions.aggregate(
                    [
                        {
                            "$group": {
                                "_id": None,
                                "total": {
                                    "$sum": "$Quantity"
                                }
                            }
                        }
                    ]
                )
            )

            total_units = (
                units_result[0]["total"]
                if units_result
                else 0
            )

            countries_result = list(
                transactions.aggregate(
                    [
                        {
                            "$group": {
                                "_id": "$Country"
                            }
                        }
                    ]
                )
            )

            total_countries = len(
                countries_result
            )

            return jsonify(
                clean_for_json(
                    {
                        "total_products":
                            total_products,

                        "total_customers":
                            total_customers,

                        "total_transactions":
                            total_transactions,

                        "total_revenue":
                            round(
                                float(
                                    total_revenue
                                ),
                                2
                            ),

                        "total_units":
                            int(
                                total_units
                            ),

                        "total_countries":
                            total_countries,

                        "timestamp":
                            datetime.now()
                            .isoformat()
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Dashboard KPI error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # MONTHLY REVENUE
    # ========================================================

    @app.route('/api/dashboard/monthly-revenue', methods=['GET'])

    def get_monthly_revenue():

        try:

            db = get_db()

            pipeline = [

                {
                    "$group": {
                        "_id": {
                            "year": {
                                "$year": "$Date"
                            },
                            "month": {
                                "$month": "$Date"
                            }
                        },

                        "revenue": {
                            "$sum": "$Revenue"
                        },

                        "quantity": {
                            "$sum": "$Quantity"
                        }
                    }
                },

                {
                    "$sort": {
                        "_id.year": 1,
                        "_id.month": 1
                    }
                },

                {
                    "$limit": 24
                }
            ]

            results = list(
                db[
                    "daily_sales"
                ].aggregate(
                    pipeline
                )
            )

            data = []

            for row in results:

                data.append(
                    {
                        "month": (
                            f"{row['_id']['year']}-"
                            f"{row['_id']['month']:02d}"
                        ),

                        "revenue": round(
                            float(
                                row["revenue"]
                            ),
                            2
                        ),

                        "quantity": int(
                            row["quantity"]
                        )
                    }
                )

            return jsonify(
                clean_for_json(data)
            ), 200

        except Exception as e:

            logger.exception(
                f"Monthly revenue error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # TOP PRODUCTS
    # ========================================================

    @app.route('/api/dashboard/top-products', methods=['GET'])

    def get_top_products():

        try:

            limit = request.args.get(
                "limit",
                10,
                type=int
            )

            limit = max(
                1,
                min(limit, 100)
            )

            db = get_db()

            results = list(
                db[
                    "transactions"
                ].aggregate(
                    [

                        {
                            "$group": {

                                "_id":
                                    "$ProductID",

                                "product_name":
                                    {
                                        "$first":
                                            "$ProductName"
                                    },

                                "revenue":
                                    {
                                        "$sum":
                                            "$Revenue"
                                    },

                                "quantity":
                                    {
                                        "$sum":
                                            "$Quantity"
                                    },

                                "transactions":
                                    {
                                        "$sum": 1
                                    }
                            }
                        },

                        {
                            "$sort": {
                                "revenue": -1
                            }
                        },

                        {
                            "$limit": limit
                        }
                    ]
                )
            )

            data = []

            for row in results:

                data.append(
                    {
                        "product_id":
                            row["_id"],

                        "product_name":
                            row.get(
                                "product_name"
                            )
                            or "Unknown",

                        "revenue":
                            round(
                                float(
                                    row.get(
                                        "revenue",
                                        0
                                    )
                                ),
                                2
                            ),

                        "quantity":
                            int(
                                row.get(
                                    "quantity",
                                    0
                                )
                            ),

                        "transactions":
                            int(
                                row.get(
                                    "transactions",
                                    0
                                )
                            )
                    }
                )

            return jsonify(
                clean_for_json(data)
            ), 200

        except Exception as e:

            logger.exception(
                f"Top products error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # TOP COUNTRIES
    # ========================================================

    @app.route('/api/dashboard/top-countries', methods=['GET'])

    def get_top_countries():

        try:

            limit = request.args.get(
                "limit",
                15,
                type=int
            )

            limit = max(
                1,
                min(limit, 100)
            )

            db = get_db()

            results = list(
                db[
                    "transactions"
                ].aggregate(
                    [

                        {
                            "$group": {

                                "_id":
                                    "$Country",

                                "revenue":
                                    {
                                        "$sum":
                                            "$Revenue"
                                    },

                                "quantity":
                                    {
                                        "$sum":
                                            "$Quantity"
                                    },

                                "transactions":
                                    {
                                        "$sum": 1
                                    }
                            }
                        },

                        {
                            "$sort": {
                                "revenue": -1
                            }
                        },

                        {
                            "$limit": limit
                        }
                    ]
                )
            )

            data = []

            for row in results:

                data.append(
                    {
                        "country":
                            row["_id"],

                        "revenue":
                            round(
                                float(
                                    row.get(
                                        "revenue",
                                        0
                                    )
                                ),
                                2
                            ),

                        "quantity":
                            int(
                                row.get(
                                    "quantity",
                                    0
                                )
                            ),

                        "transactions":
                            int(
                                row.get(
                                    "transactions",
                                    0
                                )
                            )
                    }
                )

            return jsonify(
                clean_for_json(data)
            ), 200

        except Exception as e:

            logger.exception(
                f"Top countries error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # DATA SUMMARY
    # ========================================================

    @app.route(
        "/api/data/summary",
        methods=["GET"]
    )
    def get_data_summary():

        try:

            db = get_db()

            collections = [
                "transactions",
                "products",
                "customers",
                "daily_sales",
                "monthly_sales",
                "product_daily_sales"
            ]

            summary = {
                "collections": {}
            }

            for collection_name in collections:

                collection = db[
                    collection_name
                ]

                count = (
                    collection.count_documents({})
                )

                summary[
                    "collections"
                ][collection_name] = {

                    "count": count,

                    "sample": (
                        collection.find_one()
                        is not None
                    )
                }

            return jsonify(
                summary
            ), 200

        except Exception as e:

            logger.exception(
                f"Data summary error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # DATA DATE RANGE
    # ========================================================

    @app.route(
        "/api/data/date-range",
        methods=["GET"]
    )
    def get_date_range():

        try:

            db = get_db()

            rows = get_daily_predictive_data(db)

            if not rows:

                return jsonify(
                    {
                        "error":
                            "No daily data found."
                    }
                ), 404

            df = pd.DataFrame(rows)

            min_date = df["Date"].min()
            max_date = df["Date"].max()

            return jsonify(
                clean_for_json(
                    {
                        "min_date":
                            min_date.strftime(
                                "%Y-%m-%d"
                            ),
                        "max_date":
                            max_date.strftime(
                                "%Y-%m-%d"
                            )
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Date range error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # UNIVARIATE - SUMMARY
    # ========================================================

    @app.route(
        "/api/univariate/summary",
        methods=["GET"]
    )
    def univariate_summary():

        try:

            field = request.args.get(
                "field",
                "Revenue"
            )

            if not validate_numeric_field(
                field
            ):

                return jsonify(
                    {
                        "error": (
                            "Invalid field. "
                            "Allowed fields: "
                            "Revenue, Quantity, UnitPrice"
                        )
                    }
                ), 400

            db = get_db()

            data = get_numeric_data(
                db,
                "transactions",
                field
            )

            if not data:

                return jsonify(
                    {
                        "error":
                            f"No numeric data found for {field}"
                    }
                ), 404

            result = (
                UnivariateAnalyzer
                .get_statistical_summary(
                    data
                )
            )

            return jsonify(
                clean_for_json(
                    {
                        "collection":
                            "transactions",

                        "field":
                            field,

                        "data_count":
                            len(data),

                        "summary":
                            result
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Univariate summary error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # UNIVARIATE - DISTRIBUTION
    # ========================================================

    @app.route(
        "/api/univariate/distribution",
        methods=["GET"]
    )
    def univariate_distribution():

        try:

            field = request.args.get(
                "field",
                "Revenue"
            )

            bins = request.args.get(
                "bins",
                20,
                type=int
            )

            if not validate_numeric_field(
                field
            ):

                return jsonify(
                    {
                        "error": "Invalid field"
                    }
                ), 400

            bins = max(
                5,
                min(bins, 100)
            )

            db = get_db()

            data = get_numeric_data(
                db,
                "transactions",
                field
            )

            if not data:

                return jsonify(
                    {
                        "error": "No data found"
                    }
                ), 404

            values = np.array(
                data,
                dtype=float
            )

            q1 = np.percentile(values, 25)
            q3 = np.percentile(values, 75)
            iqr_val = q3 - q1

            skewness = float(
                stats.skew(values)
            )

            use_log_scale = bool(
                abs(skewness) > 5
                and np.min(values) > 0
            )

            if use_log_scale:
                log_values = np.log(
                    np.clip(
                        values,
                        np.finfo(float).eps,
                        None
                    )
                )
                histogram_values = log_values
            else:
                histogram_values = values

            if iqr_val > 0:
                freedman_binwidth = (
                    2.0 * iqr_val
                    / (len(values) ** (1 / 3))
                )
                data_range = (
                    histogram_values.max()
                    - histogram_values.min()
                )
                suggested_bins = max(
                    5,
                    min(
                        100,
                        int(
                            np.ceil(
                                data_range
                                / max(
                                    freedman_binwidth,
                                    np.spacing(
                                        data_range
                                    )
                                )
                            )
                        )
                    )
                )
                min_bins = 10 if use_log_scale else 5
                actual_bins = max(
                    min_bins,
                    min(bins, suggested_bins)
                )
            else:
                actual_bins = bins

            counts, log_edges = np.histogram(
                histogram_values,
                bins=actual_bins
            )

            if use_log_scale:
                edges = np.exp(log_edges)
            else:
                edges = log_edges

            distribution = []

            for i in range(
                len(counts)
            ):

                distribution.append(
                    {
                        "bin_start":
                            float(
                                edges[i]
                            ),

                        "bin_end":
                            float(
                                edges[i + 1]
                            ),

                        "bin_center":
                            float(
                                (
                                    edges[i]
                                    + edges[i + 1]
                                ) / 2
                            ),

                        "count":
                            int(
                                counts[i]
                            ),

                        "log_scale":
                            use_log_scale
                    }
                )

            return jsonify(
                clean_for_json(
                    {
                        "collection":
                            "transactions",

                        "field":
                            field,

                        "data_count":
                            len(data),

                        "bins":
                            bins,

                        "distribution":
                            distribution
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Distribution error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # UNIVARIATE - OUTLIERS
    # ========================================================

    @app.route(
        "/api/univariate/outliers",
        methods=["GET"]
    )
    def univariate_outliers():

        try:

            field = request.args.get(
                "field",
                "Revenue"
            )

            limit = request.args.get(
                "limit",
                100,
                type=int
            )

            if not validate_numeric_field(
                field
            ):

                return jsonify(
                    {
                        "error":
                            "Invalid field"
                    }
                ), 400

            limit = max(
                10,
                min(limit, 1000)
            )

            db = get_db()

            data = get_numeric_data(
                db,
                "transactions",
                field
            )

            if not data:

                return jsonify(
                    {
                        "error":
                            "No data found"
                    }
                ), 404

            values = np.array(
                data,
                dtype=float
            )

            q1 = float(
                np.percentile(
                    values,
                    25
                )
            )

            q3 = float(
                np.percentile(
                    values,
                    75
                )
            )

            iqr = q3 - q1

            lower_bound = (
                q1 - 1.5 * iqr
            )

            upper_bound = (
                q3 + 1.5 * iqr
            )

            lower_values = values[
                values < lower_bound
            ]

            upper_values = values[
                values > upper_bound
            ]

            all_outliers = np.concatenate(
                [
                    lower_values,
                    upper_values
                ]
            )

            sorted_outliers = sorted(
                all_outliers,
                key=lambda value:
                    abs(
                        value -
                        (
                            q1
                            if value < lower_bound
                            else q3
                        )
                    )
            )

            outliers = []

            for value in sorted_outliers[
                :limit
            ]:

                is_lower = (
                    value < lower_bound
                )

                outliers.append(
                    {
                        "value":
                            float(value),

                        "type":
                            (
                                "lower"
                                if is_lower
                                else "upper"
                            ),

                        "threshold":
                            float(
                                lower_bound
                                if is_lower
                                else upper_bound
                            )
                    }
                )

            return jsonify(
                clean_for_json(
                    {
                        "collection":
                            "transactions",

                        "field":
                            field,

                        "data_count":
                            len(data),

                        "q1":
                            q1,

                        "q3":
                            q3,

                        "iqr":
                            iqr,

                        "lower_bound":
                            lower_bound,

                        "upper_bound":
                            upper_bound,

                        "total_outliers":
                            int(
                                len(all_outliers)
                            ),

                        "lower_outliers":
                            int(
                                len(lower_values)
                            ),

                        "upper_outliers":
                            int(
                                len(upper_values)
                            ),

                        "outliers_returned":
                            len(outliers),

                        "outliers":
                            outliers
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Outlier error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # UNIVARIATE - NORMALITY
    # ========================================================

    @app.route(
        "/api/univariate/normality",
        methods=["GET"]
    )
    def univariate_normality():

        try:

            field = request.args.get(
                "field",
                "Revenue"
            )

            if not validate_numeric_field(
                field
            ):

                return jsonify(
                    {
                        "error":
                            "Invalid field"
                    }
                ), 400

            db = get_db()

            data = get_numeric_data(
                db,
                "transactions",
                field
            )

            if len(data) < 3:

                return jsonify(
                    {
                        "error":
                            "At least 3 values are required."
                    }
                ), 400

            sample_size = min(
                len(data),
                5000
            )

            rng = np.random.default_rng(
                42
            )

            if len(data) > sample_size:

                sample = rng.choice(
                    data,
                    size=sample_size,
                    replace=False
                )

            else:

                sample = np.array(
                    data,
                    dtype=float
                )

            shapiro_stat, shapiro_p = (
                stats.shapiro(sample)
            )

            normal_stat, normal_p = (
                stats.normaltest(sample)
            )

            alpha = 0.05

            return jsonify(
                clean_for_json(
                    {
                        "collection":
                            "transactions",

                        "field":
                            field,

                        "data_count":
                            len(data),

                        "sample_size":
                            len(sample),

                        "alpha":
                            alpha,

                        "shapiro":
                            {
                                "statistic":
                                    float(
                                        shapiro_stat
                                    ),

                                "p_value":
                                    float(
                                        shapiro_p
                                    ),

                                "is_normal":
                                    bool(
                                        shapiro_p
                                        > alpha
                                    )
                            },

                        "dagostino":
                            {
                                "statistic":
                                    float(
                                        normal_stat
                                    ),

                                "p_value":
                                    float(
                                        normal_p
                                    ),

                                "is_normal":
                                    bool(
                                        normal_p
                                        > alpha
                                    )
                            }
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Normality error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # UNIVARIATE - Q-Q PLOT
    # ========================================================

    @app.route(
        "/api/univariate/qq-plot",
        methods=["GET"]
    )
    def univariate_qq_plot():

        try:

            field = request.args.get(
                "field",
                "Revenue"
            )

            sample_size = request.args.get(
                "sample_size",
                100,
                type=int
            )

            if not validate_numeric_field(
                field
            ):

                return jsonify(
                    {
                        "error":
                            "Invalid field"
                    }
                ), 400

            sample_size = max(
                20,
                min(sample_size, 500)
            )

            db = get_db()

            data = get_numeric_data(
                db,
                "transactions",
                field
            )

            if len(data) < 3:

                return jsonify(
                    {
                        "error":
                            "At least 3 values are required."
                    }
                ), 400

            rng = np.random.default_rng(
                42
            )

            if len(data) > sample_size:

                sample = rng.choice(
                    data,
                    size=sample_size,
                    replace=False
                )

            else:

                sample = np.array(
                    data,
                    dtype=float
                )

            theoretical, ordered = (
                stats.probplot(
                    sample,
                    dist="norm",
                    fit=False
                )
            )

            qq_data = []

            for (
                theoretical_value,
                actual_value
            ) in zip(
                theoretical,
                ordered
            ):

                qq_data.append(
                    {
                        "theoretical":
                            float(
                                theoretical_value
                            ),

                        "actual":
                            float(
                                actual_value
                            )
                    }
                )

            return jsonify(
                clean_for_json(
                    {
                        "collection":
                            "transactions",

                        "field":
                            field,

                        "data_count":
                            len(data),

                        "sample_size":
                            len(sample),

                        "qq_data":
                            qq_data
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Q-Q plot error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # BIVARIATE - CORRELATION
    # ========================================================

    @app.route(
        "/api/bivariate/correlation",
        methods=["GET"]
    )
    def bivariate_correlation():

        try:

            x_field = request.args.get(
                "x",
                "Quantity"
            )

            y_field = request.args.get(
                "y",
                "Revenue"
            )

            if not validate_numeric_field(
                x_field
            ):

                return jsonify(
                    {
                        "error":
                            f"Invalid x field: {x_field}"
                    }
                ), 400

            if not validate_numeric_field(
                y_field
            ):

                return jsonify(
                    {
                        "error":
                            f"Invalid y field: {y_field}"
                    }
                ), 400

            db = get_db()

            x_values, y_values = (
                get_paired_numeric_data(
                    db,
                    "transactions",
                    x_field,
                    y_field
                )
            )

            if len(x_values) < 3:

                return jsonify(
                    {
                        "error":
                            "At least 3 paired observations are required."
                    }
                ), 400

            x = np.array(
                x_values,
                dtype=float
            )

            y = np.array(
                y_values,
                dtype=float
            )

            pearson_r, pearson_p = (
                stats.pearsonr(x, y)
            )

            spearman_r, spearman_p = (
                stats.spearmanr(x, y)
            )

            covariance = np.cov(
                x,
                y,
                ddof=1
            )[0, 1]

            return jsonify(
                clean_for_json(
                    {
                        "collection":
                            "transactions",

                        "x_field":
                            x_field,

                        "y_field":
                            y_field,

                        "data_count":
                            len(x),

                        "pearson":
                            {
                                "correlation":
                                    float(
                                        pearson_r
                                    ),

                                "p_value":
                                    float(
                                        pearson_p
                                    )
                            },

                        "spearman":
                            {
                                "correlation":
                                    float(
                                        spearman_r
                                    ),

                                "p_value":
                                    float(
                                        spearman_p
                                    )
                            },

                        "covariance":
                            float(
                                covariance
                            )
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Bivariate correlation error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # BIVARIATE - SCATTER
    # ========================================================

    @app.route(
        "/api/bivariate/scatter",
        methods=["GET"]
    )
    def bivariate_scatter():

        try:

            x_field = request.args.get(
                "x",
                "Quantity"
            )

            y_field = request.args.get(
                "y",
                "Revenue"
            )

            limit = request.args.get(
                "limit",
                1000,
                type=int
            )

            if not validate_numeric_field(
                x_field
            ):

                return jsonify(
                    {
                        "error":
                            "Invalid x field"
                    }
                ), 400

            if not validate_numeric_field(
                y_field
            ):

                return jsonify(
                    {
                        "error":
                            "Invalid y field"
                    }
                ), 400

            limit = max(
                100,
                min(limit, 5000)
            )

            db = get_db()

            x_values, y_values = (
                get_paired_numeric_data(
                    db,
                    "transactions",
                    x_field,
                    y_field,
                    limit
                )
            )

            data = []

            for x, y in zip(
                x_values,
                y_values
            ):

                data.append(
                    {
                        "x": x,
                        "y": y
                    }
                )

            return jsonify(
                clean_for_json(
                    {
                        "collection":
                            "transactions",

                        "x_field":
                            x_field,

                        "y_field":
                            y_field,

                        "data_count":
                            len(data),

                        "limit":
                            limit,

                        "data":
                            data
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Bivariate scatter error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # BIVARIATE - REGRESSION
    # ========================================================

    @app.route(
        "/api/bivariate/regression",
        methods=["GET"]
    )
    def bivariate_regression():

        try:

            x_field = request.args.get(
                "x",
                "Quantity"
            )

            y_field = request.args.get(
                "y",
                "Revenue"
            )

            if not validate_numeric_field(
                x_field
            ):

                return jsonify(
                    {
                        "error":
                            "Invalid x field"
                    }
                ), 400

            if not validate_numeric_field(
                y_field
            ):

                return jsonify(
                    {
                        "error":
                            "Invalid y field"
                    }
                ), 400

            db = get_db()

            x_values, y_values = (
                get_paired_numeric_data(
                    db,
                    "transactions",
                    x_field,
                    y_field
                )
            )

            if len(x_values) < 3:

                return jsonify(
                    {
                        "error":
                            "At least 3 paired observations are required."
                    }
                ), 400

            x = np.array(
                x_values,
                dtype=float
            )

            y = np.array(
                y_values,
                dtype=float
            )

            regression = (
                stats.linregress(
                    x,
                    y
                )
            )

            predictions = (
                regression.intercept
                + regression.slope * x
            )

            ss_res = np.sum(
                (y - predictions) ** 2
            )

            ss_tot = np.sum(
                (y - np.mean(y)) ** 2
            )

            r_squared = (
                1 - ss_res / ss_tot
                if ss_tot != 0
                else 0
            )

            return jsonify(
                clean_for_json(
                    {
                        "collection":
                            "transactions",

                        "x_field":
                            x_field,

                        "y_field":
                            y_field,

                        "data_count":
                            len(x),

                        "regression":
                            {
                                "slope":
                                    float(
                                        regression.slope
                                    ),

                                "intercept":
                                    float(
                                        regression.intercept
                                    ),

                                "r_value":
                                    float(
                                        regression.rvalue
                                    ),

                                "r_squared":
                                    float(
                                        r_squared
                                    ),

                                "p_value":
                                    float(
                                        regression.pvalue
                                    ),

                                "std_error":
                                    float(
                                        regression.stderr
                                    ),

                                "equation":
                                    (
                                        f"y = "
                                        f"{regression.slope:.4f}x + "
                                        f"{regression.intercept:.4f}"
                                    )
                            }
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Bivariate regression error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # BIVARIATE - PRODUCT
    # ========================================================

    @app.route(
        "/api/bivariate/product",
        methods=["GET"]
    )
    def bivariate_product():

        try:

            limit = request.args.get(
                "limit",
                20,
                type=int
            )

            limit = max(
                5,
                min(limit, 100)
            )

            db = get_db()

            results = list(
                db[
                    "transactions"
                ].aggregate(
                    [

                        {
                            "$group": {

                                "_id":
                                    "$ProductID",

                                "product_name":
                                    {
                                        "$first":
                                            "$ProductName"
                                    },

                                "quantity":
                                    {
                                        "$sum":
                                            "$Quantity"
                                    },

                                "revenue":
                                    {
                                        "$sum":
                                            "$Revenue"
                                    },

                                "transactions":
                                    {
                                        "$sum": 1
                                    }
                            }
                        },

                        {
                            "$sort": {
                                "revenue": -1
                            }
                        },

                        {
                            "$limit": limit
                        }
                    ]
                )
            )

            data = []

            for row in results:

                data.append(
                    {
                        "product_id":
                            row["_id"],

                        "product_name":
                            row.get(
                                "product_name"
                            )
                            or "Unknown",

                        "quantity":
                            int(
                                row.get(
                                    "quantity",
                                    0
                                )
                            ),

                        "revenue":
                            round(
                                float(
                                    row.get(
                                        "revenue",
                                        0
                                    )
                                ),
                                2
                            ),

                        "transactions":
                            int(
                                row.get(
                                    "transactions",
                                    0
                                )
                            )
                    }
                )

            return jsonify(
                clean_for_json(
                    {
                        "analysis":
                            "Product quantity vs revenue",

                        "count":
                            len(data),

                        "data":
                            data
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Product analysis error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # BIVARIATE - COUNTRY
    # ========================================================

    @app.route(
        "/api/bivariate/country",
        methods=["GET"]
    )
    def bivariate_country():

        try:

            limit = request.args.get(
                "limit",
                20,
                type=int
            )

            limit = max(
                5,
                min(limit, 100)
            )

            db = get_db()

            results = list(
                db[
                    "transactions"
                ].aggregate(
                    [

                        {
                            "$group": {

                                "_id":
                                    "$Country",

                                "quantity":
                                    {
                                        "$sum":
                                            "$Quantity"
                                    },

                                "revenue":
                                    {
                                        "$sum":
                                            "$Revenue"
                                    },

                                "transactions":
                                    {
                                        "$sum": 1
                                    }
                            }
                        },

                        {
                            "$sort": {
                                "revenue": -1
                            }
                        },

                        {
                            "$limit": limit
                        }
                    ]
                )
            )

            data = []

            for row in results:

                data.append(
                    {
                        "country":
                            row["_id"],

                        "quantity":
                            int(
                                row.get(
                                    "quantity",
                                    0
                                )
                            ),

                        "revenue":
                            round(
                                float(
                                    row.get(
                                        "revenue",
                                        0
                                    )
                                ),
                                2
                            ),

                        "transactions":
                            int(
                                row.get(
                                    "transactions",
                                    0
                                )
                            )
                    }
                )

            return jsonify(
                clean_for_json(
                    {
                        "analysis":
                            "Country quantity vs revenue",

                        "count":
                            len(data),

                        "data":
                            data
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Country analysis error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # BIVARIATE - PRICE VS QUANTITY
    # ========================================================

    @app.route(
        "/api/bivariate/price-quantity",
        methods=["GET"]
    )
    def bivariate_price_quantity():

        try:

            db = get_db()

            x_values, y_values = (
                get_paired_numeric_data(
                    db,
                    "transactions",
                    "UnitPrice",
                    "Quantity"
                )
            )

            if len(x_values) < 3:

                return jsonify(
                    {
                        "error":
                            "Insufficient data"
                    }
                ), 400

            x = np.array(
                x_values,
                dtype=float
            )

            y = np.array(
                y_values,
                dtype=float
            )

            correlation, p_value = (
                stats.pearsonr(
                    x,
                    y
                )
            )

            return jsonify(
                clean_for_json(
                    {
                        "x_field":
                            "UnitPrice",

                        "y_field":
                            "Quantity",

                        "data_count":
                            len(x),

                        "correlation":
                            float(
                                correlation
                            ),

                        "p_value":
                            float(
                                p_value
                            ),

                        "relationship":
                            (
                                "positive"
                                if correlation > 0
                                else (
                                    "negative"
                                    if correlation < 0
                                    else "none"
                                )
                            )
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Price quantity error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # MULTIVARIATE - SUMMARY
    # ========================================================

    @app.route(
        "/api/multivariate/summary",
        methods=["GET"]
    )
    def multivariate_summary():

        try:

            db = get_db()

            rows = get_daily_predictive_data(
                db
            )

            if not rows:

                return jsonify(
                    {
                        "error":
                            "No multivariate data found."
                    }
                ), 404

            df = pd.DataFrame(rows)

            summary = {}

            for column in [
                "Quantity",
                "Revenue",
                "Transactions"
            ]:

                values = df[column]

                summary[column] = {

                    "count":
                        int(
                            values.count()
                        ),

                    "mean":
                        float(
                            values.mean()
                        ),

                    "median":
                        float(
                            values.median()
                        ),

                    "std":
                        float(
                            values.std()
                        ),

                    "min":
                        float(
                            values.min()
                        ),

                    "max":
                        float(
                            values.max()
                        )
                }

            return jsonify(
                clean_for_json(
                    {
                        "collection":
                            "daily_sales",

                        "data_count":
                            len(df),

                        "variables":
                            [
                                "Quantity",
                                "Revenue",
                                "Transactions"
                            ],

                        "summary":
                            summary
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Multivariate summary error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # MULTIVARIATE - CORRELATION
    # ========================================================

    @app.route(
        "/api/multivariate/correlation",
        methods=["GET"]
    )
    def multivariate_correlation():

        try:

            db = get_db()

            rows = get_daily_predictive_data(
                db
            )

            if not rows:

                return jsonify(
                    {
                        "error":
                            "No multivariate data found."
                    }
                ), 404

            df = pd.DataFrame(rows)

            start_date = request.args.get(
                "start_date", None
            )

            end_date = request.args.get(
                "end_date", None
            )

            if start_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    df = df[df["Date"] >= start_dt]
                except Exception:
                    pass

            if end_date:
                try:
                    end_dt = pd.to_datetime(end_date)
                    df = df[df["Date"] <= end_dt]
                except Exception:
                    pass

            if df.empty:
                return jsonify(
                    {
                        "error":
                            "No data found for the selected date range."
                    }
                ), 404

            variables_param = request.args.get(
                "variables",
                None
            )

            if variables_param:

                selected = [
                    v.strip()
                    for v in
                    variables_param.split(",")
                    if v.strip()
                    in df.columns
                    and v.strip() != "Date"
                ]

                if len(selected) >= 2:

                    df = df[selected]

            numeric_cols = [
                c for c in df.columns
                if c != "Date"
            ]

            if len(numeric_cols) < 2:
                return jsonify(
                    {
                        "error":
                            "At least two numeric variables are required."
                    }
                ), 400

            correlation = (
                MultivariatePredictor
                .correlation(df[numeric_cols])
            )

            return jsonify(
                clean_for_json(
                    {
                        "collection":
                            "daily_sales",

                        "data_count":
                            len(df),

                        "variables":
                            list(
                                correlation.columns
                            ),

                        "correlation_matrix":
                            (
                                correlation
                                .round(6)
                                .to_dict()
                            )
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Multivariate correlation error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # MULTIVARIATE - PCA
    # ========================================================

    @app.route(
        "/api/multivariate/pca",
        methods=["GET"]
    )
    def multivariate_pca():

        try:

            components = request.args.get(
                "components",
                request.args.get(
                    "n_components",
                    2,
                    type=int
                ),
                type=int
            )

            components = max(
                2,
                min(components, 3)
            )

            db = get_db()

            rows = get_daily_predictive_data(
                db
            )

            if not rows:

                return jsonify(
                    {
                        "error":
                            "No multivariate data found."
                    }
                ), 404

            df = pd.DataFrame(rows)

            start_date = request.args.get(
                "start_date", None
            )

            end_date = request.args.get(
                "end_date", None
            )

            if start_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    df = df[df["Date"] >= start_dt]
                except Exception:
                    pass

            if end_date:
                try:
                    end_dt = pd.to_datetime(end_date)
                    df = df[df["Date"] <= end_dt]
                except Exception:
                    pass

            if df.empty:
                return jsonify(
                    {
                        "error":
                            "No data found for the selected date range."
                    }
                ), 404

            variables_param = request.args.get(
                "variables",
                None
            )

            if variables_param:

                selected = [
                    v.strip()
                    for v in
                    variables_param.split(",")
                    if v.strip()
                    in df.columns
                    and v.strip() != "Date"
                ]

                if len(selected) >= 2:

                    df = df[selected]

            numeric_cols = [
                c for c in df.columns
                if c != "Date"
            ]

            if len(numeric_cols) < 2:
                return jsonify(
                    {
                        "error":
                            "At least two numeric variables are required for PCA."
                    }
                ), 400

            result = (
                MultivariatePredictor
                .pca(
                    df[numeric_cols],
                    n_components=components
                )
            )

            return jsonify(
                clean_for_json(
                    {
                        "collection":
                            "daily_sales",

                        "data_count":
                            len(df),

                        **result
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"PCA error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # MULTIVARIATE - REGRESSION
    # ========================================================

    @app.route(
        "/api/multivariate/regression",
        methods=["GET"]
    )
    def multivariate_regression():

        try:

            db = get_db()

            rows = get_daily_predictive_data(
                db
            )

            if not rows:

                return jsonify(
                    {
                        "error":
                            "No multivariate data found."
                    }
                ), 404

            df = pd.DataFrame(rows)

            start_date = request.args.get(
                "start_date", None
            )

            end_date = request.args.get(
                "end_date", None
            )

            if start_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    df = df[df["Date"] >= start_dt]
                except Exception:
                    pass

            if end_date:
                try:
                    end_dt = pd.to_datetime(end_date)
                    df = df[df["Date"] <= end_dt]
                except Exception:
                    pass

            if df.empty:
                return jsonify(
                    {
                        "error":
                            "No data found for the selected date range."
                    }
                ), 404

            target = request.args.get(
                "target", "Revenue"
            )

            features_param = request.args.get(
                "features", None
            )

            if features_param:
                features = [
                    v.strip()
                    for v in features_param.split(",")
                    if v.strip()
                    in df.columns
                    and v.strip() != "Date"
                    and v.strip() != target
                ]
            else:
                features = [
                    c for c in df.columns
                    if c != "Date"
                    and c != target
                ]

            if not features or target not in df.columns:
                return jsonify(
                    {
                        "error":
                            "Insufficient variables for regression."
                    }
                ), 400

            from predictive import MultivariatePredictor

            numeric_df = df[features + [target]].copy()
            numeric_df = numeric_df.replace(
                [np.inf, -np.inf], np.nan
            ).dropna()

            if len(numeric_df) < 10:
                return jsonify(
                    {
                        "error":
                            "Not enough data for regression (need at least 10 observations)."
                    }
                ), 400

            X = numeric_df[features]
            y = numeric_df[target]

            split_index = int(len(numeric_df) * 0.8)
            X_train = X.iloc[:split_index]
            X_test = X.iloc[split_index:]
            y_train = y.iloc[:split_index]
            y_test = y.iloc[split_index:]

            from sklearn.linear_model import LinearRegression
            from sklearn.metrics import mean_absolute_error, mean_squared_error

            model = LinearRegression()
            model.fit(X_train, y_train)
            predictions = model.predict(X_test)

            mae = mean_absolute_error(y_test, predictions)
            rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))

            coefficients = {}
            for i, feat in enumerate(features):
                coefficients[feat] = float(model.coef_[i])

            actual_vs_predicted = []
            for actual, predicted in zip(
                y_test.tail(50),
                predictions[-50:]
            ):
                actual_vs_predicted.append(
                    {
                        "actual": float(actual),
                        "predicted": float(predicted)
                    }
                )

            return jsonify(
                clean_for_json(
                    {
                        "collection":
                            "daily_sales",

                        "data_count":
                            len(numeric_df),

                        "model":
                            "Multiple Linear Regression",

                        "features": features,

                        "target": target,

                        "coefficients": coefficients,

                        "intercept": float(model.intercept_),

                        "r_squared": float(
                            model.score(X_test, y_test)
                        ),

                        "mae": float(mae),

                        "rmse": rmse,

                        "actual_vs_predicted":
                            actual_vs_predicted
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Multivariate regression error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # MULTIVARIATE - SCATTER
    # ========================================================

    @app.route(
        "/api/multivariate/scatter",
        methods=["GET"]
    )
    def multivariate_scatter():

        try:

            x_field = request.args.get(
                "x", "Revenue"
            )

            y_field = request.args.get(
                "y", "Quantity"
            )

            start_date = request.args.get(
                "start_date", None
            )

            end_date = request.args.get(
                "end_date", None
            )

            limit = request.args.get(
                "limit",
                2000,
                type=int
            )

            limit = max(
                100,
                min(limit, 5000)
            )

            db = get_db()

            rows = get_daily_predictive_data(
                db
            )

            if not rows:
                return jsonify(
                    {
                        "error":
                            "No data found."
                    }
                ), 404

            df = pd.DataFrame(rows)

            if start_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    df = df[df["Date"] >= start_dt]
                except Exception:
                    pass

            if end_date:
                try:
                    end_dt = pd.to_datetime(end_date)
                    df = df[df["Date"] <= end_dt]
                except Exception:
                    pass

            if x_field not in df.columns or y_field not in df.columns:
                return jsonify(
                    {
                        "error":
                            f"Fields {x_field} or {y_field} not found in data."
                    }
                ), 400

            df = df[[x_field, y_field]].dropna()

            df = df[
                np.isfinite(df[x_field])
                & np.isfinite(df[y_field])
            ]

            if len(df) == 0:
                return jsonify(
                    clean_for_json(
                        {
                            "x_field": x_field,
                            "y_field": y_field,
                            "data_count": 0,
                            "data": []
                        }
                    )
                ), 200

            if len(df) > limit:
                df = df.sample(
                    n=limit,
                    random_state=42
                )

            data = []
            for _, row in df.iterrows():
                data.append(
                    {
                        "x": float(row[x_field]),
                        "y": float(row[y_field])
                    }
                )

            return jsonify(
                clean_for_json(
                    {
                        "x_field": x_field,
                        "y_field": y_field,
                        "data_count": len(data),
                        "data": data
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Multivariate scatter error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # ARIMA
    # ========================================================

    @app.route(
        "/api/forecast/arima",
        methods=["GET"]
    )
    def forecast_arima():

        try:

            metric = request.args.get(
                "metric",
                "Revenue"
            )

            forecast_days = request.args.get(
                "forecast_days",
                30,
                type=int
            )

            p = request.args.get(
                "p",
                1,
                type=int
            )

            d = request.args.get(
                "d",
                1,
                type=int
            )

            q = request.args.get(
                "q",
                1,
                type=int
            )

            start_date = request.args.get(
                "start_date",
                None
            )

            end_date = request.args.get(
                "end_date",
                None
            )

            forecast_days = max(
                1,
                min(forecast_days, 180)
            )

            db = get_db()

            series = get_forecasting_series(
                db,
                metric,
                start_date,
                end_date
            )

            result = (
                TimeSeriesPredictor
                .arima(
                    series,
                    forecast_days,
                    order=(
                        p,
                        d,
                        q
                    )
                )
            )

            response = (
                create_forecast_response(
                    series,
                    result,
                    metric
                )
            )

            return jsonify(
                response
            ), 200

        except Exception as e:

            logger.exception(
                f"ARIMA error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # SARIMA
    # ========================================================

    @app.route(
        "/api/forecast/sarima",
        methods=["GET"]
    )
    def forecast_sarima():

        try:

            metric = request.args.get(
                "metric",
                "Revenue"
            )

            forecast_days = request.args.get(
                "forecast_days",
                30,
                type=int
            )

            start_date = request.args.get(
                "start_date",
                None
            )

            end_date = request.args.get(
                "end_date",
                None
            )

            forecast_days = max(
                1,
                min(forecast_days, 180)
            )

            db = get_db()

            series = get_forecasting_series(
                db,
                metric,
                start_date,
                end_date
            )

            result = (
                TimeSeriesPredictor
                .sarima(
                    series,
                    forecast_days,
                    order=(
                        1,
                        1,
                        1
                    ),
                    seasonal_order=(
                        1,
                        1,
                        1,
                        7
                    )
                )
            )

            response = (
                create_forecast_response(
                    series,
                    result,
                    metric
                )
            )

            return jsonify(
                response
            ), 200

        except Exception as e:

            logger.exception(
                f"SARIMA error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # HOLT-WINTERS
    # ========================================================

    @app.route(
        "/api/forecast/holt-winters",
        methods=["GET"]
    )
    def forecast_holt_winters():

        try:

            metric = request.args.get(
                "metric",
                "Revenue"
            )

            forecast_days = request.args.get(
                "forecast_days",
                30,
                type=int
            )

            seasonal_periods = request.args.get(
                "seasonal_periods",
                7,
                type=int
            )

            start_date = request.args.get(
                "start_date",
                None
            )

            end_date = request.args.get(
                "end_date",
                None
            )

            forecast_days = max(
                1,
                min(forecast_days, 180)
            )

            seasonal_periods = max(
                2,
                min(seasonal_periods, 30)
            )

            db = get_db()

            series = get_forecasting_series(
                db,
                metric,
                start_date,
                end_date
            )

            result = (
                TimeSeriesPredictor
                .holt_winters(
                    series,
                    forecast_days,
                    seasonal_periods
                )
            )

            response = (
                create_forecast_response(
                    series,
                    result,
                    metric
                )
            )

            return jsonify(
                response
            ), 200

        except Exception as e:

            logger.exception(
                f"Holt-Winters error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # FORECAST MODEL COMPARISON
    # ========================================================

    @app.route(
        "/api/forecast/compare",
        methods=["GET"]
    )
    def forecast_compare():

        try:

            metric = request.args.get(
                "metric",
                "Revenue"
            )

            forecast_days = request.args.get(
                "forecast_days",
                30,
                type=int
            )

            start_date = request.args.get(
                "start_date",
                None
            )

            end_date = request.args.get(
                "end_date",
                None
            )

            forecast_days = max(
                1,
                min(forecast_days, 180)
            )

            db = get_db()

            series = get_forecasting_series(
                db,
                metric,
                start_date,
                end_date
            )

            models = {}

            # ------------------------------------------------
            # ARIMA
            # ------------------------------------------------

            try:

                result = (
                    TimeSeriesPredictor
                    .arima(
                        series,
                        forecast_days,
                        order=(
                            1,
                            1,
                            1
                        )
                    )
                )

                models["ARIMA"] = {
                    "predictions":
                        result[
                            "predictions"
                        ],

                    "aic":
                        result["aic"],

                    "bic":
                        result["bic"]
                }

            except Exception as e:

                models["ARIMA"] = {
                    "error": str(e)
                }

            # ------------------------------------------------
            # SARIMA
            # ------------------------------------------------

            try:

                result = (
                    TimeSeriesPredictor
                    .sarima(
                        series,
                        forecast_days,
                        order=(
                            1,
                            1,
                            1
                        ),
                        seasonal_order=(
                            1,
                            1,
                            1,
                            7
                        )
                    )
                )

                models["SARIMA"] = {
                    "predictions":
                        result[
                            "predictions"
                        ],

                    "aic":
                        result["aic"],

                    "bic":
                        result["bic"]
                }

            except Exception as e:

                models["SARIMA"] = {
                    "error": str(e)
                }

            # ------------------------------------------------
            # HOLT-WINTERS
            # ------------------------------------------------

            try:

                result = (
                    TimeSeriesPredictor
                    .holt_winters(
                        series,
                        forecast_days,
                        seasonal_periods=7
                    )
                )

                models["Holt-Winters"] = {
                    "predictions":
                        result[
                            "predictions"
                        ],

                    "aic":
                        result["aic"],

                    "bic":
                        result["bic"]
                }

            except Exception as e:

                models["Holt-Winters"] = {
                    "error": str(e)
                }

            return jsonify(
                clean_for_json(
                    {
                        "metric":
                            metric,

                        "forecast_days":
                            forecast_days,

                        "last_date":
                            series.index[-1]
                            .strftime(
                                "%Y-%m-%d"
                            ),

                        "models":
                            models
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"Forecast comparison error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # INVENTORY - ABC ANALYSIS
    # ========================================================

    @app.route(
        "/api/analysis/abc",
        methods=["GET"]
    )
    def analysis_abc():

        try:

            db = get_db()

            start_date = request.args.get(
                "start_date", None
            )

            end_date = request.args.get(
                "end_date", None
            )

            if start_date and end_date:
                try:
                    if (
                        pd.to_datetime(start_date)
                        > pd.to_datetime(end_date)
                    ):
                        return jsonify(
                            {
                                "error":
                                    "Start date must not be after end date."
                            }
                        ), 400
                except Exception:
                    pass

            threshold_a = request.args.get(
                "threshold_a", 0.80, type=float
            )

            threshold_b = request.args.get(
                "threshold_b", 0.95, type=float
            )

            df = load_transactions(
                db, start_date, end_date
            )

            if df.empty:

                return jsonify(
                    clean_for_json(
                        {
                            "summary": (
                                _empty_abc_summary()
                            ),
                            "items": [],
                            "distribution": [],
                            "contribution": [],
                            "pareto": [],
                            "collection": "transactions",
                        }
                    )
                ), 200

            items, summary = calculate_abc(
                df,
                threshold_a=threshold_a,
                threshold_b=threshold_b,
            )

            distribution = []
            contribution = []

            for cls in ["A", "B", "C"]:

                distribution.append(
                    {
                        "class": cls,
                        "items": summary[
                            "counts"
                        ][cls],
                        "value": summary[
                            "value_by_class"
                        ][cls],
                        "value_pct": summary.get(
                            f"value_pct_{cls.lower()}",
                            0.0,
                        ),
                    }
                )

            # Contribution bar data (for a stacked/plain chart)
            for item in items:
                contribution.append(
                    {
                        "rank": item["rank"],
                        "name": item[
                            "product_name"
                        ],
                        "class": item["class"],
                        "value": item[
                            "consumption_value"
                        ],
                        "contribution_pct": item[
                            "contribution_pct"
                        ],
                        "cumulative_pct": item[
                            "cumulative_pct"
                        ],
                    }
                )

            # Aggregate large datasets for the Pareto chart
            pareto = _pareto_aggregate(
                items, top_n=100
            )

            return jsonify(
                clean_for_json(
                    {
                        "summary": summary,
                        "items": items,
                        "distribution": distribution,
                        "contribution": contribution,
                        "pareto": pareto,
                        "collection": "transactions",
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"ABC analysis error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # INVENTORY - XYZ ANALYSIS
    # ========================================================

    @app.route(
        "/api/analysis/xyz",
        methods=["GET"]
    )
    def analysis_xyz():

        try:

            db = get_db()

            start_date = request.args.get(
                "start_date", None
            )

            end_date = request.args.get(
                "end_date", None
            )

            if start_date and end_date:
                try:
                    if (
                        pd.to_datetime(start_date)
                        > pd.to_datetime(end_date)
                    ):
                        return jsonify(
                            {
                                "error":
                                    "Start date must not be after end date."
                            }
                        ), 400
                except Exception:
                    pass

            period = request.args.get(
                "period", "M"
            )

            cv_x = request.args.get(
                "cv_x", None, type=float
            )

            cv_y = request.args.get(
                "cv_y", None, type=float
            )

            min_periods = request.args.get(
                "min_periods", None, type=int
            )

            df = load_product_daily(
                db, start_date, end_date
            )

            # Fallback: derive per-product daily demand
            # from the transactions collection.
            if df.empty:

                trans_df = load_transactions(
                    db, start_date, end_date
                )

                if not trans_df.empty:

                    trans_df["Date"] = (
                        pd.to_datetime(
                            trans_df["Date"],
                            errors="coerce",
                        )
                    )

                    trans_df = trans_df[
                        trans_df["Date"].notna()
                    ]

                    if "Quantity" in trans_df.columns:
                        trans_df["Quantity"] = (
                            pd.to_numeric(
                                trans_df["Quantity"],
                                errors="coerce",
                            )
                            .fillna(0.0)
                        )
                    else:
                        trans_df["Quantity"] = 0.0

                    df = trans_df[
                        [
                            "ProductID",
                            "Date",
                            "Quantity",
                        ]
                    ].copy()

            if df.empty:

                return jsonify(
                    clean_for_json(
                        {
                            "summary": (
                                _empty_xyz_summary()
                            ),
                            "items": [],
                            "distribution": [],
                            "variability": [],
                            "collection":
                                "product_daily_sales",
                        }
                    )
                ), 200

            items, summary = calculate_xyz(
                df,
                period=period,
                cv_x=(
                    cv_x if cv_x is not None
                    else 0.50
                ),
                cv_y=(
                    cv_y if cv_y is not None
                    else 1.00
                ),
                min_periods=(
                    min_periods
                    if min_periods is not None
                    else 2
                ),
            )

            distribution = []

            for xyz_class in [
                "X", "Y", "Z", "ND", "U"
            ]:

                distribution.append(
                    {
                        "class": xyz_class,
                        "label": _xyz_label(xyz_class),
                        "items": summary[
                            "counts"
                        ].get(xyz_class, 0),
                    }
                )

            # Variability data for charts (classified items)
            variability = [
                {
                    "product_id": item[
                        "product_id"
                    ],
                    "mean": item[
                        "mean_demand"
                    ],
                    "cv": item["cv"],
                    "cv_pct": item[
                        "cv_pct"
                    ],
                    "class": item["class"],
                }
                for item in items
                if item["class"] in (
                    "X", "Y", "Z"
                )
            ]

            return jsonify(
                clean_for_json(
                    {
                        "summary": summary,
                        "items": items,
                        "distribution": distribution,
                        "variability": variability,
                        "collection":
                            "product_daily_sales",
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"XYZ analysis error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # INVENTORY - ABC / XYZ PRODUCT DETAIL
    # ========================================================

    @app.route(
        "/api/analysis/xyz/trend",
        methods=["GET"]
    )
    def analysis_xyz_trend():

        try:

            db = get_db()

            product_id = request.args.get(
                "product_id", None
            )

            if not product_id:

                return jsonify(
                    {
                        "error":
                            "product_id is required."
                    }
                ), 400

            period = request.args.get(
                "period", "M"
            )

            start_date = request.args.get(
                "start_date", None
            )

            end_date = request.args.get(
                "end_date", None
            )

            df = load_product_daily(
                db, start_date, end_date
            )

            if df.empty:

                trans_df = load_transactions(
                    db, start_date, end_date
                )

                if not trans_df.empty:
                    trans_df["Date"] = (
                        pd.to_datetime(
                            trans_df["Date"],
                            errors="coerce",
                        )
                    )
                    trans_df = trans_df[
                        trans_df["Date"].notna()
                    ]
                    if "Quantity" in trans_df.columns:
                        trans_df["Quantity"] = (
                            pd.to_numeric(
                                trans_df["Quantity"],
                                errors="coerce",
                            )
                            .fillna(0.0)
                        )
                    else:
                        trans_df["Quantity"] = 0.0

                    df = trans_df[
                        [
                            "ProductID",
                            "Date",
                            "Quantity",
                        ]
                    ].copy()

            trend = get_product_demand_trend(
                df, product_id, period=period
            )

            if not trend:

                return jsonify(
                    {
                        "error":
                            "No demand data for this product."
                    }
                ), 404

            return jsonify(
                clean_for_json(
                    {
                        "product_id": product_id,
                        "period": period,
                        "trend": trend,
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"XYZ trend error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # INVENTORY - ABC-XYZ MATRIX
    # ========================================================

    @app.route(
        "/api/analysis/abc-xyz",
        methods=["GET"]
    )
    def analysis_abc_xyz():

        try:

            db = get_db()

            start_date = request.args.get(
                "start_date", None
            )

            end_date = request.args.get(
                "end_date", None
            )

            threshold_a = request.args.get(
                "threshold_a", 0.80, type=float
            )

            threshold_b = request.args.get(
                "threshold_b", 0.95, type=float
            )

            cv_x = request.args.get(
                "cv_x", None, type=float
            )

            cv_y = request.args.get(
                "cv_y", None, type=float
            )

            period = request.args.get(
                "period", "M"
            )

            if start_date and end_date:
                try:
                    if (
                        pd.to_datetime(start_date)
                        > pd.to_datetime(end_date)
                    ):
                        return jsonify(
                            {
                                "error":
                                    "Start date must not be after end date."
                            }
                        ), 400
                except Exception:
                    pass

            # ABC from transactions
            trans_df = load_transactions(
                db, start_date, end_date
            )

            abc_items, abc_summary = (
                calculate_abc(trans_df) if not trans_df.empty
                else ([], _empty_abc_summary())
            )

            # XYZ from product daily sales
            xyz_df = load_product_daily(
                db, start_date, end_date
            )

            if xyz_df.empty and not trans_df.empty:

                trans_df["Date"] = pd.to_datetime(
                    trans_df["Date"], errors="coerce"
                )
                trans_df = trans_df[
                    trans_df["Date"].notna()
                ]
                trans_df["Quantity"] = pd.to_numeric(
                    trans_df["Quantity"],
                    errors="coerce",
                ).fillna(0.0)

                xyz_df = trans_df[
                    ["ProductID", "Date", "Quantity"]
                ].copy()

            xyz_items, xyz_summary = (
                calculate_xyz(
                    xyz_df,
                    period=period,
                    cv_x=(
                        cv_x if cv_x is not None
                        else 0.50
                    ),
                    cv_y=(
                        cv_y if cv_y is not None
                        else 1.00
                    ),
                    min_periods=2,
                ) if not xyz_df.empty
                else ([], _empty_xyz_summary())
            )

            matrix = calculate_abc_xyz_matrix(
                abc_items, xyz_items
            )

            return jsonify(
                clean_for_json(
                    {
                        "abc_summary": abc_summary,
                        "xyz_summary": xyz_summary,
                        "matrix_counts":
                            matrix["matrix_counts"],
                        "matrix_percentages":
                            matrix["matrix_percentages"],
                        "insights":
                            matrix["insights"],
                        "total": matrix["total"],
                    }
                )
            ), 200

        except Exception as e:

            logger.exception(
                f"ABC-XYZ matrix error: {e}"
            )

            return jsonify(
                {
                    "error": str(e)
                }
            ), 500

    # ========================================================
    # INVENTORY - HELPERS
    # ========================================================

    # ========================================================
    # ERROR HANDLERS
    # ========================================================

    @app.errorhandler(404)
    def not_found(error):

        return jsonify(
            {
                "error":
                    "Endpoint not found"
            }
        ), 404

    @app.errorhandler(500)
    def internal_error(error):

        return jsonify(
            {
                "error":
                    "Internal server error"
            }
        ), 500

    # ========================================================
    # RETURN APP
    # ========================================================

    return app


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app = create_app(
        os.getenv(
            "FLASK_ENV",
            "development"
        )
    )

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
    
    # ============================================================
# INITIALIZATION (यह लाइनें जोड़ें)
# ============================================================

app = Flask(__name__)

# यह आपके Vercel फ्रंटएंड को बिना किसी CORS या 403 एरर के डेटा ट्रांसफर करने देगा
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
