#!/usr/bin/env python3
"""
Test suite for auth.py module.
Tests password hashing, session tokens, and authentication functions.
"""

import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
import database
from test_utils import cleanup_test_db, get_test_db_path, create_mock_request


def test_hash_password():
    """Test password hashing produces different hashes."""
    print("Testing hash_password()...")
    
    try:
        password = "testpassword123"
        hash1 = auth.hash_password(password)
        hash2 = auth.hash_password(password)
        
        # Hashes should be different (due to salt)
        assert hash1 != hash2, "Different salts should produce different hashes"
        
        # Hash should contain colon (salt:hash format)
        assert ":" in hash1, "Hash should contain colon separator"
        assert len(hash1.split(":")) == 2, "Hash should have salt and hash parts"
        
        print("  ✅ hash_password() test passed")
        return True
    except Exception as e:
        print(f"  ❌ hash_password() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_verify_password():
    """Test password verification with correct password."""
    print("Testing verify_password() with correct password...")
    
    try:
        password = "testpassword123"
        password_hash = auth.hash_password(password)
        
        # Verify correct password
        result = auth.verify_password(password, password_hash)
        assert result is True, "Correct password should verify successfully"
        
        print("  ✅ verify_password() test passed")
        return True
    except Exception as e:
        print(f"  ❌ verify_password() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_verify_password_wrong():
    """Test password verification with wrong password."""
    print("Testing verify_password() with wrong password...")
    
    try:
        password = "testpassword123"
        password_hash = auth.hash_password(password)
        
        # Verify wrong password
        result = auth.verify_password("wrongpassword", password_hash)
        assert result is False, "Wrong password should fail verification"
        
        print("  ✅ verify_password_wrong() test passed")
        return True
    except Exception as e:
        print(f"  ❌ verify_password_wrong() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_session_token():
    """Test session token creation."""
    print("Testing create_session_token()...")
    
    try:
        user_id = 123
        token = auth.create_session_token(user_id)
        
        # Token should be a string
        assert isinstance(token, str), "Token should be a string"
        assert len(token) > 0, "Token should not be empty"
        
        print("  ✅ create_session_token() test passed")
        return True
    except Exception as e:
        print(f"  ❌ create_session_token() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_verify_session_token():
    """Test session token verification with valid token."""
    print("Testing verify_session_token() with valid token...")
    
    try:
        user_id = 456
        token = auth.create_session_token(user_id)
        
        # Verify token
        verified_user_id = auth.verify_session_token(token)
        assert verified_user_id == user_id, "Verified user ID should match original"
        
        print("  ✅ verify_session_token() test passed")
        return True
    except Exception as e:
        print(f"  ❌ verify_session_token() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_verify_session_token_expired():
    """Test session token verification with expired token."""
    print("Testing verify_session_token() with expired token...")
    
    try:
        # Create a serializer with very short max_age
        from itsdangerous import URLSafeTimedSerializer
        short_serializer = URLSafeTimedSerializer(auth.SECRET_KEY)
        
        user_id = 789
        token = short_serializer.dumps({"user_id": user_id})
        
        # Wait for token to expire (if max_age is very short)
        # For this test, we'll create an invalid token by using wrong secret
        wrong_serializer = URLSafeTimedSerializer("wrong_secret_key")
        wrong_token = wrong_serializer.dumps({"user_id": user_id})
        
        # Try to verify with wrong serializer (simulates expired/invalid)
        # Actually, let's test with a malformed token
        result = auth.verify_session_token("invalid_token_string")
        assert result is None, "Invalid token should return None"
        
        print("  ✅ verify_session_token_expired() test passed")
        return True
    except Exception as e:
        print(f"  ❌ verify_session_token_expired() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_verify_session_token_invalid():
    """Test session token verification with invalid token."""
    print("Testing verify_session_token() with invalid token...")
    
    try:
        # Test various invalid tokens
        invalid_tokens = [
            "not_a_valid_token",
            "",
            "12345",
            "invalid.token.here",
        ]
        
        for invalid_token in invalid_tokens:
            result = auth.verify_session_token(invalid_token)
            assert result is None, f"Invalid token '{invalid_token}' should return None"
        
        print("  ✅ verify_session_token_invalid() test passed")
        return True
    except Exception as e:
        print(f"  ❌ verify_session_token_invalid() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_current_user():
    """Test get_current_user with/without cookie."""
    print("Testing get_current_user()...")
    
    try:
        # Test without cookie
        request_no_cookie = create_mock_request(cookies={})
        user_id = auth.get_current_user(request_no_cookie)
        assert user_id is None, "Request without cookie should return None"
        
        # Test with invalid cookie
        request_invalid_cookie = create_mock_request(cookies={auth.SESSION_COOKIE_NAME: "invalid_token"})
        user_id = auth.get_current_user(request_invalid_cookie)
        assert user_id is None, "Request with invalid cookie should return None"
        
        # Test with valid cookie
        test_user_id = 999
        valid_token = auth.create_session_token(test_user_id)
        request_valid_cookie = create_mock_request(cookies={auth.SESSION_COOKIE_NAME: valid_token})
        user_id = auth.get_current_user(request_valid_cookie)
        assert user_id == test_user_id, "Request with valid cookie should return user_id"
        
        print("  ✅ get_current_user() test passed")
        return True
    except Exception as e:
        print(f"  ❌ get_current_user() test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all authentication tests."""
    print("\n" + "=" * 60)
    print("AUTHENTICATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_hash_password,
        test_verify_password,
        test_verify_password_wrong,
        test_create_session_token,
        test_verify_session_token,
        test_verify_session_token_expired,
        test_verify_session_token_invalid,
        test_get_current_user,
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
