#!/usr/bin/env python3
"""
Test suite for collection_ui.py load_collection and save_collection functions.
Tests both user_id=None (JSON) and user_id provided (database) scenarios.
"""

import os
import sys
import json
import shutil

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import collection_ui
import database
import auth
from test_utils import cleanup_test_db, cleanup_test_collection_file, get_test_db_path, TEST_COLLECTION_FILE


def test_load_collection_no_user():
    """Test loading collection from JSON when user_id=None."""
    print("Testing load_collection() with user_id=None (JSON)...")
    
    try:
        # Create test collection.json
        test_collection = [
            {"name": "Test Card 1", "sets": ["Alpha"]},
            {"name": "Test Card 2", "sets": ["Beta"]}
        ]
        
        # Save original if exists
        original_exists = os.path.exists(collection_ui.COLLECTION_FILE)
        if original_exists:
            shutil.copy(collection_ui.COLLECTION_FILE, collection_ui.COLLECTION_FILE + ".backup")
        
        # Create test file
        with open(TEST_COLLECTION_FILE, 'w') as f:
            json.dump(test_collection, f)
        
        # Temporarily set collection file
        original_file = collection_ui.COLLECTION_FILE
        collection_ui.COLLECTION_FILE = TEST_COLLECTION_FILE
        
        try:
            # Load collection (user_id=None should use JSON)
            # Pass filepath explicitly since default parameters are evaluated at definition time
            collection = collection_ui.load_collection(filepath=TEST_COLLECTION_FILE, user_id=None)
            
            assert isinstance(collection, list), "Collection should be a list"
            assert len(collection) == 2, "Should load 2 items"
            assert collection[0]["name"] == "Test Card 1", "First item should match"
            assert collection[1]["name"] == "Test Card 2", "Second item should match"
            
            print("  ✅ load_collection_no_user() test passed")
            return True
        finally:
            collection_ui.COLLECTION_FILE = original_file
            cleanup_test_collection_file()
            if original_exists:
                shutil.move(collection_ui.COLLECTION_FILE + ".backup", collection_ui.COLLECTION_FILE)
    except Exception as e:
        print(f"  ❌ load_collection_no_user() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_load_collection_with_user():
    """Test loading collection from database when user_id provided."""
    print("Testing load_collection() with user_id (database)...")
    
    original_db_file = database.DB_FILE
    database.DB_FILE = get_test_db_path()
    
    try:
        cleanup_test_db()
        database.init_db()
        
        # Create user and add items
        user_id = database.create_user("testuser", auth.hash_password("pass123"))
        item1 = {"name": "DB Card 1", "sets": ["Alpha"]}
        item2 = {"name": "DB Card 2", "sets": ["Beta"]}
        database.add_collection_item(user_id, item1)
        database.add_collection_item(user_id, item2)
        
        # Load collection from database
        collection = collection_ui.load_collection(user_id=user_id)
        
        assert isinstance(collection, list), "Collection should be a list"
        assert len(collection) == 2, "Should load 2 items from database"
        assert collection[0]["name"] == "DB Card 1", "First item should match"
        assert collection[1]["name"] == "DB Card 2", "Second item should match"
        
        print("  ✅ load_collection_with_user() test passed")
        return True
    except Exception as e:
        print(f"  ❌ load_collection_with_user() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        database.DB_FILE = original_db_file
        cleanup_test_db()


def test_save_collection_no_user():
    """Test saving collection to JSON when user_id=None."""
    print("Testing save_collection() with user_id=None (JSON)...")
    
    try:
        # Create test collection
        test_collection = [
            {"name": "Saved Card 1", "sets": ["Alpha"]},
            {"name": "Saved Card 2", "sets": ["Beta"]}
        ]
        
        # Save original if exists
        original_exists = os.path.exists(collection_ui.COLLECTION_FILE)
        if original_exists:
            shutil.copy(collection_ui.COLLECTION_FILE, collection_ui.COLLECTION_FILE + ".backup")
        
        # Temporarily set collection file
        original_file = collection_ui.COLLECTION_FILE
        collection_ui.COLLECTION_FILE = TEST_COLLECTION_FILE
        
        try:
            # Save collection (user_id=None should save to JSON)
            # Pass filepath explicitly since default parameters are evaluated at definition time
            result = collection_ui.save_collection(test_collection, filepath=TEST_COLLECTION_FILE, user_id=None)
            assert result is True, "Save should succeed"
            
            # Verify file was created and contains correct data
            assert os.path.exists(TEST_COLLECTION_FILE), "Collection file should exist"
            
            with open(TEST_COLLECTION_FILE, 'r') as f:
                saved_collection = json.load(f)
            
            assert len(saved_collection) == 2, "Should have 2 items"
            assert saved_collection[0]["name"] == "Saved Card 1", "First item should match"
            assert saved_collection[1]["name"] == "Saved Card 2", "Second item should match"
            
            print("  ✅ save_collection_no_user() test passed")
            return True
        finally:
            collection_ui.COLLECTION_FILE = original_file
            cleanup_test_collection_file()
            if original_exists:
                shutil.move(collection_ui.COLLECTION_FILE + ".backup", collection_ui.COLLECTION_FILE)
    except Exception as e:
        print(f"  ❌ save_collection_no_user() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_save_collection_with_user():
    """Test saving collection to database when user_id provided."""
    print("Testing save_collection() with user_id (database)...")
    
    original_db_file = database.DB_FILE
    database.DB_FILE = get_test_db_path()
    
    try:
        cleanup_test_db()
        database.init_db()
        
        # Create user
        user_id = database.create_user("testuser", auth.hash_password("pass123"))
        
        # Create test collection
        test_collection = [
            {"name": "DB Saved Card 1", "sets": ["Alpha"]},
            {"name": "DB Saved Card 2", "sets": ["Beta"]}
        ]
        
        # Save collection to database
        result = collection_ui.save_collection(test_collection, user_id=user_id)
        assert result is True, "Save should succeed"
        
        # Verify items were saved to database
        collection = database.get_user_collection(user_id)
        assert len(collection) == 2, "Should have 2 items in database"
        assert collection[0]["name"] == "DB Saved Card 1", "First item should match"
        assert collection[1]["name"] == "DB Saved Card 2", "Second item should match"
        
        print("  ✅ save_collection_with_user() test passed")
        return True
    except Exception as e:
        print(f"  ❌ save_collection_with_user() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        database.DB_FILE = original_db_file
        cleanup_test_db()


def test_backward_compatibility():
    """Test that non-logged-in users still use JSON file."""
    print("Testing backward_compatibility()...")
    
    try:
        # Create test collection.json
        test_collection = [
            {"name": "JSON Card", "sets": ["Alpha"]}
        ]
        
        # Save original if exists
        original_exists = os.path.exists(collection_ui.COLLECTION_FILE)
        if original_exists:
            shutil.copy(collection_ui.COLLECTION_FILE, collection_ui.COLLECTION_FILE + ".backup")
        
        # Temporarily set collection file
        original_file = collection_ui.COLLECTION_FILE
        collection_ui.COLLECTION_FILE = TEST_COLLECTION_FILE
        
        try:
            # Save to test file
            with open(TEST_COLLECTION_FILE, 'w') as f:
                json.dump(test_collection, f)
            
            # Load without user_id (should use JSON)
            # Pass filepath explicitly since default parameters are evaluated at definition time
            collection = collection_ui.load_collection(filepath=TEST_COLLECTION_FILE, user_id=None)
            assert len(collection) == 1, "Should load from JSON"
            assert collection[0]["name"] == "JSON Card", "Should match JSON data"
            
            # Modify and save without user_id (should save to JSON)
            collection[0]["name"] = "Modified JSON Card"
            result = collection_ui.save_collection(collection, filepath=TEST_COLLECTION_FILE, user_id=None)
            assert result is True, "Save should succeed"
            
            # Verify JSON file was updated
            with open(TEST_COLLECTION_FILE, 'r') as f:
                saved = json.load(f)
            assert saved[0]["name"] == "Modified JSON Card", "JSON file should be updated"
            
            print("  ✅ backward_compatibility() test passed")
            return True
        finally:
            collection_ui.COLLECTION_FILE = original_file
            cleanup_test_collection_file()
            if original_exists:
                shutil.move(collection_ui.COLLECTION_FILE + ".backup", collection_ui.COLLECTION_FILE)
    except Exception as e:
        print(f"  ❌ backward_compatibility() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all collection function tests."""
    print("\n" + "=" * 60)
    print("COLLECTION FUNCTIONS TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_load_collection_no_user,
        test_load_collection_with_user,
        test_save_collection_no_user,
        test_save_collection_with_user,
        test_backward_compatibility,
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
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
