import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), '..', 'ai_tally.db')
DB = os.path.abspath(DB)
print('DB path:', DB)
conn = sqlite3.connect(DB)
cur = conn.cursor()

def cols(table):
    cur.execute(f"PRAGMA table_info('{table}')")
    return [row[1] for row in cur.fetchall()]

for t in ['conversation_sessions', 'sync_queue_items']:
    try:
        print('\nTable:', t)
        print('Columns:', cols(t))
    except Exception as e:
        print('Error listing', t, e)

# Try to add missing columns

try:
    if 'previous_entities' not in cols('conversation_sessions'):
        print('Adding previous_entities')
        cur.execute("ALTER TABLE conversation_sessions ADD COLUMN previous_entities TEXT NOT NULL DEFAULT '{}'")
    if 'active_customer' not in cols('conversation_sessions'):
        print('Adding active_customer')
        cur.execute("ALTER TABLE conversation_sessions ADD COLUMN active_customer VARCHAR(200)")
    if 'active_products' not in cols('conversation_sessions'):
        print('Adding active_products')
        cur.execute("ALTER TABLE conversation_sessions ADD COLUMN active_products TEXT NOT NULL DEFAULT '[]'")
    if 'last_intent' not in cols('conversation_sessions'):
        print('Adding last_intent')
        cur.execute("ALTER TABLE conversation_sessions ADD COLUMN last_intent VARCHAR(120)")
except Exception as e:
    print('Error adding conversation columns:', e)

try:
    if 'updated_at' not in cols('sync_queue_items'):
        print('Adding updated_at to sync_queue_items')
        cur.execute("ALTER TABLE sync_queue_items ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")
except Exception as e:
    print('Error adding updated_at:', e)

conn.commit()
print('\nAfter migration:')
for t in ['conversation_sessions', 'sync_queue_items']:
    try:
        print('\nTable:', t)
        print('Columns:', cols(t))
    except Exception as e:
        print('Error listing', t, e)

conn.close()
print('\nDone')
