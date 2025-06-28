from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
import jwt
import os
from functools import wraps
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto (una carpeta arriba de esta)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(ENV_PATH)

app = Flask(__name__)
DB_FILE = 'tasks.db'

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("No se encontró la SECRET_KEY en las variables de entorno")

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
            created_by TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Decorador para proteger rutas con token JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            parts = auth_header.split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]

        if not token:
            return jsonify({'message': 'Token es requerido'}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user_id = data.get('user_id')
            if not current_user_id:
                return jsonify({'message': 'Token inválido: no contiene usuario'}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expirado, por favor inicia sesión nuevamente'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'message': 'Token inválido', 'error': str(e)}), 401

        return f(current_user_id, *args, **kwargs)
    return decorated

# Ruta: Crear tarea (protegida)
@app.route('/tasks', methods=['POST'])
@token_required
def create_task(current_user_id):
    data = request.get_json()
    description = data.get('description')
    deadline = data.get('deadline')
    status = data.get('status', 'pending')
    isalive = data.get('isalive', True)

    if not description:
        return jsonify({"error": "Faltan campos requeridos"}), 400

    created_at = datetime.utcnow().isoformat()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO task (description, created_at, deadline, status, isalive, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (description, created_at, deadline, status, isalive, current_user_id))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()

    return jsonify({"message": "Tarea creada", "id": task_id}), 201

# Ruta: Listar tareas (protegida - solo las del usuario)
@app.route('/tasks', methods=['GET'])
@token_required
def get_tasks(current_user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM task WHERE created_by = ?', (current_user_id,))
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

# Ruta: Obtener una tarea (no protegida aún)
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
