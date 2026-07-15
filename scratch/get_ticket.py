import sqlite3
import json

conn = sqlite3.connect('data/checkpoints.db')
c = conn.cursor()
c.execute('SELECT thread_id, state FROM checkpoints WHERE thread_id LIKE "TKT-%" ORDER BY rowid DESC LIMIT 4')
for row in c.fetchall():
    print("="*40)
    print("TICKET:", row[0])
    state = json.loads(row[1])
    print("TIPO:", state.get("tipo_solicitud"))
    print("INPUT:", state.get("_current_input"))
    print("NEXT:", state.get("next_step"))
    print("CLIENTE:", state.get("cliente"))
    print("DIAGNOSTICO:", state.get("diagnostico"))
conn.close()
