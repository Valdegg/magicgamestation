#!/usr/bin/env python3
"""
Main test runner for all database and authentication tests.
Runs all test suites and prints a summary.
"""

import os
import sys
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_test_file(test_file):
    """Run a test file and return (success, output)."""
    test_path = os.path.join(os.path.dirname(__file__), test_file)
    
    if not os.path.exists(test_path):
        return False, f"Test file not found: {test_file}"
    
    try:
        # Run the test file
        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        return success, output
    except subprocess.TimeoutExpired:
        return False, f"Test timed out: {test_file}"
    except Exception as e:
        return False, f"Error running test: {e}"


def main():
    """Run all test suites."""
    print("=" * 60)
    print("DATABASE AND AUTHENTICATION TEST SUITE")
    print("=" * 60)
    print()
    
    # List of test files to run (in order)
    test_files = [
        "test_dependencies.py",      # Run first to verify dependencies
        "test_database.py",           # Database CRUD operations
        "test_auth.py",               # Authentication functions
        "test_collection_functions.py",  # Collection load/save
        "test_api_endpoints.py",     # API endpoint integration tests
    ]
    
    results = {}
    
    for test_file in test_files:
        print(f"\n{'=' * 60}")
        print(f"Running {test_file}...")
        print('=' * 60)
        
        success, output = run_test_file(test_file)
        results[test_file] = success
        
        # Print output
        if output:
            print(output)
        
        if success:
            print(f"\n✅ {test_file} PASSED")
        else:
            print(f"\n❌ {test_file} FAILED")
    
    # Summary
    print("\n" + "=" * 60)
    print("OVERALL TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_file, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_file}: {status}")
    
    print(f"\nTotal: {passed}/{total} test suites passed")
    
    # Note about frontend tests
    print("\n" + "=" * 60)
    print("FRONTEND TESTS")
    print("=" * 60)
    print("Frontend JavaScript tests (test_frontend_auth.js) must be run manually")
    print("in the browser console. See test_frontend_auth.js for instructions.")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
