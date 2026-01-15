#!/usr/bin/env python3
"""
Test suite for collection_ui.py API endpoints.
Tests authentication and collection endpoints using FastAPI TestClient.
"""

import os
import sys
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
import collection_ui
import database
import auth
from test_utils import cleanup_test_db, get_test_db_path


def setup_test_environment():
    """Set up test environment with test database."""
    original_db_file = database.DB_FILE
    database.DB_FILE = get_test_db_path()
    cleanup_test_db()
    database.init_db()
    return original_db_file


def teardown_test_environment(original_db_file):
    """Clean up test environment."""
    database.DB_FILE = original_db_file
    cleanup_test_db()


def test_register_endpoint():
    """Test POST /api/auth/register endpoint."""
    print("Testing register endpoint...")
    
    original_db_file = setup_test_environment()
    client = TestClient(collection_ui.app)
    
    try:
        # Test successful registration
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "password123"
        })
        
        assert response.status_code == 200, f"Registration should succeed, got {response.status_code}"
        data = response.json()
        assert data["success"] is True, "Response should indicate success"
        assert "session_token" in response.cookies, "Session cookie should be set"
        
        # Test duplicate username
        response2 = client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "differentpass"
        })
        
        assert response2.status_code == 400, "Duplicate username should fail"
        
        # Test missing fields
        response3 = client.post("/api/auth/register", json={
            "username": "user2"
        })
        assert response3.status_code == 400, "Missing password should fail"
        
        print("  ✅ register_endpoint() test passed")
        return True
    except Exception as e:
        print(f"  ❌ register_endpoint() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        teardown_test_environment(original_db_file)


def test_login_endpoint():
    """Test POST /api/auth/login endpoint."""
    print("Testing login endpoint...")
    
    original_db_file = setup_test_environment()
    client = TestClient(collection_ui.app)
    
    try:
        # Create user first
        client.post("/api/auth/register", json={
            "username": "loginuser",
            "password": "password123"
        })
        
        # Test successful login
        response = client.post("/api/auth/login", json={
            "username": "loginuser",
            "password": "password123"
        })
        
        assert response.status_code == 200, f"Login should succeed, got {response.status_code}"
        data = response.json()
        assert data["success"] is True, "Response should indicate success"
        assert "session_token" in response.cookies, "Session cookie should be set"
        
        # Test wrong password
        response2 = client.post("/api/auth/login", json={
            "username": "loginuser",
            "password": "wrongpassword"
        })
        
        assert response2.status_code == 401, "Wrong password should fail"
        
        # Test non-existent user
        response3 = client.post("/api/auth/login", json={
            "username": "nonexistent",
            "password": "password123"
        })
        
        assert response3.status_code == 401, "Non-existent user should fail"
        
        print("  ✅ login_endpoint() test passed")
        return True
    except Exception as e:
        print(f"  ❌ login_endpoint() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        teardown_test_environment(original_db_file)


def test_logout_endpoint():
    """Test POST /api/auth/logout endpoint."""
    print("Testing logout endpoint...")
    
    original_db_file = setup_test_environment()
    client = TestClient(collection_ui.app)
    
    try:
        # Login first
        login_response = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "testpass"
        })
        
        # If user doesn't exist, create it
        if login_response.status_code != 200:
            client.post("/api/auth/register", json={
                "username": "testuser",
                "password": "testpass"
            })
            login_response = client.post("/api/auth/login", json={
                "username": "testuser",
                "password": "testpass"
            })
        
        # Test logout
        response = client.post("/api/auth/logout", cookies=login_response.cookies)
        assert response.status_code == 200, "Logout should succeed"
        data = response.json()
        assert data["success"] is True, "Response should indicate success"
        
        print("  ✅ logout_endpoint() test passed")
        return True
    except Exception as e:
        print(f"  ❌ logout_endpoint() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        teardown_test_environment(original_db_file)


def test_me_endpoint():
    """Test GET /api/auth/me endpoint."""
    print("Testing me endpoint...")
    
    original_db_file = setup_test_environment()
    client = TestClient(collection_ui.app)
    
    try:
        # Test without authentication
        response = client.get("/api/auth/me")
        assert response.status_code == 200, "Should return 200 even when not authenticated"
        data = response.json()
        assert data["authenticated"] is False, "Should indicate not authenticated"
        
        # Test with authentication
        # Register and login
        client.post("/api/auth/register", json={
            "username": "meuser",
            "password": "password123"
        })
        login_response = client.post("/api/auth/login", json={
            "username": "meuser",
            "password": "password123"
        })
        
        # Get user info
        response = client.get("/api/auth/me", cookies=login_response.cookies)
        assert response.status_code == 200, "Should succeed when authenticated"
        data = response.json()
        assert data["authenticated"] is True, "Should indicate authenticated"
        assert data["username"] == "meuser", "Username should match"
        
        print("  ✅ me_endpoint() test passed")
        return True
    except Exception as e:
        print(f"  ❌ me_endpoint() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        teardown_test_environment(original_db_file)


def test_get_collection_anonymous():
    """Test GET /api/collection without authentication (uses JSON)."""
    print("Testing get_collection() anonymous...")
    
    original_db_file = setup_test_environment()
    client = TestClient(collection_ui.app)
    
    try:
        # Test without authentication (should use JSON fallback)
        response = client.get("/api/collection")
        assert response.status_code == 200, "Should succeed even without auth"
        data = response.json()
        assert "collection" in data, "Response should contain collection"
        assert isinstance(data["collection"], list), "Collection should be a list"
        
        print("  ✅ get_collection_anonymous() test passed")
        return True
    except Exception as e:
        print(f"  ❌ get_collection_anonymous() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        teardown_test_environment(original_db_file)


def test_get_collection_authenticated():
    """Test GET /api/collection with authentication (uses DB)."""
    print("Testing get_collection() authenticated...")
    
    original_db_file = setup_test_environment()
    client = TestClient(collection_ui.app)
    
    try:
        # Register, login, and add item
        client.post("/api/auth/register", json={
            "username": "collectionuser",
            "password": "password123"
        })
        login_response = client.post("/api/auth/login", json={
            "username": "collectionuser",
            "password": "password123"
        })
        
        # Add item to collection
        client.post("/api/collection", json={
            "name": "Test Card",
            "sets": ["Alpha"]
        }, cookies=login_response.cookies)
        
        # Get collection
        response = client.get("/api/collection", cookies=login_response.cookies)
        assert response.status_code == 200, "Should succeed"
        data = response.json()
        assert "collection" in data, "Response should contain collection"
        assert len(data["collection"]) == 1, "Should have 1 item"
        assert data["collection"][0]["name"] == "Test Card", "Item name should match"
        
        print("  ✅ get_collection_authenticated() test passed")
        return True
    except Exception as e:
        print(f"  ❌ get_collection_authenticated() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        teardown_test_environment(original_db_file)


def test_add_collection_item_anonymous():
    """Test POST /api/collection without authentication."""
    print("Testing add_collection_item() anonymous...")
    
    original_db_file = setup_test_environment()
    client = TestClient(collection_ui.app)
    
    try:
        # Add item without authentication (should save to JSON)
        response = client.post("/api/collection", json={
            "name": "Anonymous Card",
            "sets": ["Beta"]
        })
        
        assert response.status_code == 200, "Should succeed (saves to JSON)"
        data = response.json()
        assert data["success"] is True, "Should indicate success"
        
        print("  ✅ add_collection_item_anonymous() test passed")
        return True
    except Exception as e:
        print(f"  ❌ add_collection_item_anonymous() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        teardown_test_environment(original_db_file)


def test_add_collection_item_authenticated():
    """Test POST /api/collection with authentication."""
    print("Testing add_collection_item() authenticated...")
    
    original_db_file = setup_test_environment()
    client = TestClient(collection_ui.app)
    
    try:
        # Register and login
        client.post("/api/auth/register", json={
            "username": "adduser",
            "password": "password123"
        })
        login_response = client.post("/api/auth/login", json={
            "username": "adduser",
            "password": "password123"
        })
        
        # Add item with authentication
        response = client.post("/api/collection", json={
            "name": "Authenticated Card",
            "sets": ["Gamma"],
            "buy_price": 5.50
        }, cookies=login_response.cookies)
        
        assert response.status_code == 200, "Should succeed"
        data = response.json()
        assert data["success"] is True, "Should indicate success"
        
        # Verify item was added to database
        get_response = client.get("/api/collection", cookies=login_response.cookies)
        collection = get_response.json()["collection"]
        assert len(collection) == 1, "Should have 1 item"
        assert collection[0]["name"] == "Authenticated Card", "Item name should match"
        
        print("  ✅ add_collection_item_authenticated() test passed")
        return True
    except Exception as e:
        print(f"  ❌ add_collection_item_authenticated() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        teardown_test_environment(original_db_file)


def test_update_collection_item():
    """Test PUT /api/collection/{index} endpoint."""
    print("Testing update_collection_item()...")
    
    original_db_file = setup_test_environment()
    client = TestClient(collection_ui.app)
    
    try:
        # Register, login, and add item
        client.post("/api/auth/register", json={
            "username": "updateuser",
            "password": "password123"
        })
        login_response = client.post("/api/auth/login", json={
            "username": "updateuser",
            "password": "password123"
        })
        
        client.post("/api/collection", json={
            "name": "Original Card",
            "sets": ["Alpha"]
        }, cookies=login_response.cookies)
        
        # Update item
        response = client.put("/api/collection/0", json={
            "name": "Updated Card",
            "buy_price": 10.00
        }, cookies=login_response.cookies)
        
        assert response.status_code == 200, "Should succeed"
        data = response.json()
        assert data["success"] is True, "Should indicate success"
        
        # Verify update
        get_response = client.get("/api/collection", cookies=login_response.cookies)
        collection = get_response.json()["collection"]
        assert collection[0]["name"] == "Updated Card", "Name should be updated"
        
        print("  ✅ update_collection_item() test passed")
        return True
    except Exception as e:
        print(f"  ❌ update_collection_item() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        teardown_test_environment(original_db_file)


def test_delete_collection_item():
    """Test DELETE /api/collection/{index} endpoint."""
    print("Testing delete_collection_item()...")
    
    original_db_file = setup_test_environment()
    client = TestClient(collection_ui.app)
    
    try:
        # Register, login, and add items
        client.post("/api/auth/register", json={
            "username": "deleteuser",
            "password": "password123"
        })
        login_response = client.post("/api/auth/login", json={
            "username": "deleteuser",
            "password": "password123"
        })
        
        client.post("/api/collection", json={
            "name": "Card 1",
            "sets": ["Alpha"]
        }, cookies=login_response.cookies)
        
        client.post("/api/collection", json={
            "name": "Card 2",
            "sets": ["Beta"]
        }, cookies=login_response.cookies)
        
        # Delete first item
        response = client.delete("/api/collection/0", cookies=login_response.cookies)
        assert response.status_code == 200, "Should succeed"
        
        # Verify deletion
        get_response = client.get("/api/collection", cookies=login_response.cookies)
        collection = get_response.json()["collection"]
        assert len(collection) == 1, "Should have 1 item remaining"
        assert collection[0]["name"] == "Card 2", "Remaining item should be correct"
        
        print("  ✅ delete_collection_item() test passed")
        return True
    except Exception as e:
        print(f"  ❌ delete_collection_item() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        teardown_test_environment(original_db_file)


def test_reorder_collection():
    """Test POST /api/collection/reorder endpoint."""
    print("Testing reorder_collection()...")
    
    original_db_file = setup_test_environment()
    client = TestClient(collection_ui.app)
    
    try:
        # Register, login, and add items
        client.post("/api/auth/register", json={
            "username": "reorderuser",
            "password": "password123"
        })
        login_response = client.post("/api/auth/login", json={
            "username": "reorderuser",
            "password": "password123"
        })
        
        client.post("/api/collection", json={"name": "First", "sets": ["Alpha"]}, cookies=login_response.cookies)
        client.post("/api/collection", json={"name": "Second", "sets": ["Beta"]}, cookies=login_response.cookies)
        
        # Reorder (reverse order)
        response = client.post("/api/collection/reorder", json={
            "order": [1, 0]
        }, cookies=login_response.cookies)
        
        assert response.status_code == 200, "Should succeed"
        data = response.json()
        assert data["success"] is True, "Should indicate success"
        
        # Verify reordering
        get_response = client.get("/api/collection", cookies=login_response.cookies)
        collection = get_response.json()["collection"]
        assert collection[0]["name"] == "Second", "First item should be reordered"
        assert collection[1]["name"] == "First", "Second item should be reordered"
        
        print("  ✅ reorder_collection() test passed")
        return True
    except Exception as e:
        print(f"  ❌ reorder_collection() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        teardown_test_environment(original_db_file)


def test_user_isolation_api():
    """Test that users can't access each other's data via API."""
    print("Testing user_isolation_api()...")
    
    original_db_file = setup_test_environment()
    client = TestClient(collection_ui.app)
    
    try:
        # Create two users
        client.post("/api/auth/register", json={
            "username": "userA",
            "password": "password123"
        })
        client.post("/api/auth/register", json={
            "username": "userB",
            "password": "password123"
        })
        
        loginA = client.post("/api/auth/login", json={
            "username": "userA",
            "password": "password123"
        })
        loginB = client.post("/api/auth/login", json={
            "username": "userB",
            "password": "password123"
        })
        
        # User A adds item
        client.post("/api/collection", json={
            "name": "UserA Card",
            "sets": ["Alpha"]
        }, cookies=loginA.cookies)
        
        # User B adds different item
        client.post("/api/collection", json={
            "name": "UserB Card",
            "sets": ["Beta"]
        }, cookies=loginB.cookies)
        
        # Verify isolation
        responseA = client.get("/api/collection", cookies=loginA.cookies)
        responseB = client.get("/api/collection", cookies=loginB.cookies)
        
        collectionA = responseA.json()["collection"]
        collectionB = responseB.json()["collection"]
        
        assert len(collectionA) == 1, "User A should have 1 item"
        assert len(collectionB) == 1, "User B should have 1 item"
        assert collectionA[0]["name"] == "UserA Card", "User A should see their own card"
        assert collectionB[0]["name"] == "UserB Card", "User B should see their own card"
        
        print("  ✅ user_isolation_api() test passed")
        return True
    except Exception as e:
        print(f"  ❌ user_isolation_api() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        teardown_test_environment(original_db_file)


def main():
    """Run all API endpoint tests."""
    print("\n" + "=" * 60)
    print("API ENDPOINTS TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_register_endpoint,
        test_login_endpoint,
        test_logout_endpoint,
        test_me_endpoint,
        test_get_collection_anonymous,
        test_get_collection_authenticated,
        test_add_collection_item_anonymous,
        test_add_collection_item_authenticated,
        test_update_collection_item,
        test_delete_collection_item,
        test_reorder_collection,
        test_user_isolation_api,
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
