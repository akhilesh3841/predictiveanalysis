#!/usr/bin/env python
"""Test database connection and basic functionality"""
import sys
import os
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

print("Step 1: Loading configuration...")
try:
    from config import MONGODB_URI, DB_NAME, COLLECTIONS
    print(f"✓ Configuration loaded: DB_NAME={DB_NAME}")
except Exception as e:
    print(f"✗ Failed to load config: {e}")
    sys.exit(1)

print("\nStep 2: Importing database module...")
try:
    from db import MongoDatabase
    print("✓ Database module imported")
except Exception as e:
    print(f"✗ Failed to import database: {e}")
    sys.exit(1)

print("\nStep 3: Creating database connection...")
try:
    start_time = time.time()
    db = MongoDatabase()
    elapsed = time.time() - start_time
    print(f"✓ Database instance created ({elapsed:.2f}s)")
except Exception as e:
    print(f"✗ Failed to create database: {e}")
    sys.exit(1)

print("\nStep 4: Connecting to database...")
try:
    start_time = time.time()
    result = db.connect()
    elapsed = time.time() - start_time
    if result:
        print(f"✓ Connected to database ({elapsed:.2f}s)")
    else:
        print(f"✗ Failed to connect to database ({elapsed:.2f}s)")
except Exception as e:
    print(f"✗ Connection error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 5: Testing collection access...")
try:
    col = db.get_collection('test')
    print(f"✓ Got test collection")
except Exception as e:
    print(f"✗ Failed to get collection: {e}")
    sys.exit(1)

print("\n✓ All tests passed!")
