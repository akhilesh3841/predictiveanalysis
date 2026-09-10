"""
Inventory Analytics Module

Provides:
- ABC classification (contribution to consumption value)
- XYZ classification (demand variability / predictability)
- ABC-XYZ combined matrix

All calculations are performed from the actual dataset.
No hardcoded sample data.
"""

import logging
import math

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ============================================================
# DATA LOADING
# ============================================================

def load_transactions(db, start_date=None, end_date=None):
    """
    Load transaction-level records into a DataFrame.

    Fields expected (existing project schema):
        ProductID, ProductName, Quantity, UnitPrice, Revenue, Date

    Performs safe numeric conversion and date filtering.
    Handles NaN / infinite / invalid records.
    """

    projection = {
        "_id": 0,
        "ProductID": 1,
        "ProductName": 1,
        "Quantity": 1,
        "UnitPrice": 1,
        "Revenue": 1,
        "Date": 1,
    }

    rows = []

    for document in db["transactions"].find(
        {}, projection
    ):

        try:

            product_id = document.get("ProductID")

            if product_id is None:
                continue

            quantity = document.get("Quantity")
            unit_price = document.get("UnitPrice")
            revenue = document.get("Revenue")

            try:
                quantity = float(quantity)
            except (TypeError, ValueError):
                quantity = None

            try:
                unit_price = float(unit_price)
            except (TypeError, ValueError):
                unit_price = None

            try:
                revenue = float(revenue)
            except (TypeError, ValueError):
                revenue = None

            rows.append(
                {
                    "ProductID": str(product_id),
                    "ProductName": document.get(
                        "ProductName"
                    ),
                    "Quantity": quantity,
                    "UnitPrice": unit_price,
                    "Revenue": revenue,
                    "Date": document.get("Date"),
                }
            )

        except (TypeError, ValueError, KeyError):
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Convert date
    df["Date"] = pd.to_datetime(
        df["Date"], errors="coerce"
    )

    # Numeric conversions
    for col in ["Quantity", "UnitPrice", "Revenue"]:
        df[col] = pd.to_numeric(
            df[col], errors="coerce"
        )

    # Drop rows without a usable date
    df = df.dropna(subset=["Date"])

    # Date range filter
    df = _apply_date_range(df, start_date, end_date)

    if df.empty:
        return df

    # Replace infinite numeric values with NaN
    df = df.replace(
        [np.inf, -np.inf], np.nan
    )

    return df


def load_product_daily(db, start_date=None, end_date=None):
    """
    Load per-product daily sales into a DataFrame.

    Fields expected:
        ProductID, Date, Quantity, Revenue, Transactions

    This is the preferred source for XYZ demand variability
    because it already carries one row per product per day.
    """

    projection = {
        "_id": 0,
        "ProductID": 1,
        "Date": 1,
        "Quantity": 1,
        "Revenue": 1,
    }

    rows = []

    for document in db["product_daily_sales"].find(
        {}, projection
    ):

        try:

            product_id = document.get("ProductID")

            if product_id is None:
                continue

            try:
                quantity = float(
                    document.get("Quantity", 0)
                )
            except (TypeError, ValueError):
                quantity = 0.0

            try:
                revenue = float(
                    document.get("Revenue", 0)
                )
            except (TypeError, ValueError):
                revenue = 0.0

            rows.append(
                {
                    "ProductID": str(product_id),
                    "Date": document.get("Date"),
                    "Quantity": quantity,
                    "Revenue": revenue,
                }
            )

        except (TypeError, ValueError, KeyError):
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    df["Date"] = pd.to_datetime(
        df["Date"], errors="coerce"
    )

    for col in ["Quantity", "Revenue"]:
        df[col] = pd.to_numeric(
            df[col], errors="coerce"
        )

    df = df.dropna(subset=["Date"])

    df = _apply_date_range(df, start_date, end_date)

    if df.empty:
        return df

    df = df.replace(
        [np.inf, -np.inf], np.nan
    ).fillna(0.0)

    return df


def _apply_date_range(df, start_date, end_date):
    """
    Filter a DataFrame by optional start/end date.
    """

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

    return df


# ============================================================
# ABC CLASSIFICATION
# ============================================================

DEFAULT_ABC_THRESHOLDS = {"a": 0.80, "b": 0.95}


def calculate_abc(
    df,
    threshold_a=0.80,
    threshold_b=0.95,
):
    """
    Compute ABC classification for each product.

    Methodology:
      1. Aggregate each product's consumption value.
         - Preferred: sum of Revenue (already Quantity x UnitPrice)
         - Fallback: sum(Quantity * UnitPrice)
      2. Compute total consumption value.
      3. Compute each item's contribution percentage.
      4. Sort descending by consumption value.
      5. Compute cumulative contribution.
      6. Classify via cumulative contribution thresholds:
           A: cumulative <= a
           B: a < cumulative <= b
           C: cumulative > b

    Returns (items, summary).
    """

    if df is None or df.empty:
        return [], _empty_abc_summary()

    # Determine consumption value per transaction row
    if "Revenue" in df.columns:
        use_revenue = (
            df["Revenue"].notna().any()
        )
    else:
        use_revenue = False

    work = df.copy()

    if use_revenue:
        work["Value"] = work["Revenue"].fillna(0.0)
        value_metric = "Revenue"
    else:
        qty = work["Quantity"].fillna(0.0)
        price = work["UnitPrice"].fillna(0.0)
        work["Value"] = qty * price
        value_metric = "Quantity x UnitPrice"

    # First available non-null product name
    product_names = (
        work.dropna(subset=["ProductName"])
        .groupby("ProductID")["ProductName"]
        .first()
        .to_dict()
    )

    agg = (
        work.groupby("ProductID", as_index=False)
        .agg(
            quantity=("Quantity", "sum"),
            unit_price=(
                "UnitPrice",
                "mean",
            ),
            value=("Value", "sum"),
        )
    )

    agg["ProductID"] = agg["ProductID"].astype(str)

    # Clean / normalise
    agg["quantity"] = pd.to_numeric(
        agg["quantity"], errors="coerce"
    ).fillna(0.0)

    agg["unit_price"] = pd.to_numeric(
        agg["unit_price"], errors="coerce"
    ).fillna(0.0)

    agg["value"] = pd.to_numeric(
        agg["value"], errors="coerce"
    ).fillna(0.0)

    total_value = float(agg["value"].sum())

    if total_value <= 0:
        return [], _empty_abc_summary()

    threshold_a = _clean_threshold(threshold_a)
    threshold_b = _clean_threshold(threshold_b)

    # Sort descending by consumption value
    agg = agg.sort_values(
        "value", ascending=False
    ).reset_index(drop=True)

    agg["contribution_pct"] = (
        agg["value"] / total_value * 100.0
    )

    agg["cumulative_pct"] = (
        agg["contribution_pct"].cumsum()
    )

    items = []

    for index, row in agg.iterrows():

        cumulative = float(row["cumulative_pct"])

        if cumulative <= threshold_a * 100.0:
            abc_class = "A"
        elif cumulative <= threshold_b * 100.0:
            abc_class = "B"
        else:
            abc_class = "C"

        items.append(
            {
                "rank": int(index) + 1,
                "product_id": str(
                    row["ProductID"]
                ),
                "product_name": product_names.get(
                    str(row["ProductID"])
                ) or str(row["ProductID"]),
                "quantity": clean_float(
                    row["quantity"]
                ),
                "unit_price": clean_float(
                    row["unit_price"]
                ),
                "consumption_value": clean_float(
                    row["value"]
                ),
                "contribution_pct": clean_float(
                    row["contribution_pct"]
                ),
                "cumulative_pct": clean_float(
                    cumulative
                ),
                "class": abc_class,
            }
        )

    summary = _build_abc_summary(
        items, total_value
    )

    summary["value_metric"] = value_metric

    return items, summary


def _build_abc_summary(items, total_value):
    """
    Build ABC summary populated from computed items.
    """

    summary = {
        "total_items": len(items),
        "total_value": clean_float(total_value),
        "counts": {"A": 0, "B": 0, "C": 0},
        "value_by_class": {
            "A": 0.0,
            "B": 0.0,
            "C": 0.0,
        },
        "value_metric": "Revenue",
        "thresholds": {
            "a": DEFAULT_ABC_THRESHOLDS["a"],
            "b": DEFAULT_ABC_THRESHOLDS["b"],
        },
    }

    for item in items:
        cls = item["class"]
        summary["counts"][cls] += 1
        summary["value_by_class"][cls] += (
            item["consumption_value"]
        )

    for cls in ["A", "B", "C"]:
        value_pct = (
            (summary["value_by_class"][cls] / total_value * 100.0)
            if total_value > 0
            else 0.0
        )
        summary["value_by_class"][cls] = clean_float(
            summary["value_by_class"][cls]
        )
        summary[
            f"value_pct_{cls.lower()}"
        ] = clean_float(value_pct)

    return summary


def _empty_abc_summary():
    """
    Empty summary for no-data case.
    """

    return {
        "total_items": 0,
        "total_value": 0.0,
        "counts": {"A": 0, "B": 0, "C": 0},
        "value_by_class": {
            "A": 0.0,
            "B": 0.0,
            "C": 0.0,
        },
        "value_pct_a": 0.0,
        "value_pct_b": 0.0,
        "value_pct_c": 0.0,
        "value_metric": "Revenue",
        "thresholds": {
            "a": DEFAULT_ABC_THRESHOLDS["a"],
            "b": DEFAULT_ABC_THRESHOLDS["b"],
        },
    }


# ============================================================
# XYZ CLASSIFICATION
# ============================================================

DEFAULT_XYZ_THRESHOLDS = {"x": 0.50, "y": 1.00}
DEFAULT_MIN_PERIODS = 2


def calculate_xyz(
    df,
    period="M",
    cv_x=0.50,
    cv_y=1.00,
    min_periods=DEFAULT_MIN_PERIODS,
):
    """
    Compute XYZ classification for each product based on
    demand variability (Coefficient of Variation).

    Methodology:
      1. Aggregate demand (Quantity sold) per product per period.
         - Default period: month ("M").
      2. For each product compute:
           mean demand, std deviation, CV = std / mean
      3. Classify:
           X: CV <= cv_x
           Y: cv_x < CV <= cv_y
           Z: CV > cv_y
      4. Handle zero mean safely (No Demand / Unclassified).
      5. Handle insufficient number of periods safely.

    Returns (items, summary).
    """

    if df is None or df.empty:
        return [], _empty_xyz_summary()

    cv_x = _clean_threshold(cv_x)
    cv_y = _clean_threshold(cv_y)
    min_periods = max(1, int(min_periods))

    work = df.copy()

    # Ensure numeric quantity
    work["Quantity"] = pd.to_numeric(
        work["Quantity"], errors="coerce"
    ).fillna(0.0)

    # Build period key
    work["Period"] = work["Date"].dt.to_period(period)

    demand = (
        work.groupby(
            ["ProductID", "Period"]
        )["Quantity"]
        .sum()
        .reset_index()
    )

    grouped = (
        demand.groupby("ProductID")["Quantity"]
    )

    result = pd.DataFrame(
        {
            "mean": grouped.mean(),
            "std": grouped.std(ddof=0),
            "periods": grouped.count(),
        }
    ).reset_index()

    result["ProductID"] = result["ProductID"].astype(str)

    items = []
    total_periods = int(
        demand["Period"].nunique()
    )

    for _, row in result.iterrows():

        mean = float(row["mean"])
        std = float(row["std"])
        periods = int(row["periods"])

        if mean == 0:
            xyz_class = "ND"
            class_label = "No Demand"
            cv = 0.0
        elif periods < min_periods:
            xyz_class = "U"
            class_label = "Unclassified"
            cv = (
                std / mean if mean else 0.0
            )
        else:
            cv = std / mean
            if cv <= cv_x:
                xyz_class = "X"
                class_label = "Stable"
            elif cv <= cv_y:
                xyz_class = "Y"
                class_label = "Moderately Variable"
            else:
                xyz_class = "Z"
                class_label = "Highly Variable"

        items.append(
            {
                "product_id": str(
                    row["ProductID"]
                ),
                "mean_demand": clean_float(mean),
                "std_dev": clean_float(std),
                "cv": clean_float(cv),
                "cv_pct": clean_float(cv * 100.0),
                "class": xyz_class,
                "class_label": class_label,
                "periods": periods,
            }
        )

    summary = _build_xyz_summary(items)

    summary["period"] = period
    summary["total_periods"] = total_periods
    summary["min_periods"] = min_periods
    summary["thresholds"] = {"x": cv_x, "y": cv_y}

    return items, summary


def _build_xyz_summary(items):
    """
    Build XYZ summary populated from computed items.
    """

    counts = {
        "X": 0,
        "Y": 0,
        "Z": 0,
        "ND": 0,
        "U": 0,
    }

    cv_values = []

    for item in items:

        cls = item["class"]
        counts[cls] = counts.get(cls, 0) + 1

        if item["cv"] > 0 and (
            cls in ("X", "Y", "Z")
        ):
            cv_values.append(item["cv"])

    most_stable = None
    most_variable = None

    classified = [
        item for item in items
        if item["class"] in ("X", "Y", "Z")
        and item["mean_demand"] > 0
    ]

    if classified:
        most_stable = min(
            classified,
            key=lambda i: i["cv"],
        )
        most_variable = max(
            classified,
            key=lambda i: i["cv"],
        )

    return {
        "total_items": len(items),
        "counts": counts,
        "average_cv": clean_float(
            (sum(cv_values) / len(cv_values))
            if cv_values
            else 0.0
        ),
        "most_stable": (
            {
                "product_id":
                    most_stable["product_id"],
                "cv": clean_float(
                    most_stable["cv"]
                ),
                "mean_demand": clean_float(
                    most_stable["mean_demand"]
                ),
            }
            if most_stable
            else None
        ),
        "most_variable": (
            {
                "product_id":
                    most_variable["product_id"],
                "cv": clean_float(
                    most_variable["cv"]
                ),
                "mean_demand": clean_float(
                    most_variable["mean_demand"]
                ),
            }
            if most_variable
            else None
        ),
        "thresholds": {
            "x": DEFAULT_XYZ_THRESHOLDS["x"],
            "y": DEFAULT_XYZ_THRESHOLDS["y"],
        },
        "min_periods": DEFAULT_MIN_PERIODS,
    }


def _empty_xyz_summary():
    """
    Empty summary for no-data case.
    """

    return {
        "total_items": 0,
        "counts": {
            "X": 0,
            "Y": 0,
            "Z": 0,
            "ND": 0,
            "U": 0,
        },
        "average_cv": 0.0,
        "most_stable": None,
        "most_variable": None,
        "thresholds": {
            "x": DEFAULT_XYZ_THRESHOLDS["x"],
            "y": DEFAULT_XYZ_THRESHOLDS["y"],
        },
        "min_periods": DEFAULT_MIN_PERIODS,
        "total_periods": 0,
    }


# ============================================================
# ABC-XYZ MATRIX
# ============================================================

def calculate_abc_xyz_matrix(
    abc_items,
    xyz_items,
):
    """
    Combine ABC and XYZ classifications into a 3x3 matrix.

    Combination strategy (standard):
        A = high value, B = medium value, C = low value
        X = stable, Y = moderate variability, Z = high variability

    Returns matrix counts + percentage breakdown.
    """

    abc_map = {
        item["product_id"]: item
        for item in abc_items
    }

    xyz_map = {
        item["product_id"]: item
        for item in xyz_items
    }

    cells = {}

    for abc_class in ["A", "B", "C"]:
        for xyz_class in ["X", "Y", "Z"]:
            cells[f"{abc_class}{xyz_class}"] = []

    shared_ids = set(abc_map.keys()) & set(xyz_map.keys())

    for product_id in shared_ids:

        abc_class = abc_map[product_id]["class"]
        xyz_class = xyz_map[product_id]["class"]

        if abc_class not in (
            "A", "B", "C"
        ):
            continue

        if xyz_class not in (
            "X", "Y", "Z"
        ):
            continue

        cells[
            f"{abc_class}{xyz_class}"
        ].append(
            {
                "product_id": product_id,
                "product_name": abc_map[
                    product_id
                ].get("product_name")
                or abc_map[product_id][
                    "product_id"
                ],
                "consumption_value":
                    abc_map[product_id][
                        "consumption_value"
                    ],
                "abc_class": abc_class,
                "xyz_class": xyz_class,
            }
        )

    matrix_counts = {}

    matrix_percentages = {}

    total = sum(
        len(cells[key])
        for key in cells
    )

    for abc_class in ["A", "B", "C"]:
        matrix_counts[abc_class] = {}
        matrix_percentages[abc_class] = {}
        for xyz_class in ["X", "Y", "Z"]:
            count = len(
                cells[f"{abc_class}{xyz_class}"]
            )
            matrix_counts[abc_class][xyz_class] = count
            matrix_percentages[abc_class][xyz_class] = (
                clean_float(
                    count / total * 100.0
                )
                if total > 0
                else 0.0
            )

    return {
        "matrix_counts": matrix_counts,
        "matrix_percentages": matrix_percentages,
        "cells": {
            key: value
            for key, value in cells.items()
        },
        "total": total,
        "insights": _generate_matrix_insights(
            matrix_counts, total
        ),
    }


def _generate_matrix_insights(
    matrix_counts, total
):
    """
    Generate business insights based on actual counts.
    """

    if total <= 0:
        return []

    insights = []

    def count(abc, xyz):
        return matrix_counts.get(
            abc, {}
        ).get(xyz, 0)

    # High-value + stable
    ax = count("A", "X")
    insights.append(
        {
            "combination": "AX",
            "count": ax,
            "percent": clean_float(
                ax / total * 100.0
            ),
            "message": (
                "High-value items with stable demand. "
                "These should receive tight inventory control "
                "and reliable replenishment."
            ),
        }
    )

    az = count("A", "Z")
    insights.append(
        {
            "combination": "AZ",
            "count": az,
            "percent": clean_float(
                az / total * 100.0
            ),
            "message": (
                "High-value items with highly variable demand. "
                "These require careful forecasting, safety-stock "
                "review, and close monitoring."
            ),
        }
    )

    cx = count("C", "X")
    insights.append(
        {
            "combination": "CX",
            "count": cx,
            "percent": clean_float(
                cx / total * 100.0
            ),
            "message": (
                "Low-value items with stable demand. "
                "These may be suitable for simpler "
                "replenishment policies."
            ),
        }
    )

    cz = count("C", "Z")
    insights.append(
        {
            "combination": "CZ",
            "count": cz,
            "percent": clean_float(
                cz / total * 100.0
            ),
            "message": (
                "Low-value items with highly variable demand. "
                "Avoid excessive inventory investment unless "
                "service requirements justify it."
            ),
        }
    )

    # Additional insights derived from data
    if count("A", "Y") > 0:
        insights.append(
            {
                "combination": "AY",
                "count": count("A", "Y"),
                "percent": clean_float(
                    count("A", "Y") / total * 100.0
                ),
                "message": (
                    "High-value items with moderately variable "
                    "demand. Balance availability with "
                    "moderate safety stock."
                ),
            }
        )

    if count("B", "X") + count("B", "Y") + count("B", "Z") > 0:
        insights.append(
            {
                "combination": "B*",
                "count": (
                    count("B", "X")
                    + count("B", "Y")
                    + count("B", "Z")
                ),
                "percent": clean_float(
                    (
                        count("B", "X")
                        + count("B", "Y")
                        + count("B", "Z")
                    )
                    / total
                    * 100.0
                ),
                "message": (
                    "Medium-value items. Apply standard "
                    "inventory policies with moderate "
                    "monitoring."
                ),
            }
        )

    insights.sort(
        key=lambda i: i["count"],
        reverse=True,
    )

    return insights


# ============================================================
# DEMAND TREND (per product)
# ============================================================

def get_product_demand_trend(
    df,
    product_id,
    period="M",
):
    """
    Historical demand trend for a single product.
    Used to explain WHY a product was classified X / Y / Z.
    """

    if df is None or df.empty:
        return []

    product_id = str(product_id)

    work = df.copy()

    work["Quantity"] = pd.to_numeric(
        work["Quantity"], errors="coerce"
    ).fillna(0.0)

    work["Period"] = work["Date"].dt.to_period(period)

    subset = work[work["ProductID"].astype(str) == product_id]

    if subset.empty:
        return []

    trend = (
        subset.groupby("Period")["Quantity"]
        .sum()
        .reset_index()
    )

    trend["label"] = trend["Period"].astype(str)

    # Order chronologically
    trend = (
        trend.sort_values("Period")
        .reset_index(drop=True)
    )

    return [
        {
            "period": str(row["Period"]),
            "label": str(row["Period"]),
            "quantity": clean_float(
                row["Quantity"]
            ),
        }
        for _, row in trend.iterrows()
    ]


# ============================================================
# HELPERS
# ============================================================

def clean_float(value):
    """
    Convert a value to a safe finite float.
    """

    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0

    if not math.isfinite(value):
        return None

    return value


def _clean_threshold(value):
    """
    Parse and clamp a threshold to [0, 1].
    """

    try:
        value = float(value)
    except (TypeError, ValueError):
        return 1.0

    if not math.isfinite(value):
        return 1.0

    return max(0.0, min(value, 1.0))
