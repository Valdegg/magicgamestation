#!/usr/bin/env python3
"""
Quick script to run database migrations.
Use this to update existing databases with new schema changes.
"""

import database

if __name__ == "__main__":
    print("🔄 Running database migrations...")
    print("=" * 60)
    try:
        database.init_db()
        print("\n✅ Database migration completed successfully!")
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
