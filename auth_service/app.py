from flask import Flask, request, jsonify
import sqlite3
from dotenv import load_dotenv
import os
import jwt
import datetime
from flask_cors import CORS
import pyotp
import qrcode
import io
import base64
import requests
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(ENV_PATH)

app = Flask(__name__)
CORS(app)

# ======== Rate Limiting ========
limiter = Limiter(
    get_remote_address,          # Limita por IP
    app=app,
    default_limits=["100 per minute"]  # Límite global
)

DB_FILE = os.path.join(BASE_DIR, 'auth.db')
SECRET_KEY = os.getenv('SECRET_KEY')
USER_SERVICE_URL = "http://localhost:5002/users"

if not SECRET_KEY:
    raise ValueError("No se encontró la SECRET_KEY en .env")

# Inicializar DB de auth solo para OTP
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS otp_data (
            user_id INTEGER PRIMARY KEY,
            otp_secret TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ===== Registro =====
@app.route('/register', methods=['POST'])
@limiter.limit("5 per minute")  # Máximo 5 registros por IP por minuto
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ('username', 'password', 'email')):
        return jsonify({"error": "Faltan username, password o email"}), 400

    try:
        resp = requests.get(USER_SERVICE_URL)
        resp.raise_for_status()
        users = resp.json().get("users", [])
        if any(u["email"] == data['email'] for u in users):
            return jsonify({"error": "El correo electrónico ya está registrado"}), 409
    except requests.RequestException as e:
        return jsonify({"error": "No se pudo conectar al User Service", "detalle": str(e)}), 500

    try:
        resp = requests.post(USER_SERVICE_URL, json=data)
        resp.raise_for_status()
        user_info = resp.json()["user"]
    except requests.RequestException as e:
        return jsonify({"error": "Error creando usuario en User Service", "detalle": str(e)}), 400

    otp_secret = pyotp.random_base32()
    totp_uri = pyotp.TOTP(otp_secret).provisioning_uri(
        name=data['username'], issuer_name="TASK APP"
    )
    buf = io.BytesIO()
    qrcode.make(totp_uri).save(buf)
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO otp_data (user_id, otp_secret) VALUES (?, ?)',
                       (user_info['id'], otp_secret))
        conn.commit()

    return jsonify({
        "message": "Usuario registrado exitosamente",
        "user": user_info,
        "otp_qr": img_base64
    }), 201

# ===== Login =====
@app.route('/login', methods=['POST'])
@limiter.limit("10 per minute")  # Máximo 10 logins por IP por minuto
def login():
    data = request.get_json()
    if not data or 'identifier' not in data or 'password' not in data or 'otp' not in data:
        return jsonify({"error": "Faltan datos (identifier, password, otp)"}), 400

    identifier = str(data['identifier']).strip()
    password = str(data['password'])
    code = str(data.get('otp', '')).strip()

    try:
        resp = requests.get(USER_SERVICE_URL)
        resp.raise_for_status()
        users = resp.json().get("users", [])
        user = next((u for u in users
                     if (u.get("username") == identifier or u.get("email") == identifier)
                     and u.get("password") == password), None)
    except Exception as e:
        return jsonify({"error": "No se pudo conectar al User Service", "detalle": str(e)}), 500

    if not user:
        return jsonify({"error": "Credenciales inválidas"}), 401

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT otp_secret FROM otp_data WHERE user_id = ?', (user["id"],))
        row = cursor.fetchone()

    if not row:
        return jsonify({"error": "No se encontró OTP para este usuario"}), 401

    secret_raw = row[0]
    secret = secret_raw.decode() if isinstance(secret_raw, (bytes, bytearray)) else str(secret_raw)
    secret = secret.strip()

    if not code.isdigit() or len(code) != 6:
        return jsonify({"error": "Formato de OTP inválido"}), 400

    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        return jsonify({"error": "Código OTP incorrecto"}), 401

    payload = {
        'user_id': user["id"],
        'username': user.get("username"),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return jsonify({"mensaje": "Login exitoso", "token": token}), 200

if __name__ == '__main__':
    app.run(port=5001, debug=True)
