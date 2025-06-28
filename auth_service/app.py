from flask import Flask, request, jsonify
import sqlite3
from dotenv import load_dotenv
import os
import jwt
import datetime

# Cargar .env desde la raíz del proyecto (una carpeta arriba de esta)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(ENV_PATH)

app = Flask(__name__)
DB_FILE = 'auth.db'

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("No se encontró la SECRET_KEY en las variables de entorno")

# Crear tabla si no existe
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Ruta: Registro de usuario
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Faltan username o password"}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO users (username, password) VALUES (?, ?)
        ''', (data['username'], data['password']))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        return jsonify({
            "message": "Usuario registrado exitosamente",
            "user": {
                "id": user_id,
                "username": data['username']
            }
        }), 201

    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "El nombre de usuario ya existe"}), 409

# Ruta: Login con token JWT de 5 minutos
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Faltan username o password"}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, password FROM users WHERE username = ?
    ''', (data['username'],))
    row = cursor.fetchone()
    conn.close()

    if row and row[1] == data['password']:
        payload = {
            'user_id': row[0],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({
            "mensaje": "Login exitoso",
            "token": token
        }), 200

    return jsonify({"error": "Credenciales inválidas"}), 401

if __name__ == '__main__':
    app.run(port=5001, debug=True)
