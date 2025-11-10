import sqlite3

conn = sqlite3.connect('registrations.db')
cur = conn.cursor()
cur.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cur.fetchall()
print('Tables:', [t[0] for t in tables])

if 'teams' in [t[0] for t in tables]:
    cur.execute('SELECT COUNT(*) FROM teams')
    count = cur.fetchone()[0]
    print('Registrations:', count)
else:
    print('No teams table found')

conn.close()
