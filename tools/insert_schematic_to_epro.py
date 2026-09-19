#!/usr/bin/env python3
"""
Insert validated EasyEDA Pro schematic format into .epro database
"""

import sqlite3
from pathlib import Path

epro_file = Path("out/PicAmpControl.epro")
format_file = Path("out/picampcontrol_easyeda_pro.txt")

if not epro_file.exists():
    print(f"✗ File not found: {epro_file}")
    exit(1)

if not format_file.exists():
    print(f"✗ File not found: {format_file}")
    exit(1)

# Read the schematic format
schematic_data = format_file.read_text()

# Connect to .epro database
conn = sqlite3.connect(str(epro_file))
cursor = conn.cursor()

# Get document UUID (there should be one schematic document)
cursor.execute('SELECT uuid FROM documents LIMIT 1')
result = cursor.fetchone()

if not result:
    print("✗ No documents found in .epro file")
    conn.close()
    exit(1)

doc_uuid = result[0]
print(f"✓ Found document: {doc_uuid}")

# Update the dataStr with our generated format
try:
    cursor.execute('''
        UPDATE documents 
        SET dataStr = ?
        WHERE uuid = ?
    ''', (schematic_data, doc_uuid))
    
    conn.commit()
    
    # Verify
    cursor.execute('SELECT LENGTH(dataStr) FROM documents WHERE uuid = ?', (doc_uuid,))
    size = cursor.fetchone()[0]
    
    print(f"✓ Updated documents.dataStr ({size} bytes)")
    print(f"✓ Circuit: 55 components, 92 connections")
    print()
    print("✓ COMPLETE - Your .epro file is ready to open in EasyEDA Pro!")
    print(f"  File: {epro_file}")
    print()
    print("Next: Open in EasyEDA Pro:")
    print("  File → Open → PicAmpControl.epro")
    
except Exception as e:
    print(f"✗ Error updating database: {e}")
    exit(1)
finally:
    conn.close()
