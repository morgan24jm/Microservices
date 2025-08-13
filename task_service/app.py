from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
import jwt
import os
from functools import wraps
from dotenv import load_dotenv
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
CORS(app)

# ==== Rate Limiting ====
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"]  # Límite global por IP
)

# Cargar .env desde la raíz del proyecto (una carpeta arriba de esta)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(ENV_PATH)

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
            current_username = data.get('username')
            if not current_username:
                return jsonify({'message': 'Token inválido: no contiene username'}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expirado, por favor inicia sesión nuevamente'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'message': 'Token inválido', 'error': str(e)}), 401

        return f(current_username, *args, **kwargs)

    return decorated

# Ruta: Crear tarea (protegida)
@app.route('/tasks', methods=['POST'])
@token_required
@limiter.limit("5 per minute")  # Límite específico
def create_task(current_username):
    data = request.get_json()
    description = data.get('description')
    deadline = data.get('deadline')
    status = data.get('status', 'pending')
    isalive = data.get('isalive', True)

    if not description:
        return jsonify({"error": "Faltan campos requeridos"}), 400

    created_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO task (description, created_at, deadline, status, isalive, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (description, created_at, deadline, status, isalive, current_username))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()

    return jsonify({"message": "Tarea creada", "id": task_id}), 201

# Ruta: Listar tareas (protegida - solo las del usuario)
@app.route('/tasks', methods=['GET'])
@token_required
@limiter.limit("10 per minute")
def get_tasks(current_username):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM task WHERE created_by = ?', (current_username,))
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
@limiter.limit("15 per minute")
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
@limiter.limit("5 per minute")
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
@limiter.limit("5 per minute")
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
