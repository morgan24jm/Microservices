from flask import Flask, request, jsonify
import sqlite3
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
DB_FILE = 'users.db'

# Inicializar rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Inicializar DB y crear tabla si no existe
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Ruta: Listar todos los usuarios
@app.route('/users', methods=['GET'])
@limiter.limit("10 per minute")
def get_users():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    rows = cursor.fetchall()
    conn.close()

    users = []
    for row in rows:
        users.append({
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "password": row[3]  
        })

    return jsonify({"users": users})

# Ruta: Obtener un usuario por ID
@app.route('/users/<int:user_id>', methods=['GET'])
@limiter.limit("10 per minute")
def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        user = {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "password": row[3]
        }
        return jsonify({"user": user})
    return jsonify({"error": "Usuario no encontrado"}), 404

# Ruta: Crear un nuevo usuario
@app.route('/users', methods=['POST'])
@limiter.limit("5 per minute")
def create_user():
    data = request.get_json()

    if not data or 'username' not in data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "username, email y password requeridos"}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (username, email, password)
        VALUES (?, ?, ?)
    ''', (data['username'], data['email'], data['password']))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "message": "Usuario creado",
        "user": {
            "id": user_id,
            "username": data['username'],
            "email": data['email'],
            "password": data['password']
        }
    }), 201

# Ruta: Actualizar usuario
@app.route('/users/<int:user_id>', methods=['PUT'])
@limiter.limit("5 per minute")
def update_user(user_id):
    data = request.get_json()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Usuario no encontrado"}), 404

    cursor.execute('''
        UPDATE users SET
            username = COALESCE(?, username),
            email = COALESCE(?, email),
            password = COALESCE(?, password)
        WHERE id = ?
    ''', (
        data.get('username'),
        data.get('email'),
        data.get('password'),
        user_id
    ))
    conn.commit()
    conn.close()

    return jsonify({"message": "Usuario actualizado"}), 200

# Ruta: Eliminar usuario
@app.route('/users/<int:user_id>', methods=['DELETE'])
@limiter.limit("5 per minute")
def delete_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Usuario no encontrado"}), 404

    return jsonify({"message": "Usuario eliminado"}), 200

if __name__ == '__main__':
    app.run(port=5002, debug=True)
