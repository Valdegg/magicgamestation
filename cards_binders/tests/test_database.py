#!/usr/bin/env python3
"""
Test suite for database.py module.
Tests database CRUD operations and user isolation.
"""

import os
import sys
import sqlite3

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
from test_utils import cleanup_test_db, get_test_db_path


def test_init_db():
    """Test database initialization creates tables."""
    print("Testing init_db()...")
    
    # Set test database
    original_db_file = database.DB_FILE
    database.DB_FILE = get_test_db_path()
    
    try:
        cleanup_test_db()
        database.init_db()
        
        # Verify database file exists
        assert os.path.exists(get_test_db_path()), "Database file should be created"
        
        # Verify tables exist
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        # Check users table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is not None, "Users table should exist"
        
        # Check collection table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='collection'")
        assert cursor.fetchone() is not None, "Collection table should exist"
        
        conn.close()
        print("  ✅ init_db() test passed")
        return True
    except Exception as e:
        print(f"  ❌ init_db() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        database.DB_FILE = original_db_file
        cleanup_test_db()


def test_create_user():
    """Test user creation and username uniqueness."""
    print("Testing create_user()...")
    
    original_db_file = database.DB_FILE
    database.DB_FILE = get_test_db_path()
    
    try:
        cleanup_test_db()
        database.init_db()
        
        # Create first user
        user_id1 = database.create_user("testuser1", "hash1")
        assert user_id1 is not None, "User creation should return user_id"
        assert isinstance(user_id1, int), "User ID should be integer"
        
        # Try to create duplicate username
        user_id2 = database.create_user("testuser1", "hash2")
        assert user_id2 is None, "Duplicate username should return None"
        
        # Create second user with different username
        user_id3 = database.create_user("testuser2", "hash3")
        assert user_id3 is not None, "Different username should succeed"
        assert user_id3 != user_id1, "Different users should have different IDs"
        
        print("  ✅ create_user() test passed")
        return True
    except Exception as e:
        print(f"  ❌ create_user() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        database.DB_FILE = original_db_file
        cleanup_test_db()


def test_get_user_by_username():
    """Test retrieving user by username."""
    print("Testing get_user_by_username()...")
    
    original_db_file = database.DB_FILE
    database.DB_FILE = get_test_db_path()
    
    try:
        cleanup_test_db()
        database.init_db()
        
        # Create user
        password_hash = "salt:hash123"
        user_id = database.create_user("testuser", password_hash)
        
        # Retrieve user
        user = database.get_user_by_username("testuser")
        assert user is not None, "User should be found"
        assert user["id"] == user_id, "User ID should match"
        assert user["username"] == "testuser", "Username should match"
        assert user["password_hash"] == password_hash, "Password hash should match"
        
        # Try non-existent user
        user2 = database.get_user_by_username("nonexistent")
        assert user2 is None, "Non-existent user should return None"
        
        print("  ✅ get_user_by_username() test passed")
        return True
    except Exception as e:
        print(f"  ❌ get_user_by_username() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        database.DB_FILE = original_db_file
        cleanup_test_db()


def test_get_user_by_id():
    """Test retrieving user by ID."""
    print("Testing get_user_by_id()...")
    
    original_db_file = database.DB_FILE
    database.DB_FILE = get_test_db_path()
    
    try:
        cleanup_test_db()
        database.init_db()
        
        # Create user
        user_id = database.create_user("testuser", "hash123")
        
        # Retrieve user
        user = database.get_user_by_id(user_id)
        assert user is not None, "User should be found"
        assert user["id"] == user_id, "User ID should match"
        assert user["username"] == "testuser", "Username should match"
        
        # Try non-existent user
        user2 = database.get_user_by_id(99999)
        assert user2 is None, "Non-existent user ID should return None"
        
        print("  ✅ get_user_by_id() test passed")
        return True
    except Exception as e:
        print(f"  ❌ get_user_by_id() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        database.DB_FILE = original_db_file
        cleanup_test_db()


def test_get_user_collection():
    """Test getting user collection (empty initially)."""
    print("Testing get_user_collection()...")
    
    original_db_file = database.DB_FILE
    database.DB_FILE = get_test_db_path()
    
    try:
        cleanup_test_db()
        database.init_db()
        
        # Create user
        user_id = database.create_user("testuser", "hash123")
        
        # Get empty collection
        collection = database.get_user_collection(user_id)
        assert isinstance(collection, list), "Collection should be a list"
        assert len(collection) == 0, "New user should have empty collection"
        
        print("  ✅ get_user_collection() test passed")
        return True
    except Exception as e:
        print(f"  ❌ get_user_collection() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        database.DB_FILE = original_db_file
        cleanup_test_db()


def test_add_collection_item():
    """Test adding item to user collection."""
    print("Testing add_collection_item()...")
    
    original_db_file = database.DB_FILE
    database.DB_FILE = get_test_db_path()
    
    try:
        cleanup_test_db()
        database.init_db()
        
        # Create user
        user_id = database.create_user("testuser", "hash123")
        
        # Add collection item
        item = {
            "name": "Lightning Bolt",
            "sets": ["Alpha", "Beta"],
            "buy_price": 10.50,
            "condition": "Near Mint",
            "foil": False
        }
        
        item_id = database.add_collection_item(user_id, item)
        assert item_id is not None, "Item ID should be returned"
        
        # Verify item was added
        collection = database.get_user_collection(user_id)
        assert len(collection) == 1, "Collection should have 1 item"
        assert collection[0]["name"] == "Lightning Bolt", "Item name should match"
        assert collection[0]["buy_price"] == 10.50, "Buy price should match"
        assert collection[0]["sets"] == ["Alpha", "Beta"], "Sets should match"
        
        print("  ✅ add_collection_item() test passed")
        return True
    except Exception as e:
        print(f"  ❌ add_collection_item() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        database.DB_FILE = original_db_file
        cleanup_test_db()


def test_update_collection_item():
    """Test updating collection item."""
    print("Testing update_collection_item()...")
    
    original_db_file = database.DB_FILE
    database.DB_FILE = get_test_db_path()
    
    try:
        cleanup_test_db()
        database.init_db()
        
        # Create user and add item
        user_id = database.create_user("testuser", "hash123")
        item = {"name": "Lightning Bolt", "sets": ["Alpha"], "buy_price": 10.50}
        item_id = database.add_collection_item(user_id, item)
        
        # Update item
        updates = {"buy_price": 15.00, "condition": "Mint"}
        result = database.update_collection_item(user_id, item_id, updates)
        assert result is True, "Update should succeed"
        
        # Verify update
        collection = database.get_user_collection(user_id)
        assert collection[0]["buy_price"] == 15.00, "Price should be updated"
        assert collection[0]["condition"] == "Mint", "Condition should be updated"
        
        # Try updating non-existent item
        result2 = database.update_collection_item(user_id, 99999, updates)
        assert result2 is False, "Non-existent item update should fail"
        
        print("  ✅ update_collection_item() test passed")
        return True
    except Exception as e:
        print(f"  ❌ update_collection_item() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        database.DB_FILE = original_db_file
        cleanup_test_db()


def test_delete_collection_item():
    """Test deleting collection item."""
    print("Testing delete_collection_item()...")
    
    original_db_file = database.DB_FILE
    database.DB_FILE = get_test_db_path()
    
    try:
        cleanup_test_db()
        database.init_db()
        
        # Create user and add items
        user_id = database.create_user("testuser", "hash123")
        item1 = {"name": "Lightning Bolt", "sets": ["Alpha"]}
        item2 = {"name": "Counterspell", "sets": ["Beta"]}
        item_id1 = database.add_collection_item(user_id, item1)
        item_id2 = database.add_collection_item(user_id, item2)
        
        # Delete first item
        result = database.delete_collection_item(user_id, item_id1)
        assert result is True, "Delete should succeed"
        
        # Verify deletion
        collection = database.get_user_collection(user_id)
        assert len(collection) == 1, "Collection should have 1 item remaining"
        assert collection[0]["name"] == "Counterspell", "Remaining item should be correct"
        
        # Try deleting non-existent item
        result2 = database.delete_collection_item(user_id, 99999)
        assert result2 is False, "Non-existent item delete should fail"
        
        print("  ✅ delete_collection_item() test passed")
        return True
    except Exception as e:
        print(f"  ❌ delete_collection_item() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        database.DB_FILE = original_db_file
        cleanup_test_db()


def test_save_user_collection():
    """Test saving entire collection (for reordering)."""
    print("Testing save_user_collection()...")
    
    original_db_file = database.DB_FILE
    database.DB_FILE = get_test_db_path()
    
    try:
        cleanup_test_db()
        database.init_db()
        
        # Create user and add items
        user_id = database.create_user("testuser", "hash123")
        item1 = {"name": "Lightning Bolt", "sets": ["Alpha"]}
        item2 = {"name": "Counterspell", "sets": ["Beta"]}
        database.add_collection_item(user_id, item1)
        database.add_collection_item(user_id, item2)
        
        # Get collection and reorder
        collection = database.get_user_collection(user_id)
        assert len(collection) == 2, "Should have 2 items"
        
        # Reverse order
        reordered = [collection[1], collection[0]]
        
        # Save reordered collection
        result = database.save_user_collection(user_id, reordered)
        assert result is True, "Save should succeed"
        
        # Verify reordering
        new_collection = database.get_user_collection(user_id)
        assert len(new_collection) == 2, "Should still have 2 items"
        assert new_collection[0]["name"] == "Counterspell", "First item should be reordered"
        assert new_collection[1]["name"] == "Lightning Bolt", "Second item should be reordered"
        
        print("  ✅ save_user_collection() test passed")
        return True
    except Exception as e:
        print(f"  ❌ save_user_collection() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        database.DB_FILE = original_db_file
        cleanup_test_db()


def test_user_isolation():
    """Test that users can't access each other's collections."""
    print("Testing user_isolation()...")
    
    original_db_file = database.DB_FILE
    database.DB_FILE = get_test_db_path()
    
    try:
        cleanup_test_db()
        database.init_db()
        
        # Create two users
        user_id1 = database.create_user("user1", "hash1")
        user_id2 = database.create_user("user2", "hash2")
        
        # Add items to user1's collection
        item1 = {"name": "User1 Card", "sets": ["Alpha"]}
        database.add_collection_item(user_id1, item1)
        
        # Add items to user2's collection
        item2 = {"name": "User2 Card", "sets": ["Beta"]}
        database.add_collection_item(user_id2, item2)
        
        # Verify isolation
        collection1 = database.get_user_collection(user_id1)
        collection2 = database.get_user_collection(user_id2)
        
        assert len(collection1) == 1, "User1 should have 1 item"
        assert len(collection2) == 1, "User2 should have 1 item"
        assert collection1[0]["name"] == "User1 Card", "User1 should see their own card"
        assert collection2[0]["name"] == "User2 Card", "User2 should see their own card"
        
        # Verify user2 can't access user1's items
        assert collection1[0]["name"] != collection2[0]["name"], "Collections should be different"
        
        print("  ✅ user_isolation() test passed")
        return True
    except Exception as e:
        print(f"  ❌ user_isolation() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        database.DB_FILE = original_db_file
        cleanup_test_db()


def main():
    """Run all database tests."""
    print("\n" + "=" * 60)
    print("DATABASE TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_init_db,
        test_create_user,
        test_get_user_by_username,
        test_get_user_by_id,
        test_get_user_collection,
        test_add_collection_item,
        test_update_collection_item,
        test_delete_collection_item,
        test_save_user_collection,
        test_user_isolation,
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
