import sqlite3
import os

db_path = 'db.sqlite3'
if not os.path.exists(db_path):
    print(f"Database file {db_path} not found.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in database:")
    for table in tables:
        print(f" - {table[0]}")
    
    # Check if lands_utility exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lands_utility';")
    if cursor.fetchone():
        print("\nTable 'lands_utility' exists. Schema:")
        cursor.execute("PRAGMA table_info(lands_utility);")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
    else:
        print("\nTable 'lands_utility' DOES NOT exist yet. You need to run migrations.")
    
    conn.close()
