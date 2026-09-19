#!/usr/bin/env python3
"""
Generate EasyEDA Pro .eprj file from YAML schematic specification
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path


def create_eprj_database(json_path: Path, eprj_path: Path) -> None:
    """Create an EasyEDA Pro .eprj SQLite database"""
    
    # Read the schematic JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        schematic = json.load(f)
    
    # Create database connection
    conn = sqlite3.connect(str(eprj_path))
    cursor = conn.cursor()
    
    # Create essential tables (simplified from full schema)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            uuid varchar PRIMARY KEY NOT NULL,
            archive boolean NOT NULL,
            name varchar NOT NULL,
            content varchar NOT NULL,
            cbb_project boolean NOT NULL DEFAULT (0),
            thumb varchar NOT NULL,
            ticket integer NOT NULL,
            g_ticket integer NOT NULL DEFAULT (1),
            owner_uuid varchar,
            creator_uuid varchar,
            created_at datetime NOT NULL DEFAULT (datetime('now')),
            updated_at datetime NOT NULL DEFAULT (datetime('now')),
            modifier_uuid varchar,
            boards varchar NOT NULL DEFAULT ('{}'),
            block_symbol_attrs_groups varchar NOT NULL DEFAULT ('{}'),
            pcb_count integer NOT NULL DEFAULT (0),
            default_sheet TEXT DEFAULT ""
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schematics (
            uuid varchar PRIMARY KEY NOT NULL,
            description varchar NOT NULL DEFAULT (''),
            ticket integer NOT NULL DEFAULT (1),
            sheet_count integer NOT NULL DEFAULT (0),
            project_uuid varchar NOT NULL,
            name varchar NOT NULL,
            display_name varchar NOT NULL,
            createtime integer NOT NULL,
            updatetime integer NOT NULL,
            created_at datetime NOT NULL DEFAULT (datetime('now')),
            updated_at datetime NOT NULL DEFAULT (datetime('now')),
            sort varchar NOT NULL DEFAULT ('')
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            uuid varchar PRIMARY KEY NOT NULL,
            title varchar NOT NULL,
            display_title varchar NOT NULL,
            description varchar NOT NULL,
            docType integer NOT NULL,
            dataStr text NOT NULL,
            sheet_id integer NOT NULL DEFAULT (1),
            ticket integer NOT NULL DEFAULT (1),
            sort_ticket integer NOT NULL DEFAULT (1),
            created_at datetime NOT NULL DEFAULT (datetime('now')),
            updated_at datetime NOT NULL DEFAULT (datetime('now')),
            creator_uuid varchar,
            schematic_uuid varchar,
            project_uuid varchar,
            image TEXT
        )
    ''')
    
    # Generate UUIDs
    project_uuid = str(uuid.uuid4())
    schematic_uuid = str(uuid.uuid4())
    document_uuid = str(uuid.uuid4())
    
    # Current timestamp
    now = datetime.now()
    timestamp = int(now.timestamp() * 1000)
    
    # Insert project
    cursor.execute('''
        INSERT INTO projects (uuid, archive, name, content, cbb_project, thumb, ticket, owner_uuid, creator_uuid)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        project_uuid,
        False,
        'PicAmpControl',
        'PIC16F18855-based linear amplifier protection controller',
        False,
        '',
        1,
        None,
        None
    ))
    
    # Insert schematic
    cursor.execute('''
        INSERT INTO schematics (uuid, description, ticket, sheet_count, project_uuid, name, display_name, createtime, updatetime)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        schematic_uuid,
        'Main schematic with amplifier control circuit',
        1,
        1,
        project_uuid,
        'Sheet1',
        'Schematic1',
        timestamp,
        timestamp
    ))
    
    # Insert document (schematic data)
    cursor.execute('''
        INSERT INTO documents (uuid, title, display_title, description, docType, dataStr, sheet_id, ticket, creator_uuid, schematic_uuid, project_uuid)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        document_uuid,
        'Sheet1',
        'Schematic Sheet 1',
        'Main schematic sheet',
        1,  # docType 1 = schematic
        json.dumps(schematic, ensure_ascii=False),
        1,
        1,
        None,
        schematic_uuid,
        project_uuid
    ))
    
    # Insert system config
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            key varchar PRIMARY KEY NOT NULL,
            value varchar NOT NULL
        )
    ''')
    
    cursor.execute('''
        INSERT OR IGNORE INTO system_config (key, value)
        VALUES ('db_version', '1.0.0')
    ''')
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f'✓ Created: {eprj_path}')
    print(f'  Project UUID: {project_uuid}')
    print(f'  Schematic UUID: {schematic_uuid}')
    print(f'  Document UUID: {document_uuid}')
    print(f'  Schematic data stored in documents table')


def main():
    json_path = Path('out/picampcontrol_easyeda.json')
    eprj_path = Path('out/PicAmpControl.eprj')
    
    if not json_path.exists():
        print(f'Error: {json_path} not found')
        return
    
    create_eprj_database(json_path, eprj_path)
    
    # Verify
    file_size = eprj_path.stat().st_size
    print(f'  Size: {file_size} bytes')
    print()
    print('✓ Ready to open in EasyEDA Pro')
    print('  File → Open → PicAmpControl.eprj')


if __name__ == '__main__':
    main()
