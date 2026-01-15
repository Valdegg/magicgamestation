#!/usr/bin/env python3
"""
Check and fix database initialization.
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database

def check_database():
    """Check database status and initialize if needed."""
    db_file = database.DB_FILE
    
    print(f"\n{'='*60}")
    print("DATABASE STATUS CHECK")
    print(f"{'='*60}\n")
    
    # Check if file exists
    if os.path.exists(db_file):
        stat = os.stat(db_file)
        print(f"Database file exists: {db_file}")
        print(f"  Size: {stat.st_size} bytes")
        print(f"  Permissions: {oct(stat.st_mode)[-3:]}")
        
        # Check if readable/writable
        if os.access(db_file, os.R_OK):
            print("  ✅ Readable")
        else:
            print("  ❌ NOT readable")
        
        if os.access(db_file, os.W_OK):
            print("  ✅ Writable")
        else:
            print("  ❌ NOT writable")
    else:
        print(f"Database file does not exist: {db_file}")
        print("  Will be created on initialization")
    
    print()
    
    # Try to connect and check tables
    try:
        conn = sqlite3.connect(db_file, timeout=5.0)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        users_table = cursor.fetchone()
        
        # Check if collection table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='collection'")
        collection_table = cursor.fetchone()
        
        if users_table and collection_table:
            print("✅ Database tables exist")
            
            # Count users
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"  Users in database: {user_count}")
            
            if user_count > 0:
                cursor.execute("SELECT id, username, created_at FROM users ORDER BY id")
                users = cursor.fetchall()
                print("\n  User list:")
                for user in users:
                    print(f"    ID {user[0]}: {user[1]} (created: {user[2]})")
        else:
            print("❌ Database tables missing!")
            print("  Users table exists:", bool(users_table))
            print("  Collection table exists:", bool(collection_table))
            print("\n  Initializing database...")
            try:
                database.init_db()
                print("  ✅ Database initialized successfully")
            except Exception as e:
                print(f"  ❌ Failed to initialize: {e}")
                import traceback
                traceback.print_exc()
        
        conn.close()
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            print("⚠️  Database is locked (server may be running)")
            print("   Stop the server and try again, or check server logs")
        else:
            print(f"❌ Database error: {e}")
            print("\n  Attempting to initialize database...")
            try:
                database.init_db()
                print("  ✅ Database initialized successfully")
            except Exception as init_error:
                print(f"  ❌ Failed to initialize: {init_error}")
                import traceback
                traceback.print_exc()
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    check_database()
