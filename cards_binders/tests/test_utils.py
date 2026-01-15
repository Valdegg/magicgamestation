#!/usr/bin/env python3
"""
Test utilities for database and authentication tests.
"""

import os
import sys
import tempfile
from unittest.mock import Mock
from fastapi import Request
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


TEST_DB_FILE = "test_collections.db"
TEST_COLLECTION_FILE = "test_collection.json"


def get_test_db_path():
    """Return path to test database file."""
    return TEST_DB_FILE


def cleanup_test_db():
    """Delete test database file if it exists."""
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


def cleanup_test_collection_file():
    """Delete test collection.json file if it exists."""
    if os.path.exists(TEST_COLLECTION_FILE):
        os.remove(TEST_COLLECTION_FILE)


def create_test_user(username="testuser", password="testpass123"):
    """Helper to create a test user. Returns user_id."""
    import database
    import auth
    
    # Temporarily set database to test DB
    original_db_file = database.DB_FILE
    database.DB_FILE = TEST_DB_FILE
    
    try:
        # Initialize test database
        database.init_db()
        
        # Create user
        password_hash = auth.hash_password(password)
        user_id = database.create_user(username, password_hash)
        
        return user_id
    finally:
        # Restore original DB file
        database.DB_FILE = original_db_file


def get_test_client():
    """Create FastAPI TestClient with test app."""
    import collection_ui
    
    # Temporarily set database to test DB
    import database
    original_db_file = database.DB_FILE
    database.DB_FILE = TEST_DB_FILE
    
    try:
        # Initialize test database
        database.init_db()
        
        # Create test client
        client = TestClient(collection_ui.app)
        return client
    finally:
        # Note: We don't restore here because the client needs the test DB
        # The caller should handle cleanup
        pass


def create_mock_request(cookies=None):
    """Create mock Request object with optional cookies."""
    request = Mock(spec=Request)
    request.cookies = cookies or {}
    return request


def restore_db_file():
    """Restore original database file path."""
    import database
    database.DB_FILE = "collections.db"
