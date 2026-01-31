#!/usr/bin/env python3
"""
Database module for SQLite storage of users and collections.
"""

import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_FILE = "collections.db"


def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def init_db():
    """Initialize the database with schema."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create collection table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                sets TEXT,
                buy_price REAL,
                sell_price REAL,
                market_price REAL,
                condition TEXT,
                source TEXT,
                notes TEXT,
                language TEXT,
                foil BOOLEAN DEFAULT 0,
                purchase_date TEXT,
                sale_date TEXT,
                format_validity TEXT,
                old_school_legal BOOLEAN,
                premodern_legal BOOLEAN,
                old_school_sets TEXT,
                premodern_sets TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Check if market_price column exists, add if not (migration for existing databases)
        cursor.execute("PRAGMA table_info(collection)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'market_price' not in columns:
            cursor.execute("ALTER TABLE collection ADD COLUMN market_price REAL")
            print(f"✅ Added market_price column to existing collection table", flush=True)
        
        # Create index on user_id for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_collection_user_id ON collection(user_id)
        """)
        
        # Create wishlist table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wishlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                sets TEXT,
                notes TEXT,
                archived BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Create index on user_id for wishlist
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_wishlist_user_id ON wishlist(user_id)
        """)
        
        # Create index on archived for faster filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_wishlist_archived ON wishlist(user_id, archived)
        """)
        
        # Create market_scan_deal table for storing market scan results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_scan_deal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                -- Card info
                card_name TEXT NOT NULL,
                expansion TEXT,
                card_id INTEGER,
                old_school_legal BOOLEAN DEFAULT 0,
                premodern_legal BOOLEAN DEFAULT 0,
                -- Historical prices
                trend_price REAL,
                avg30_price REAL,
                avg7_price REAL,
                -- Live data
                url TEXT,
                total_listings INTEGER,
                available_items_total INTEGER,
                expansion_name TEXT,
                cheapest_good_price REAL,
                cheapest_condition TEXT,
                cheapest_seller TEXT,
                cheapest_quantity INTEGER,
                cheapest_country TEXT,
                cheapest_price REAL,
                top_sellers TEXT,
                -- Discounts (vs current market listings)
                has_discount BOOLEAN,
                discount_vs_market REAL,
                market_baseline REAL,
                baseline_count INTEGER,
                category TEXT,
                -- Metadata
                scan_date DATE NOT NULL DEFAULT (DATE('now')),
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(card_name, expansion, scan_date)
            )
        """)
        
        # Create indexes for market_scan_deal
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_scan_card ON market_scan_deal(card_name, expansion)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_scan_category ON market_scan_deal(category)
        """)
        
        # Add scan_date column if it doesn't exist (migration for existing databases)
        # MUST be done before creating indexes that reference scan_date
        cursor.execute("PRAGMA table_info(market_scan_deal)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'scan_date' not in columns:
            cursor.execute("ALTER TABLE market_scan_deal ADD COLUMN scan_date DATE DEFAULT (DATE('now'))")
            cursor.execute("UPDATE market_scan_deal SET scan_date = DATE(scanned_at) WHERE scan_date IS NULL")
            print(f"✅ Added scan_date column to existing market_scan_deal table", flush=True)
        
        # Create indexes that reference scan_date (only after column exists)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_scan_date ON market_scan_deal(scan_date)
        """)
        
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_market_scan_unique ON market_scan_deal(card_name, expansion, scan_date)
        """)
        
        conn.commit()
        print(f"✅ Database initialized: {DB_FILE}", flush=True)
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize database: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise
    finally:
        if conn:
            conn.close()


# User CRUD operations

def create_user(username: str, password_hash: str) -> Optional[int]:
    """Create a new user. Returns user_id on success, None on failure."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError as e:
        # Username already exists
        print(f"Username '{username}' already exists", flush=True)
        return None
    except sqlite3.OperationalError as e:
        # Database/table doesn't exist or other operational error
        error_msg = str(e).lower()
        if "no such table" in error_msg:
            print(f"ERROR: Users table does not exist! Database needs initialization.", flush=True)
            print(f"       Run: database.init_db()", flush=True)
        else:
            print(f"Database operational error creating user: {e}", flush=True)
        raise  # Re-raise so registration endpoint can handle it properly
    except Exception as e:
        print(f"Error creating user: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise  # Re-raise so registration endpoint can handle it properly
    finally:
        if conn:
            conn.close()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username. Returns dict with id, username, password_hash, or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return {"id": row["id"], "username": row["username"], "password_hash": row["password_hash"]}
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by id. Returns dict with id, username, or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return {"id": row["id"], "username": row["username"]}
        return None
    except Exception as e:
        print(f"Error getting user by id: {e}")
        return None
    finally:
        if conn:
            conn.close()


# Collection CRUD operations

def get_user_collection(user_id: int) -> List[Dict[str, Any]]:
    """Get all collection items for a user."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM collection WHERE user_id = ? ORDER BY id",
            (user_id,)
        )
        rows = cursor.fetchall()
        
        collection = []
        for row in rows:
            item = {
                "id": row["id"],
                "name": row["name"],
                "sets": json.loads(row["sets"]) if row["sets"] else [],
                "buy_price": row["buy_price"],
                "sell_price": row["sell_price"],
                "market_price": row.get("market_price"),  # Use .get() for backward compatibility
                "condition": row["condition"],
                "source": row["source"],
                "notes": row["notes"],
                "language": row["language"],
                "foil": bool(row["foil"]),
                "purchase_date": row["purchase_date"],
                "sale_date": row["sale_date"],
                "format_validity": row["format_validity"],
                "old_school_legal": bool(row["old_school_legal"]) if row["old_school_legal"] is not None else None,
                "premodern_legal": bool(row["premodern_legal"]) if row["premodern_legal"] is not None else None,
                "old_school_sets": json.loads(row["old_school_sets"]) if row["old_school_sets"] else [],
                "premodern_sets": json.loads(row["premodern_sets"]) if row["premodern_sets"] else [],
            }
            # Remove None values to match JSON structure
            item = {k: v for k, v in item.items() if v is not None and v != ""}
            collection.append(item)
        
        return collection
    except Exception as e:
        print(f"Error getting user collection: {e}")
        return []
    finally:
        if conn:
            conn.close()


def add_collection_item(user_id: int, item: Dict[str, Any]) -> Optional[int]:
    """Add a collection item for a user. Returns item_id on success, None on failure."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO collection (
                user_id, name, sets, buy_price, sell_price, market_price, condition, source,
                notes, language, foil, purchase_date, sale_date, format_validity,
                old_school_legal, premodern_legal, old_school_sets, premodern_sets
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            item.get("name"),
            json.dumps(item.get("sets", [])),
            item.get("buy_price"),
            item.get("sell_price"),
            item.get("market_price"),
            item.get("condition"),
            item.get("source"),
            item.get("notes"),
            item.get("language"),
            1 if item.get("foil") else 0,
            item.get("purchase_date"),
            item.get("sale_date"),
            item.get("format_validity"),
            1 if item.get("old_school_legal") else 0 if item.get("old_school_legal") is not None else None,
            1 if item.get("premodern_legal") else 0 if item.get("premodern_legal") is not None else None,
            json.dumps(item.get("old_school_sets", [])),
            json.dumps(item.get("premodern_sets", [])),
        ))
        
        item_id = cursor.lastrowid
        conn.commit()
        return item_id
    except Exception as e:
        print(f"Error adding collection item: {e}")
        return None
    finally:
        if conn:
            conn.close()


def update_collection_item(user_id: int, item_id: int, item: Dict[str, Any]) -> bool:
    """Update a collection item. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify item belongs to user
        cursor.execute("SELECT id FROM collection WHERE id = ? AND user_id = ?", (item_id, user_id))
        if not cursor.fetchone():
            return False
        
        # Build update query dynamically based on provided fields
        updates = []
        values = []
        
        if "name" in item:
            updates.append("name = ?")
            values.append(item["name"])
        if "sets" in item:
            updates.append("sets = ?")
            values.append(json.dumps(item["sets"]))
        if "buy_price" in item:
            updates.append("buy_price = ?")
            values.append(item["buy_price"])
        if "sell_price" in item:
            updates.append("sell_price = ?")
            values.append(item["sell_price"])
        if "market_price" in item:
            updates.append("market_price = ?")
            values.append(item["market_price"])
        if "condition" in item:
            updates.append("condition = ?")
            values.append(item["condition"])
        if "source" in item:
            updates.append("source = ?")
            values.append(item["source"])
        if "notes" in item:
            updates.append("notes = ?")
            values.append(item["notes"])
        if "language" in item:
            updates.append("language = ?")
            values.append(item["language"])
        if "foil" in item:
            updates.append("foil = ?")
            values.append(1 if item["foil"] else 0)
        if "purchase_date" in item:
            updates.append("purchase_date = ?")
            values.append(item["purchase_date"])
        if "sale_date" in item:
            updates.append("sale_date = ?")
            values.append(item["sale_date"])
        if "format_validity" in item:
            updates.append("format_validity = ?")
            values.append(item["format_validity"])
        if "old_school_legal" in item:
            updates.append("old_school_legal = ?")
            values.append(1 if item["old_school_legal"] else 0 if item["old_school_legal"] is not None else None)
        if "premodern_legal" in item:
            updates.append("premodern_legal = ?")
            values.append(1 if item["premodern_legal"] else 0 if item["premodern_legal"] is not None else None)
        if "old_school_sets" in item:
            updates.append("old_school_sets = ?")
            values.append(json.dumps(item["old_school_sets"]))
        if "premodern_sets" in item:
            updates.append("premodern_sets = ?")
            values.append(json.dumps(item["premodern_sets"]))
        
        if not updates:
            return True  # Nothing to update
        
        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(item_id)
        values.append(user_id)
        
        query = f"UPDATE collection SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
        cursor.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating collection item: {e}")
        return False
    finally:
        if conn:
            conn.close()


def delete_collection_item(user_id: int, item_id: int) -> bool:
    """Delete a collection item. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM collection WHERE id = ? AND user_id = ?", (item_id, user_id))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    except Exception as e:
        print(f"Error deleting collection item: {e}")
        return False
    finally:
        if conn:
            conn.close()


def reorder_collection(user_id: int, item_ids: List[int]) -> bool:
    """Reorder collection items. Note: SQLite doesn't have a natural order, so we'll use a position column or recreate items."""
    # For simplicity, we'll just verify all items belong to the user
    # The actual reordering will be handled by the application layer
    # by deleting and recreating items in the new order if needed.
    # For now, we'll just return True since SQLite doesn't preserve insertion order
    # and we're using ORDER BY id which maintains creation order.
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Verify all items belong to user
        placeholders = ','.join('?' * len(item_ids))
        cursor.execute(
            f"SELECT COUNT(*) FROM collection WHERE id IN ({placeholders}) AND user_id = ?",
            item_ids + [user_id]
        )
        count = cursor.fetchone()[0]
        return count == len(item_ids)
    except Exception as e:
        print(f"Error reordering collection: {e}")
        return False
    finally:
        if conn:
            conn.close()


def save_user_collection(user_id: int, collection: List[Dict[str, Any]]) -> bool:
    """Save entire collection (replaces existing). Used for reordering."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete existing collection
        cursor.execute("DELETE FROM collection WHERE user_id = ?", (user_id,))
        
        # Insert all items
        for item in collection:
            cursor.execute("""
                INSERT INTO collection (
                    user_id, name, sets, buy_price, sell_price, condition, source,
                    notes, language, foil, purchase_date, sale_date, format_validity,
                    old_school_legal, premodern_legal, old_school_sets, premodern_sets
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                item.get("name"),
                json.dumps(item.get("sets", [])),
                item.get("buy_price"),
                item.get("sell_price"),
                item.get("condition"),
                item.get("source"),
                item.get("notes"),
                item.get("language"),
                1 if item.get("foil") else 0,
                item.get("purchase_date"),
                item.get("sale_date"),
                item.get("format_validity"),
                1 if item.get("old_school_legal") else 0 if item.get("old_school_legal") is not None else None,
                1 if item.get("premodern_legal") else 0 if item.get("premodern_legal") is not None else None,
                json.dumps(item.get("old_school_sets", [])),
                json.dumps(item.get("premodern_sets", [])),
            ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving user collection: {e}")
        return False
    finally:
        if conn:
            conn.close()


# Wishlist CRUD operations

def get_user_wishlist(user_id: int, include_archived: bool = False) -> List[Dict[str, Any]]:
    """Get wishlist items for a user. By default excludes archived items."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if include_archived:
            cursor.execute(
                "SELECT * FROM wishlist WHERE user_id = ? ORDER BY id",
                (user_id,)
            )
        else:
            cursor.execute(
                "SELECT * FROM wishlist WHERE user_id = ? AND archived = 0 ORDER BY id",
                (user_id,)
            )
        
        rows = cursor.fetchall()
        
        wishlist = []
        for row in rows:
            item = {
                "id": row["id"],
                "name": row["name"],
                "sets": json.loads(row["sets"]) if row["sets"] else [],
                "notes": row["notes"],
                "archived": bool(row["archived"]),
            }
            # Remove None values to match JSON structure
            item = {k: v for k, v in item.items() if v is not None and v != ""}
            wishlist.append(item)
        
        return wishlist
    except Exception as e:
        print(f"Error getting user wishlist: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_archived_wishlist(user_id: int) -> List[Dict[str, Any]]:
    """Get only archived wishlist items for a user."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM wishlist WHERE user_id = ? AND archived = 1 ORDER BY id",
            (user_id,)
        )
        
        rows = cursor.fetchall()
        
        wishlist = []
        for row in rows:
            item = {
                "id": row["id"],
                "name": row["name"],
                "sets": json.loads(row["sets"]) if row["sets"] else [],
                "notes": row["notes"],
                "archived": bool(row["archived"]),
            }
            # Remove None values to match JSON structure
            item = {k: v for k, v in item.items() if v is not None and v != ""}
            wishlist.append(item)
        
        return wishlist
    except Exception as e:
        print(f"Error getting archived wishlist: {e}")
        return []
    finally:
        if conn:
            conn.close()


def add_wishlist_item(user_id: int, item: Dict[str, Any]) -> Optional[int]:
    """Add a wishlist item for a user. Returns item_id on success, None on failure."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO wishlist (user_id, name, sets, notes, archived)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            item.get("name"),
            json.dumps(item.get("sets", [])),
            item.get("notes"),
            1 if item.get("archived") else 0,
        ))
        
        item_id = cursor.lastrowid
        conn.commit()
        return item_id
    except Exception as e:
        print(f"Error adding wishlist item: {e}")
        return None
    finally:
        if conn:
            conn.close()


def update_wishlist_item(user_id: int, item_id: int, item: Dict[str, Any]) -> bool:
    """Update a wishlist item. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify item belongs to user
        cursor.execute("SELECT id FROM wishlist WHERE id = ? AND user_id = ?", (item_id, user_id))
        if not cursor.fetchone():
            return False
        
        # Build update query dynamically based on provided fields
        updates = []
        values = []
        
        if "name" in item:
            updates.append("name = ?")
            values.append(item["name"])
        if "sets" in item:
            updates.append("sets = ?")
            values.append(json.dumps(item["sets"]))
        if "notes" in item:
            updates.append("notes = ?")
            values.append(item["notes"])
        if "archived" in item:
            updates.append("archived = ?")
            values.append(1 if item["archived"] else 0)
        
        if not updates:
            return True  # Nothing to update
        
        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(item_id)
        values.append(user_id)
        
        query = f"UPDATE wishlist SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
        cursor.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating wishlist item: {e}")
        return False
    finally:
        if conn:
            conn.close()


def delete_wishlist_item(user_id: int, item_id: int) -> bool:
    """Delete a wishlist item. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM wishlist WHERE id = ? AND user_id = ?", (item_id, user_id))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    except Exception as e:
        print(f"Error deleting wishlist item: {e}")
        return False
    finally:
        if conn:
            conn.close()


def archive_wishlist_item(user_id: int, item_id: int) -> bool:
    """Archive a wishlist item (sets archived=1). Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify item belongs to user and update
        cursor.execute(
            "UPDATE wishlist SET archived = 1, updated_at = ? WHERE id = ? AND user_id = ?",
            (datetime.now().isoformat(), item_id, user_id)
        )
        updated = cursor.rowcount > 0
        conn.commit()
        return updated
    except Exception as e:
        print(f"Error archiving wishlist item: {e}")
        return False
    finally:
        if conn:
            conn.close()


def unarchive_wishlist_item(user_id: int, item_id: int) -> bool:
    """Unarchive a wishlist item (sets archived=0). Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify item belongs to user and update
        cursor.execute(
            "UPDATE wishlist SET archived = 0, updated_at = ? WHERE id = ? AND user_id = ?",
            (datetime.now().isoformat(), item_id, user_id)
        )
        updated = cursor.rowcount > 0
        conn.commit()
        return updated
    except Exception as e:
        print(f"Error unarchiving wishlist item: {e}")
        return False
    finally:
        if conn:
            conn.close()


def save_user_wishlist(user_id: int, wishlist: List[Dict[str, Any]]) -> bool:
    """Save entire wishlist (replaces existing non-archived items). Used for reordering."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete existing non-archived wishlist items
        cursor.execute("DELETE FROM wishlist WHERE user_id = ? AND archived = 0", (user_id,))
        
        # Insert all items
        for item in wishlist:
            cursor.execute("""
                INSERT INTO wishlist (user_id, name, sets, notes, archived)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                item.get("name"),
                json.dumps(item.get("sets", [])),
                item.get("notes"),
                1 if item.get("archived") else 0,
            ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving user wishlist: {e}")
        return False
    finally:
        if conn:
            conn.close()


# Market Scan CRUD operations

def save_scan_deals(deals: List[Dict[str, Any]]) -> bool:
    """
    Atomically replace all scan deals (transactional).
    
    Accepts deal dictionaries with nested structure:
    {
        "card": {"name", "expansion", "card_id", "old_school_legal", "premodern_legal", 
                 "historical": {"trend", "avg30", "avg7"}},
        "live_data": {"url", "total_listings", "available_items_total", "expansion_name",
                      "cheapest_good_condition", "cheapest_good_details": {...}, "top_sellers": [...]},
        "discounts": {"has_discount", "discount_vs_market", "market_baseline", "baseline_count"},
        "category": "..."
    }
    
    In a single transaction, DELETE all old deals then INSERT new ones.
    If any insert fails, rollback preserves old data.
    
    Returns True on success, False on failure.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete old deals
        cursor.execute("DELETE FROM market_scan_deal")
        
        # Insert all new deals
        for deal in deals:
            # Extract nested values with safe defaults
            card = deal.get("card", {})
            historical = card.get("historical", {})
            live_data = deal.get("live_data", {})
            cheapest_details = live_data.get("cheapest_good_details", {})
            discounts = deal.get("discounts", {})
            
            # Serialize top_sellers as JSON text
            top_sellers = live_data.get("top_sellers")
            top_sellers_json = json.dumps(top_sellers) if top_sellers else None
            
            # Use today's date for scan_date
            scan_date = datetime.now().strftime('%Y-%m-%d')
            
            cursor.execute("""
                INSERT INTO market_scan_deal (
                    card_name, expansion, card_id, old_school_legal, premodern_legal,
                    trend_price, avg30_price, avg7_price,
                    url, total_listings, available_items_total, expansion_name,
                    cheapest_good_price, cheapest_condition, cheapest_seller,
                    cheapest_quantity, cheapest_country, cheapest_price, top_sellers,
                    has_discount, discount_vs_market, market_baseline, baseline_count,
                    category, scan_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card.get("name"),
                card.get("expansion"),
                card.get("card_id"),
                1 if card.get("old_school_legal") else 0,
                1 if card.get("premodern_legal") else 0,
                historical.get("trend"),
                historical.get("avg30"),
                historical.get("avg7"),
                live_data.get("url"),
                live_data.get("total_listings"),
                live_data.get("available_items_total"),
                live_data.get("expansion_name"),
                live_data.get("cheapest_good_condition"),
                cheapest_details.get("condition"),
                cheapest_details.get("seller"),
                cheapest_details.get("quantity"),
                cheapest_details.get("country"),
                cheapest_details.get("price"),
                top_sellers_json,
                1 if discounts.get("has_discount") else 0,
                discounts.get("discount_vs_market"),
                discounts.get("market_baseline"),
                discounts.get("baseline_count"),
                deal.get("category"),
                scan_date,
            ))
        
        conn.commit()  # Only commits if ALL inserts succeed
        print(f"✅ Saved {len(deals)} scan deals to database", flush=True)
        return True
    except Exception as e:
        if conn:
            conn.rollback()  # Old data preserved on any failure
        print(f"❌ Error saving scan deals: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()


def save_single_scan_deal(deal: Dict[str, Any], scan_date: Optional[str] = None) -> bool:
    """
    Save a single scan deal incrementally to the database.
    
    Uses INSERT OR REPLACE to update if the card+expansion+date already exists.
    This allows incremental saving during scans and resuming interrupted scans.
    
    Args:
        deal: Single deal dictionary with nested structure (same as save_scan_deals)
        scan_date: Date string (YYYY-MM-DD). If None, uses today's date.
    
    Returns:
        True on success, False on failure.
    """
    if scan_date is None:
        scan_date = datetime.now().strftime('%Y-%m-%d')
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Extract nested values with safe defaults
        card = deal.get("card", {})
        historical = card.get("historical", {})
        live_data = deal.get("live_data", {})
        cheapest_details = live_data.get("cheapest_good_details", {})
        discounts = deal.get("discounts", {})
        
        # Serialize top_sellers as JSON text
        top_sellers = live_data.get("top_sellers")
        top_sellers_json = json.dumps(top_sellers) if top_sellers else None
        
        # Use INSERT OR REPLACE to update if card+expansion+date already exists
        cursor.execute("""
            INSERT OR REPLACE INTO market_scan_deal (
                card_name, expansion, card_id, old_school_legal, premodern_legal,
                trend_price, avg30_price, avg7_price,
                url, total_listings, available_items_total, expansion_name,
                cheapest_good_price, cheapest_condition, cheapest_seller,
                cheapest_quantity, cheapest_country, cheapest_price, top_sellers,
                has_discount, discount_vs_market, market_baseline, baseline_count,
                category, scan_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            card.get("name"),
            card.get("expansion"),
            card.get("card_id"),
            1 if card.get("old_school_legal") else 0,
            1 if card.get("premodern_legal") else 0,
            historical.get("trend"),
            historical.get("avg30"),
            historical.get("avg7"),
            live_data.get("url"),
            live_data.get("total_listings"),
            live_data.get("available_items_total"),
            live_data.get("expansion_name"),
            live_data.get("cheapest_good_condition"),
            cheapest_details.get("condition"),
            cheapest_details.get("seller"),
            cheapest_details.get("quantity"),
            cheapest_details.get("country"),
            cheapest_details.get("price"),
            top_sellers_json,
            1 if discounts.get("has_discount") else 0,
            discounts.get("discount_vs_market"),
            discounts.get("market_baseline"),
            discounts.get("baseline_count"),
            deal.get("category"),
            scan_date,
        ))
        
        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error saving single scan deal: {e}", flush=True)
        return False
    finally:
        if conn:
            conn.close()


def get_cards_with_scan_date(scan_date: Optional[str] = None) -> set:
    """
    Get set of (card_name, expansion) tuples that already have scan data for the given date.
    
    Args:
        scan_date: Date string (YYYY-MM-DD). If None, uses today's date.
    
    Returns:
        Set of tuples: {(card_name, expansion), ...}
    """
    if scan_date is None:
        scan_date = datetime.now().strftime('%Y-%m-%d')
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT card_name, expansion
            FROM market_scan_deal
            WHERE scan_date = ?
        """, (scan_date,))
        
        rows = cursor.fetchall()
        # Return set of tuples for fast lookup
        return {(row[0], row[1]) for row in rows}
    except Exception as e:
        print(f"❌ Error getting cards with scan date: {e}", flush=True)
        return set()
    finally:
        if conn:
            conn.close()


def get_scan_deals(card_names: Optional[List[str]] = None, scan_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get scan deals, optionally filtered by card names and/or scan date.
    
    Args:
        card_names: Optional list of card names to filter by. If None, returns all deals.
        scan_date: Optional date string (YYYY-MM-DD) to filter by. If None, returns all dates.
                   Use this to get only today's scans, or scans from a specific date.
    
    Returns:
        List of deal dictionaries in the same nested structure as save_scan_deals expects.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if card_names:
            # Filter by card names (case-insensitive)
            placeholders = ','.join('?' * len(card_names))
            lower_names = [name.lower() for name in card_names]
            conditions.append(f"LOWER(card_name) IN ({placeholders})")
            params.extend(lower_names)
        
        if scan_date:
            conditions.append("scan_date = ?")
            params.append(scan_date)
        
        # Deduplicate: keep only the newest scan_date per unique
        # (card_name, expansion, cheapest_condition, cheapest_seller).
        dedup_subquery = """
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY card_name, expansion, cheapest_condition, cheapest_seller
                    ORDER BY scan_date DESC, id DESC
                ) as rn
                FROM market_scan_deal
            ) WHERE rn = 1
        """

        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            where_clause += f" AND id IN ({dedup_subquery})"
            cursor.execute(f"SELECT * FROM market_scan_deal{where_clause} ORDER BY id", params)
        else:
            cursor.execute(f"SELECT * FROM market_scan_deal WHERE id IN ({dedup_subquery}) ORDER BY id")
        
        rows = cursor.fetchall()
        
        deals = []
        for row in rows:
            # Reconstruct nested structure from flat columns
            deal = {
                "id": row["id"],
                "card": {
                    "name": row["card_name"],
                    "expansion": row["expansion"],
                    "card_id": row["card_id"],
                    "old_school_legal": bool(row["old_school_legal"]),
                    "premodern_legal": bool(row["premodern_legal"]),
                    "historical": {
                        "trend": row["trend_price"],
                        "avg30": row["avg30_price"],
                        "avg7": row["avg7_price"],
                    }
                },
                "live_data": {
                    "url": row["url"],
                    "total_listings": row["total_listings"],
                    "available_items_total": row["available_items_total"],
                    "expansion_name": row["expansion_name"],
                    "cheapest_good_condition": row["cheapest_good_price"],
                    "cheapest_good_details": {
                        "condition": row["cheapest_condition"],
                        "seller": row["cheapest_seller"],
                        "quantity": row["cheapest_quantity"],
                        "country": row["cheapest_country"],
                        "price": row["cheapest_price"],
                    },
                    "top_sellers": json.loads(row["top_sellers"]) if row["top_sellers"] else [],
                },
                "discounts": {
                    "has_discount": bool(row["has_discount"]),
                    "discount_vs_market": row["discount_vs_market"],
                    "market_baseline": row["market_baseline"],
                    "baseline_count": row["baseline_count"],
                },
                "category": row["category"],
                "scanned_at": row["scanned_at"],
            }
            
            # Clean up None values in nested structures
            if deal["card"]["historical"]["trend"] is None and deal["card"]["historical"]["avg30"] is None:
                deal["card"]["historical"] = {}
            
            deals.append(deal)
        
        return deals
    except Exception as e:
        print(f"Error getting scan deals: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn:
            conn.close()


def get_scan_metadata() -> Dict[str, Any]:
    """
    Get metadata about the last market scan.
    
    Returns:
        Dict with:
        - last_scan: timestamp of most recent scan (or None if no scans)
        - total_deals: count of deals in database
        - categories: dict of category counts
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total count and most recent scan time
        cursor.execute("""
            SELECT COUNT(*) as total, MAX(scanned_at) as last_scan 
            FROM market_scan_deal
        """)
        row = cursor.fetchone()
        total_deals = row["total"] if row else 0
        last_scan = row["last_scan"] if row else None
        
        # Get category breakdown
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM market_scan_deal 
            GROUP BY category
        """)
        category_rows = cursor.fetchall()
        categories = {row["category"]: row["count"] for row in category_rows if row["category"]}
        
        return {
            "last_scan": last_scan,
            "total_deals": total_deals,
            "categories": categories,
        }
    except Exception as e:
        print(f"Error getting scan metadata: {e}", flush=True)
        return {"last_scan": None, "total_deals": 0, "categories": {}}
    finally:
        if conn:
            conn.close()
