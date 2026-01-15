#!/usr/bin/env python3
"""
Simple script to list all users in the database.
"""

import sys
import os
import sqlite3

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database

def list_users():
    """List all users in the database."""
    db_file = database.DB_FILE
    
    if not os.path.exists(db_file):
        print(f"Database file '{db_file}' does not exist.")
        print("The database will be created when the first user registers.")
        return
    
    try:
        # Try to connect with a short timeout
        conn = sqlite3.connect(db_file, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("Users table does not exist. Database may need initialization.")
            conn.close()
            return
        
        # Get all users
        cursor.execute("SELECT id, username, created_at FROM users ORDER BY id")
        users = cursor.fetchall()
        
        if not users:
            print("\nNo users found in database.")
            print("Users will be created when someone registers through the web interface.\n")
            conn.close()
            return
        
        print(f"\n{'='*60}")
        print(f"Users in database ({len(users)} total):")
        print(f"{'='*60}")
        print(f"{'ID':<6} {'Username':<20} {'Created At':<20}")
        print(f"{'-'*60}")
        
        for user in users:
            user_id = user["id"]
            username = user["username"]
            created_at = user["created_at"] or "N/A"
            print(f"{user_id:<6} {username:<20} {created_at:<20}")
        
        print(f"{'='*60}\n")
        
        conn.close()
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower() or "unable to open" in str(e).lower():
            print(f"\n⚠️  Database file is locked (server may be running).")
            print(f"   Try stopping the server first, or query users via the API:")
            print(f"   curl http://localhost:5003/api/auth/me")
            print(f"\n   Or check the database directly:")
            print(f"   sqlite3 {db_file} 'SELECT id, username, created_at FROM users;'\n")
        else:
            print(f"Error accessing database: {e}")
    except Exception as e:
        print(f"Error listing users: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_users()
