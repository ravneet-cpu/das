#!/usr/bin/env python3
"""
Migration script to add TOTP support to the database
"""

import sqlite3
import os

DATABASE_PATH = '/app/data/photo_validator.db'
#DATABASE_PATH = '/home/projet/photo-validator/data/photo_validator.db'
def migrate_database():
    """Add TOTP-related columns to users table"""
    
    if not os.path.exists(DATABASE_PATH):
        print("❌ Database not found!")
        return False
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Add TOTP secret column
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN totp_secret TEXT')
            print("✅ Added totp_secret column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️ totp_secret column already exists")
            else:
                raise
        
        # Add TOTP enabled column
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN totp_enabled INTEGER DEFAULT 0')
            print("✅ Added totp_enabled column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️ totp_enabled column already exists")
            else:
                raise
        
        # Add backup codes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_backup_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, code)
            )
        ''')
        print("✅ Created user_backup_codes table")
        
        # Update two_factor_enabled logic to include TOTP
        cursor.execute('''
            UPDATE users 
            SET two_factor_enabled = 1 
            WHERE totp_enabled = 1 AND totp_secret IS NOT NULL
        ''')
        
        conn.commit()
        print("🎉 Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
