import sqlite3
import requests
import urllib
import json
import hashlib
import sys


def hash_for(conn, key, metadata):
    assert key in ('source', 'license')
    name = metadata.get(key)
    url = metadata.get(key + '_url')
    if not (name and url):
        return None
    # Insert if missing
    hash = hashlib.sha1(
        (name + ':' + url).encode('utf8')
    ).hexdigest()[:8]
    if conn.execute(
        'select * from {}s where hash = ?'.format(key), (hash,)
    ).fetchall():
        return hash
    conn.execute('''
        INSERT INTO {key}s (hash, {key}, {key}_url)
        VALUES (:hash, :name, :url);
    '''.format(key=key), {
        'hash': hash,
        'name': name,
        'url': url,
    })
    conn.commit()
    return hash


def build_database(filename, registry):
    conn = sqlite3.connect(filename)
    create_tables(conn)
    cursor = conn.cursor()
    for item in registry:
        url = item['url']
        try:
            metadata = requests.get(
                urllib.parse.urljoin(url, '/-/metadata.json')
            ).json()
        except Exception as e:
            print(url, e)
            metadata = {}
        try:
            inspect = requests.get(
                urllib.parse.urljoin(url, '/-/inspect.json')
            ).json()
        except Exception as e:
            print(url, e)
            inspect = {}
        cursor.execute('''
            INSERT INTO datasettes (
                title, url, about_url, description,
                source_hash, license_hash
            ) VALUES (
                :title, :url, :about_url, :description,
                :source_hash, :license_hash
            )
        ''', {
            'title': metadata.get('title', item.get('title')),
            'url': url,
            'about_url': item.get('about_url'),
            'description': item.get('description', metadata.get('description')),
            'source_hash': hash_for(conn, 'source', metadata) or '',
            'license_hash': hash_for(conn, 'license', metadata) or '',
        })
        datasette_id = cursor.lastrowid
        # Add any tags
        for tag in item.get('tags', []):
            cursor.execute('''
                REPLACE INTO tags (tag)
                    VALUES
                (?)
            ''', (tag,))
            cursor.execute('''
                INSERT INTO datasette_tags
                    (datasette_id, tag)
                VALUES (?, ?)
            ''', (datasette_id, tag))
        # Create the databases
        for name, database in inspect.items():
            cursor.execute('''
                INSERT INTO databases (
                    datasette_id, name
                ) VALUES (
                    :datasette_id, :name
                );
            ''', {
                'datasette_id': datasette_id,
                'name': name,
            })
            database_id = cursor.lastrowid
            # Create the views
            for view in database.get('views', []):
                cursor.execute('''
                    INSERT INTO views (
                        database_id, name
                    ) VALUES (
                        :database_id, :name
                    );
                ''', {
                    'database_id': database_id,
                    'name': view,
                })
            # Create the tables
            for table_name, table in database.get('tables', {}).items():
                cursor.execute('''
                    INSERT INTO tables (
                        database_id, name, count, has_fts,
                        is_hidden, label_column
                    ) VALUES (
                        :database_id, :name, :count, :has_fts,
                        :is_hidden, :label_column
                    );
                ''', {
                    'database_id': database_id,
                    'name': table_name,
                    'count': table['count'],
                    'has_fts': bool(table.get('fts_table')),
                    'is_hidden': bool(table['hidden']),
                    'label_column': table['label_column'],
                })
                table_id = cursor.lastrowid
                # Add the columns
                for column in table['columns']:
                    cursor.execute('''
                        INSERT INTO columns (
                            table_id, name
                        ) VALUES (
                            :table_id, :name
                        );
                    ''', {
                        'table_id': table_id,
                        'name': column,
                    })
    conn.commit()



def create_tables(conn):
    conn.executescript('''
        CREATE TABLE tags (
            tag text PRIMARY KEY
        );
        CREATE TABLE sources (
            hash text PRIMARY KEY,
            source text,
            source_url text
        );
        CREATE TABLE licenses (
            hash text PRIMARY KEY,
            license text,
            license_url text
        );
        CREATE TABLE datasettes (
            id integer PRIMARY KEY,
            title text,
            url text,
            about_url text,
            description text,
            source_hash text,
            license_hash text,
            FOREIGN KEY (source_hash) REFERENCES sources(hash),
            FOREIGN KEY (license_hash) REFERENCES licenses(hash)
        );
        CREATE TABLE datasette_tags (
            datasette_id integer,
            tag text,
            PRIMARY KEY (datasette_id, tag),
            FOREIGN KEY (datasette_id) REFERENCES datasettes(id),
            FOREIGN KEY (tag) REFERENCES tags(tag)
        );
        CREATE TABLE databases (
            id integer PRIMARY KEY,
            datasette_id integer,
            name text,
            -- TODO: source_hash, license_hash etc
            FOREIGN KEY (datasette_id) REFERENCES datasettes(id)
        );
        CREATE TABLE tables (
            id integer PRIMARY KEY,
            database_id integer,
            name text,
            count integer,
            has_fts integer,
            is_hidden integer,
            label_column text,
            FOREIGN KEY (database_id) REFERENCES databases(id)
        );
        CREATE TABLE views (
            id integer PRIMARY KEY,
            database_id integer,
            name text,
            FOREIGN KEY (database_id) REFERENCES databases(id)
        );
        CREATE TABLE columns (
            id integer PRIMARY KEY,
            table_id integer,
            name text,
            FOREIGN KEY (table_id) REFERENCES tables(id)
        );
    ''')


if __name__ == '__main__':
    build_database(
        'registry.db', json.load(open('registry.json'))
    )
