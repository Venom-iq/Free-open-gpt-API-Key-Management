#!/usr/bin/env python3
"""Test script to verify login functionality"""

import sqlite3
import hashlib
import os

DB_PATH = "open_gpt_keys.db"

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def test_database():
    """Test database connection and admin user"""
    print(f"[TEST] Database path: {DB_PATH}")
    print(f"[TEST] Database exists: {os.path.exists(DB_PATH)}")
    
    if not os.path.exists(DB_PATH):
        print("[TEST] Creating database...")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check admin_users table
    print("\n[TEST] Checking admin_users table...")
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_users'")
    if c.fetchone():
        print("[TEST] ✓ admin_users table exists")
        
        # Get all admin users
        c.execute("SELECT id, username, password_hash FROM admin_users")
        admins = c.fetchall()
        print(f"[TEST] Found {len(admins)} admin user(s)")
        
        for admin_id, username, password_hash in admins:
            print(f"  - ID: {admin_id}, Username: {username}")
            print(f"    Hash: {password_hash[:20]}...")
    else:
        print("[TEST] ✗ admin_users table does NOT exist")
    
    # Test password verification
    print("\n[TEST] Testing password verification...")
    test_password = "admin-password-2026"
    test_hash = hash_password(test_password)
    print(f"[TEST] Test password: {test_password}")
    print(f"[TEST] Generated hash: {test_hash}")
    
    # Check if hash matches
    c.execute("SELECT password_hash FROM admin_users WHERE username = ?", ("admin",))
    row = c.fetchone()
    if row:
        stored_hash = row[0]
        print(f"[TEST] Stored hash: {stored_hash}")
        print(f"[TEST] Hashes match: {test_hash == stored_hash}")
    else:
        print("[TEST] ✗ No admin user found with username 'admin'")
    
    conn.close()
    print("\n[TEST] Database test complete")

if __name__ == "__main__":
    test_database()
