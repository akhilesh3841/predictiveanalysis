"""
MongoDB database connection and initialization
"""

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import logging
import os
import sys

# Add backend folder to path
backend_path = os.path.dirname(os.path.abspath(__file__))

if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

try:
    from config import MONGODB_URI, DB_NAME, COLLECTIONS
except ImportError:
    from backend.config import MONGODB_URI, DB_NAME, COLLECTIONS

logger = logging.getLogger(__name__)


class MongoDatabase:

    _instance = None
    _client = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self):
        """Establish real MongoDB Atlas connection"""

        try:
            logger.info("Connecting to MongoDB Atlas...")

            self._client = MongoClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=10000
            )

            # Test connection
            self._client.admin.command("ping")

            # Select database
            self._db = self._client[DB_NAME]

            logger.info(
                f"Successfully connected to MongoDB database: {DB_NAME}"
            )

            # Create indexes
            self._create_indexes()

            return True

        except ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB server selection error: {e}")
            raise

        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise

    def disconnect(self):
        """Close MongoDB connection"""

        if self._client:
            self._client.close()
            self._client = None
            self._db = None

            logger.info("Disconnected from MongoDB")

    def get_db(self):
        """Get database instance"""

        if self._db is None:
            self.connect()

        return self._db

    def get_collection(self, collection_name):
        """Get collection by name"""

        if self._db is None:
            self.connect()

        return self._db[collection_name]

    def _create_indexes(self):
        """Create indexes for better query performance"""

        try:

            # Transactions
            self._db[
                COLLECTIONS["transactions"]
            ].create_index("Date")

            self._db[
                COLLECTIONS["transactions"]
            ].create_index("ProductID")

            self._db[
                COLLECTIONS["transactions"]
            ].create_index("CustomerID")

            # Products
            self._db[
                COLLECTIONS["products"]
            ].create_index(
                "ProductID",
                unique=True
            )

            # Customers
            self._db[
                COLLECTIONS["customers"]
            ].create_index(
                "CustomerID",
                unique=True
            )

            # Daily sales
            self._db[
                COLLECTIONS["daily_sales"]
            ].create_index("Date")

            # Monthly sales
            self._db[
                COLLECTIONS["monthly_sales"]
            ].create_index("YearMonth")

            # Product daily sales
            self._db[
                COLLECTIONS["product_daily_sales"]
            ].create_index(
                [
                    ("ProductID", 1),
                    ("Date", 1)
                ]
            )

            logger.info("MongoDB indexes created successfully")

        except Exception as e:
            logger.warning(
                f"Index creation warning: {e}"
            )


# Global database instance
db = MongoDatabase()


def get_db():
    """Get database connection"""
    return db.get_db()


def close_db():
    """Close database connection"""
    db.disconnect()