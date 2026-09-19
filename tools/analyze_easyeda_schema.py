#!/usr/bin/env python3
"""
Analyze EasyEDA Pro SQLite schema from example project
"""

import sqlite3
import zipfile
from pathlib import Path

example_zip = Path('C:/Program Files/easyeda-pro/resources/app/assets/db/example-projects.zip')

# Extract and examine the SQLite schema
with zipfile.ZipFile(example_zip, 'r') as outer_zip:
    for file_name in outer_zip.namelist():
        if 'Quick Start' in file_name and file_name.endswith('.eprj'):
            eprj_data = outer_zip.read(file_name)
            
            # Save to temp file
            temp_db = Path('temp_example.eprj')
            temp_db.write_bytes(eprj_data)
            
            # Open and inspect schema
            conn = sqlite3.connect(str(temp_db))
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            print('=== EasyEDA Pro SQLite Schema ===\n')
            for table_name in tables:
                table = table_name[0]
                print(f'TABLE: {table}')
                cursor.execute(f'PRAGMA table_info({table})')
                cols = cursor.fetchall()
                for col in cols:
                    print(f'  {col[1]:20} {col[2]:10}')
                
                # Show sample row count
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                print(f'  (rows: {count})\n')
            
            # Show CREATE TABLE statements
            print('\n=== CREATE TABLE Statements ===\n')
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL")
            for row in cursor.fetchall():
                print(row[0])
                print()
            
            conn.close()
            temp_db.unlink()
            break
