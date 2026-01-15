#!/usr/bin/env python3
"""
Test suite to verify all required dependencies are installed.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_itsdangerous_installed():
    """Test that itsdangerous package is installed."""
    print("Testing itsdangerous installation...")
    
    try:
        import itsdangerous
        from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
        
        # Verify version if possible
        try:
            version = itsdangerous.__version__
            print(f"  itsdangerous version: {version}")
        except:
            pass
        
        print("  ✅ itsdangerous is installed")
        return True
    except ImportError as e:
        print(f"  ❌ itsdangerous is not installed: {e}")
        return False


def test_database_imports():
    """Test that database.py imports work."""
    print("Testing database.py imports...")
    
    try:
        import database
        
        # Verify key functions exist
        assert hasattr(database, 'init_db'), "init_db function should exist"
        assert hasattr(database, 'create_user'), "create_user function should exist"
        assert hasattr(database, 'get_user_collection'), "get_user_collection function should exist"
        assert hasattr(database, 'add_collection_item'), "add_collection_item function should exist"
        
        print("  ✅ database.py imports work")
        return True
    except Exception as e:
        print(f"  ❌ database.py imports failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auth_imports():
    """Test that auth.py imports work."""
    print("Testing auth.py imports...")
    
    try:
        import auth
        
        # Verify key functions exist
        assert hasattr(auth, 'hash_password'), "hash_password function should exist"
        assert hasattr(auth, 'verify_password'), "verify_password function should exist"
        assert hasattr(auth, 'create_session_token'), "create_session_token function should exist"
        assert hasattr(auth, 'verify_session_token'), "verify_session_token function should exist"
        assert hasattr(auth, 'get_current_user'), "get_current_user function should exist"
        
        print("  ✅ auth.py imports work")
        return True
    except Exception as e:
        print(f"  ❌ auth.py imports failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_collection_ui_imports():
    """Test that collection_ui.py imports work."""
    print("Testing collection_ui.py imports...")
    
    try:
        import collection_ui
        
        # Verify key functions exist
        assert hasattr(collection_ui, 'load_collection'), "load_collection function should exist"
        assert hasattr(collection_ui, 'save_collection'), "save_collection function should exist"
        assert hasattr(collection_ui, 'app'), "app should exist"
        
        # Verify app is FastAPI app
        from fastapi import FastAPI
        assert isinstance(collection_ui.app, FastAPI), "app should be FastAPI instance"
        
        print("  ✅ collection_ui.py imports work")
        return True
    except Exception as e:
        print(f"  ❌ collection_ui.py imports failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fastapi_testclient():
    """Test that FastAPI TestClient is available."""
    print("Testing FastAPI TestClient...")
    
    try:
        from fastapi.testclient import TestClient
        print("  ✅ FastAPI TestClient is available")
        return True
    except ImportError as e:
        print(f"  ❌ FastAPI TestClient not available: {e}")
        return False


def test_sqlite3_available():
    """Test that sqlite3 is available."""
    print("Testing sqlite3 availability...")
    
    try:
        import sqlite3
        print(f"  ✅ sqlite3 is available (version: {sqlite3.sqlite_version})")
        return True
    except ImportError as e:
        print(f"  ❌ sqlite3 not available: {e}")
        return False


def main():
    """Run all dependency tests."""
    print("\n" + "=" * 60)
    print("DEPENDENCIES TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_itsdangerous_installed,
        test_database_imports,
        test_auth_imports,
        test_collection_ui_imports,
        test_fastapi_testclient,
        test_sqlite3_available,
    ]
    
    results = {}
    for test_func in tests:
        try:
            results[test_func.__name__] = test_func()
        except Exception as e:
            print(f"\n❌ {test_func.__name__} crashed: {e}")
            import traceback
            traceback.print_exc()
            results[test_func.__name__] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if not all_passed:
        print("\n⚠️  Some dependencies are missing. Run: pip install -r requirements.txt")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
