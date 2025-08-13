from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import jwt
import requests

# Importar logger y función para guardar en Mongo
from logger import logger, log_to_mongo

app = Flask(__name__)
CORS(app)

SECRET_KEY = os.getenv('SECRET_KEY')

# ====== Configuración de Rate Limiter ======
def get_user_or_ip():
    """Usar username del JWT o la IP del cliente"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            return payload.get('username', get_remote_address())
        except jwt.PyJWTError:
            return get_remote_address()
    return get_remote_address()

limiter = Limiter(
    get_user_or_ip,  # clave para el rate limit
    app=app,
    default_limits=["100 per minute"]  # Límite por defecto
)

# ===== Middleware de Logging =====
@app.before_request
def start_timer():
    request.start_time = time.time()

@app.before_request
def extract_user_from_jwt():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user = 'anonymous'
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            user = payload.get('username', 'anonymous')
        except jwt.PyJWTError:
            user = 'anonymous'
    request.headers.environ['HTTP_X_USER'] = user

@app.after_request
def log_request(response):
    duration = time.time() - request.start_time
    duration_ms = int(duration * 1000)

    timestamp = datetime.now(
        ZoneInfo("America/Mexico_City")).strftime('%Y-%m-%d %H:%M:%S')
    method = request.method
    path = request.path
    status = response.status_code

    if path.startswith('/auth'):
        service = 'auth-service'
    elif path.startswith('/user'):
        service = 'user-service'
    elif path.startswith('/tasks'):
        service = 'task-service'
    elif path.startswith('/logs'):
        service = 'logs-service'
    else:
        service = 'unknown'

    user = request.headers.get('X-User', 'anonymous')

    log_msg = (
        f"{timestamp} | {method} {path} | "
        f"Service: {service} | User: {user} | "
        f"Status: {status} | Duration: {duration_ms}ms"
    )
    logger.info(log_msg)

    log_document = {
        "timestamp": timestamp,
        "method": method,
        "path": path,
        "service": service,
        "user": user,
        "status": status,
        "duration_ms": duration_ms
    }
    log_to_mongo(log_document)

    return response

# ===== URLs de microservicios =====
AUTH_SERVICE_URL = 'http://localhost:5001'
USER_SERVICE_URL = 'http://localhost:5002'
TASK_SERVICE_URL = 'http://localhost:5003'
LOGS_SERVICE_URL = 'http://localhost:5004'

def filter_headers(headers):
    return {key: value for key, value in headers.items() if key.lower() != 'host'}

# ===== Rutas proxy con rate limit personalizado =====

@app.route('/auth/<path:path>', methods=['POST'])
@limiter.limit("10 per minute")  # Solo 10 solicitudes por minuto a /auth
def auth_proxy(path):
    url = f"{AUTH_SERVICE_URL}/{path}"
    headers = filter_headers(request.headers)
    resp = requests.post(
        url,
        json=request.get_json(silent=True),
        headers=headers
    )
    return jsonify(resp.json()), resp.status_code

@app.route('/user/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@limiter.limit("50 per minute")  # 50 solicitudes/min para /user
def user_proxy(path):
    url = f"{USER_SERVICE_URL}/{path}"
    headers = filter_headers(request.headers)
    resp = requests.request(
        method=request.method,
        url=url,
        json=request.get_json(silent=True),
        headers=headers
    )
    return jsonify(resp.json()), resp.status_code

@app.route('/tasks', methods=['GET', 'POST'])
@app.route('/tasks/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@limiter.limit("200 per hour")  # 200 solicitudes/hora para /tasks
def task_proxy(path=None):
    url = f"{TASK_SERVICE_URL}/tasks"
    if path:
        url += f"/{path}"
    headers = filter_headers(request.headers)
    resp = requests.request(
        method=request.method,
        url=url,
        json=request.get_json(silent=True),
        headers=headers
    )
    return jsonify(resp.json()), resp.status_code

@app.route('/logs', methods=['GET'])
@app.route('/logs/<path:path>', methods=['GET'])
@limiter.limit("20 per minute")  # 20 solicitudes/min para /logs
def logs_proxy(path=None):
    url = f"{LOGS_SERVICE_URL}/logs"
    if path:
        url += f"/{path}"
    headers = filter_headers(request.headers)
    resp = requests.request(
        method=request.method,
        url=url,
        json=request.get_json(silent=True),
        headers=headers
    )
    return jsonify(resp.json()), resp.status_code

if __name__ == '__main__':
    app.run(port=5000, debug=True)
