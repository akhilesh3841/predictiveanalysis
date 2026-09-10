"""
CSV Data Importer for Retail Analytics
Imports cleaned CSV files into MongoDB Atlas
"""

import sys
import os
import logging
from pathlib import Path

import pandas as pd
from pymongo import MongoClient

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import get_db
from backend.config import COLLECTIONS
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

CHUNK_SIZE = 5000


# ============================================================
# DATA IMPORTER
# ============================================================

class DataImporter:

    def __init__(self):
        logger.info("Connecting to MongoDB Atlas...")

        self.db = get_db()

        if self.db is None:
            raise ConnectionError("Could not connect to MongoDB")

        self.data_folder = PROJECT_ROOT / "data"

        logger.info(f"Data folder: {self.data_folder}")
        logger.info(f"Database: {self.db.name}")

    # ========================================================
    # HELPER: CLEAR COLLECTION
    # ========================================================

    def clear_collection(self, collection_name):
        """
        Delete all existing documents from a collection.
        """

        logger.info(
            f"Clearing existing collection: {collection_name}"
        )

        result = self.db[collection_name].delete_many({})

        logger.info(
            f"Deleted {result.deleted_count} existing documents"
        )

    # ========================================================
    # HELPER: INSERT DATAFRAME IN CHUNKS
    # ========================================================

    def insert_dataframe(
        self,
        df,
        collection_name,
        date_columns=None
    ):
        """
        Insert DataFrame into MongoDB in chunks.
        """

        if date_columns is None:
            date_columns = []

        # Convert date columns
        for column in date_columns:
            if column in df.columns:
                df[column] = pd.to_datetime(
                    df[column],
                    errors="coerce"
                )

        # Replace NaN / NaT with None
        df = df.astype(object).where(
            pd.notna(df),
            None
        )

        total_inserted = 0

        collection = self.db[collection_name]

        # Insert in chunks
        for start in range(0, len(df), CHUNK_SIZE):

            chunk = df.iloc[start:start + CHUNK_SIZE]

            records = chunk.to_dict(
                orient="records"
            )

            if not records:
                continue

            result = collection.insert_many(
                records,
                ordered=False
            )

            total_inserted += len(
                result.inserted_ids
            )

            logger.info(
                f"{collection_name}: "
                f"{total_inserted}/{len(df)} records inserted"
            )

        return total_inserted

    # ========================================================
    # TRANSACTIONS
    # ========================================================

    def import_transactions(
        self,
        filename="sales_cleaned.csv"
    ):

        try:

            filepath = self.data_folder / filename

            if not filepath.exists():
                logger.error(
                    f"File not found: {filepath}"
                )
                return False

            logger.info(
                f"Importing transactions from {filename}..."
            )

            df = pd.read_csv(
                filepath,
                low_memory=False
            )

            logger.info(
                f"Original transaction rows: {len(df)}"
            )

            # Remove duplicate columns
            df = df.loc[
                :,
                ~df.columns.duplicated()
            ]

            # ------------------------------------------------
            # DATE
            # ------------------------------------------------

            if "InvoiceDate" in df.columns:

                df["Date"] = pd.to_datetime(
                    df["InvoiceDate"],
                    errors="coerce"
                )

            elif "Date" in df.columns:

                df["Date"] = pd.to_datetime(
                    df["Date"],
                    errors="coerce"
                )

            # ------------------------------------------------
            # RENAME COLUMNS
            # ------------------------------------------------

            rename_map = {}

            if "StockCode" in df.columns:
                rename_map["StockCode"] = "ProductID"

            if "Description" in df.columns:
                rename_map["Description"] = "ProductName"

            if (
                "Price" in df.columns
                and "UnitPrice" not in df.columns
            ):
                rename_map["Price"] = "UnitPrice"

            df = df.rename(
                columns=rename_map
            )

            # ------------------------------------------------
            # REVENUE
            # ------------------------------------------------

            if "Revenue" not in df.columns:

                if (
                    "Quantity" in df.columns
                    and "UnitPrice" in df.columns
                ):

                    df["Revenue"] = (
                        df["Quantity"]
                        * df["UnitPrice"]
                    )

            # ------------------------------------------------
            # NUMERIC CONVERSION
            # ------------------------------------------------

            numeric_columns = [
                "Quantity",
                "UnitPrice",
                "Revenue",
                "CustomerID"
            ]

            for column in numeric_columns:

                if column in df.columns:

                    df[column] = pd.to_numeric(
                        df[column],
                        errors="coerce"
                    )

            # ------------------------------------------------
            # IMPORTANT
            # ------------------------------------------------
            # CustomerID CAN be missing.
            # We only remove rows where Date/ProductID
            # are missing.

            critical_columns = [
                column
                for column in [
                    "Date",
                    "ProductID"
                ]
                if column in df.columns
            ]

            if critical_columns:

                before = len(df)

                df = df.dropna(
                    subset=critical_columns
                )

                removed = before - len(df)

                logger.info(
                    f"Removed {removed} rows "
                    f"with missing critical values"
                )

            # ------------------------------------------------
            # SELECT REQUIRED COLUMNS
            # ------------------------------------------------

            relevant_columns = [
                "InvoiceNo",
                "ProductID",
                "ProductName",
                "Quantity",
                "Date",
                "UnitPrice",
                "CustomerID",
                "Country",
                "Revenue"
            ]

            available_columns = [
                column
                for column in relevant_columns
                if column in df.columns
            ]

            df = df[
                available_columns
            ]

            logger.info(
                f"Final transaction rows: {len(df)}"
            )

            # ------------------------------------------------
            # CLEAR COLLECTION
            # ------------------------------------------------

            collection_name = COLLECTIONS[
                "transactions"
            ]

            self.clear_collection(
                collection_name
            )

            # ------------------------------------------------
            # INSERT
            # ------------------------------------------------

            inserted = self.insert_dataframe(
                df,
                collection_name,
                date_columns=["Date"]
            )

            logger.info(
                f"[OK] Imported {inserted} "
                f"transaction records"
            )

            return inserted > 0

        except Exception as e:

            logger.exception(
                f"Error importing transactions: {e}"
            )

            return False

    # ========================================================
    # PRODUCTS
    # ========================================================

    def import_products(
        self,
        filename="product_summary.csv"
    ):

        try:

            filepath = self.data_folder / filename

            if not filepath.exists():
                logger.error(
                    f"File not found: {filepath}"
                )
                return False

            logger.info(
                f"Importing products from {filename}..."
            )

            df = pd.read_csv(
                filepath
            )

            # Rename columns
            df = df.rename(
                columns={
                    "StockCode": "ProductID",
                    "Description": "ProductName"
                }
            )

            # Numeric columns
            numeric_columns = [
                "Total_Quantity",
                "Total_Revenue",
                "Average_Price",
                "Transaction_Count"
            ]

            for column in numeric_columns:

                if column in df.columns:

                    df[column] = pd.to_numeric(
                        df[column],
                        errors="coerce"
                    )

            collection_name = COLLECTIONS[
                "products"
            ]

            self.clear_collection(
                collection_name
            )

            inserted = self.insert_dataframe(
                df,
                collection_name
            )

            logger.info(
                f"[OK] Imported {inserted} "
                f"product records"
            )

            return inserted > 0

        except Exception as e:

            logger.exception(
                f"Error importing products: {e}"
            )

            return False

    # ========================================================
    # CUSTOMERS
    # ========================================================

    def import_customers(
        self,
        filename="customer_summary.csv"
    ):

        try:

            filepath = self.data_folder / filename

            if not filepath.exists():
                logger.error(
                    f"File not found: {filepath}"
                )
                return False

            logger.info(
                f"Importing customers from {filename}..."
            )

            df = pd.read_csv(
                filepath
            )

            df = df.rename(
                columns={
                    "Customer ID": "CustomerID"
                }
            )

            numeric_columns = [
                "CustomerID",
                "Total_Quantity",
                "Total_Revenue",
                "Transactions",
                "Unique_Products"
            ]

            for column in numeric_columns:

                if column in df.columns:

                    df[column] = pd.to_numeric(
                        df[column],
                        errors="coerce"
                    )

            # CustomerID is required here because
            # this is specifically customer_summary.

            if "CustomerID" in df.columns:

                df = df.dropna(
                    subset=["CustomerID"]
                )

            collection_name = COLLECTIONS[
                "customers"
            ]

            self.clear_collection(
                collection_name
            )

            inserted = self.insert_dataframe(
                df,
                collection_name
            )

            logger.info(
                f"[OK] Imported {inserted} "
                f"customer records"
            )

            return inserted > 0

        except Exception as e:

            logger.exception(
                f"Error importing customers: {e}"
            )

            return False

    # ========================================================
    # DAILY SALES
    # ========================================================

    def import_daily_sales(
        self,
        filename="daily_sales.csv"
    ):

        try:

            filepath = self.data_folder / filename

            if not filepath.exists():
                logger.error(
                    f"File not found: {filepath}"
                )
                return False

            logger.info(
                f"Importing daily sales from {filename}..."
            )

            df = pd.read_csv(
                filepath
            )

            numeric_columns = [
                "Quantity",
                "Revenue",
                "Transactions"
            ]

            for column in numeric_columns:

                if column in df.columns:

                    df[column] = pd.to_numeric(
                        df[column],
                        errors="coerce"
                    )

            if "Date" in df.columns:

                df["Date"] = pd.to_datetime(
                    df["Date"],
                    errors="coerce"
                )

            collection_name = COLLECTIONS[
                "daily_sales"
            ]

            self.clear_collection(
                collection_name
            )

            inserted = self.insert_dataframe(
                df,
                collection_name,
                date_columns=["Date"]
            )

            logger.info(
                f"[OK] Imported {inserted} "
                f"daily sales records"
            )

            return inserted > 0

        except Exception as e:

            logger.exception(
                f"Error importing daily sales: {e}"
            )

            return False

    # ========================================================
    # MONTHLY SALES
    # ========================================================

    def import_monthly_sales(
        self,
        filename="monthly_sales.csv"
    ):

        try:

            filepath = self.data_folder / filename

            if not filepath.exists():
                logger.error(
                    f"File not found: {filepath}"
                )
                return False

            logger.info(
                f"Importing monthly sales from {filename}..."
            )

            df = pd.read_csv(
                filepath
            )

            numeric_columns = [
                "Quantity",
                "Revenue",
                "Transactions"
            ]

            for column in numeric_columns:

                if column in df.columns:

                    df[column] = pd.to_numeric(
                        df[column],
                        errors="coerce"
                    )

            collection_name = COLLECTIONS[
                "monthly_sales"
            ]

            self.clear_collection(
                collection_name
            )

            inserted = self.insert_dataframe(
                df,
                collection_name
            )

            logger.info(
                f"[OK] Imported {inserted} "
                f"monthly sales records"
            )

            return inserted > 0

        except Exception as e:

            logger.exception(
                f"Error importing monthly sales: {e}"
            )

            return False

    # ========================================================
    # PRODUCT DAILY SALES
    # ========================================================

    def import_product_daily_sales(
        self,
        filename="product_daily_sales.csv"
    ):

        try:

            filepath = self.data_folder / filename

            if not filepath.exists():
                logger.error(
                    f"File not found: {filepath}"
                )
                return False

            logger.info(
                f"Importing product daily sales "
                f"from {filename}..."
            )

            df = pd.read_csv(
                filepath
            )

            numeric_columns = [
                "Quantity",
                "Revenue",
                "Transactions"
            ]

            for column in numeric_columns:

                if column in df.columns:

                    df[column] = pd.to_numeric(
                        df[column],
                        errors="coerce"
                    )

            if "Date" in df.columns:

                df["Date"] = pd.to_datetime(
                    df["Date"],
                    errors="coerce"
                )

            collection_name = COLLECTIONS[
                "product_daily_sales"
            ]

            self.clear_collection(
                collection_name
            )

            inserted = self.insert_dataframe(
                df,
                collection_name,
                date_columns=["Date"]
            )

            logger.info(
                f"[OK] Imported {inserted} "
                f"product daily sales records"
            )

            return inserted > 0

        except Exception as e:

            logger.exception(
                f"Error importing product daily sales: {e}"
            )

            return False

    # ========================================================
    # COMPLETE DAILY
    # ========================================================

    def import_complete_daily(
        self,
        filename="complete_daily.csv"
    ):

        try:

            filepath = self.data_folder / filename

            if not filepath.exists():
                logger.error(
                    f"File not found: {filepath}"
                )
                return False

            logger.info(
                f"Importing forecasting data "
                f"from {filename}..."
            )

            df = pd.read_csv(
                filepath,
                low_memory=False
            )

            logger.info(
                f"Complete daily rows: {len(df)}"
            )

            # Date
            if "Date" in df.columns:

                df["Date"] = pd.to_datetime(
                    df["Date"],
                    errors="coerce"
                )

            # Numeric conversion
            numeric_columns = [
                "Quantity",
                "Revenue",
                "Transactions",
                "UnitPrice",
                "Average_Price",
                "Year",
                "Month",
                "Day",
                "Week",
                "Weekday",
                "Weekday_Num",
                "Quarter",
                "Is_Weekend"
            ]

            for column in numeric_columns:

                if column in df.columns:

                    df[column] = pd.to_numeric(
                        df[column],
                        errors="coerce"
                    )

            # Remove only rows without Date/ProductID
            critical_columns = [
                column
                for column in [
                    "Date",
                    "ProductID"
                ]
                if column in df.columns
            ]

            if critical_columns:

                df = df.dropna(
                    subset=critical_columns
                )

            # complete_daily collection
            collection_name = "complete_daily"

            self.clear_collection(
                collection_name
            )

            inserted = self.insert_dataframe(
                df,
                collection_name,
                date_columns=["Date"]
            )

            logger.info(
                f"[OK] Imported {inserted} "
                f"complete daily records"
            )

            return inserted > 0

        except Exception as e:

            logger.exception(
                f"Error importing complete daily: {e}"
            )

            return False

    # ========================================================
    # IMPORT EVERYTHING
    # ========================================================

    def import_all(self):

        logger.info("=" * 70)
        logger.info("STARTING RETAIL DATA IMPORT")
        logger.info("=" * 70)

        results = {}

        # 1
        results["transactions"] = (
            self.import_transactions()
        )

        # 2
        results["products"] = (
            self.import_products()
        )

        # 3
        results["customers"] = (
            self.import_customers()
        )

        # 4
        results["daily_sales"] = (
            self.import_daily_sales()
        )

        # 5
        results["monthly_sales"] = (
            self.import_monthly_sales()
        )

        # 6
        results["product_daily_sales"] = (
            self.import_product_daily_sales()
        )

        # 7
        results["complete_daily"] = (
            self.import_complete_daily()
        )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        success_count = sum(
            1
            for success in results.values()
            if success
        )

        total = len(results)

        logger.info("=" * 70)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 70)

        for name, success in results.items():

            status = "SUCCESS" if success else "FAILED"

            logger.info(
                f"{name}: {status}"
            )

        logger.info("-" * 70)

        logger.info(
            f"Import completed: "
            f"{success_count}/{total}"
        )

        logger.info("=" * 70)

        return success_count == total


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("RETAIL ANALYTICS - MONGODB DATA IMPORT")
    print("=" * 70)
    print()

    try:

        print("[1/3] Creating DataImporter...")

        importer = DataImporter()

        print("[OK] MongoDB connection established")
        print()

        print("[2/3] Starting data import...")
        print()

        success = importer.import_all()

        print()

        if success:

            print("=" * 70)
            print("[SUCCESS] ALL DATA IMPORTED SUCCESSFULLY")
            print("=" * 70)

            sys.exit(0)

        else:

            print("=" * 70)
            print("[ERROR] SOME DATA IMPORTS FAILED")
            print("=" * 70)

            sys.exit(1)

    except Exception as e:

        print()
        print("=" * 70)
        print("[ERROR] FATAL ERROR")
        print("=" * 70)
        print(str(e))
        print()

        import traceback

        traceback.print_exc()

        sys.exit(1)