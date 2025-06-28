from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_FILE = 'tasks.db'

# Crear la tabla si no existe
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL,
            deadline TEXT,
            status TEXT,
            isalive BOOLEAN,
            created_by INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Ruta: Crear tarea
@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    description = data.get('description')
    deadline = data.get('deadline')
    status = data.get('status', 'pending')
    isalive = data.get('isalive', True)
    created_by = data.get('created_by')

    if not description or not created_by:
        return jsonify({"error": "Faltan campos requeridos"}), 400

    created_at = datetime.utcnow().isoformat()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO task (description, created_at, deadline, status, isalive, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (description, created_at, deadline, status, isalive, created_by))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()

    return jsonify({"message": "Tarea creada", "id": task_id}), 201

# Ruta: Listar tareas
@app.route('/tasks', methods=['GET'])
def get_tasks():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM task')
    rows = cursor.fetchall()
    conn.close()

    tasks = []
    for row in rows:
        tasks.append({
            "id": row[0],
            "description": row[1],
            "created_at": row[2],
            "deadline": row[3],
            "status": row[4],
            "isalive": bool(row[5]),
            "created_by": row[6]
        })

    return jsonify(tasks)

# Ruta: Obtener una tarea
@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM task WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        task = {
            "id": row[0],
            "description": row[1],
            "created_at": row[2],
            "deadline": row[3],
            "status": row[4],
            "isalive": bool(row[5]),
            "created_by": row[6]
        }
        return jsonify(task)
    return jsonify({"error": "Tarea no encontrada"}), 404

# Ruta: Actualizar tarea
@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.get_json()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM task WHERE id = ?', (task_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Tarea no encontrada"}), 404

    cursor.execute('''
        UPDATE task SET
            description = COALESCE(?, description),
            deadline = COALESCE(?, deadline),
            status = COALESCE(?, status),
            isalive = COALESCE(?, isalive)
        WHERE id = ?
    ''', (data.get('description'), data.get('deadline'), data.get('status'),
          data.get('isalive'), task_id))
    conn.commit()
    conn.close()

    return jsonify({"message": "Tarea actualizada"}), 200

# Ruta: Eliminar tarea
@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM task WHERE id = ?', (task_id,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Tarea no encontrada"}), 404

    return jsonify({"message": "Tarea eliminada"}), 200

if __name__ == '__main__':
    app.run(port=5003, debug=True)
