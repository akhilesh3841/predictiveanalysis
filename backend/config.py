"""
MongoDB Configuration for Retail Analytics
"""
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://akhileshyadav3841_db_user:b5COMxpGuCRBTT5P@cluster0.tbs5c7f.mongodb.net/?appName=Cluster0")
DB_NAME = os.getenv("DB_NAME", "retail_analytics")
COLLECTIONS = {
    "transactions": "transactions",
    "products": "products",
    "customers": "customers",
    "daily_sales": "daily_sales",
    "monthly_sales": "monthly_sales",
    "product_daily_sales": "product_daily_sales",
    "forecasts": "forecasts"
}

class Config:
    """Base configuration"""
    DEBUG = False
    TESTING = False
    JSON_SORT_KEYS = False

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
