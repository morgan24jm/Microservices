from flask import Flask, jsonify, request
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Permite CORS para todas las rutas y orígenes (ajusta si quieres restringir)

# URLs de los microservicios
AUTH_SERVICE_URL = 'http://localhost:5001'
USER_SERVICE_URL = 'http://localhost:5002'
TASK_SERVICE_URL = 'http://localhost:5003'

def filter_headers(headers):
    # Copia los headers excepto 'Host' para pasar a microservicios
    return {key: value for key, value in headers.items() if key.lower() != 'host'}

# Proxy para autenticación (POST)
@app.route('/auth/<path:path>', methods=['POST'])
def auth_proxy(path):
    url = f"{AUTH_SERVICE_URL}/{path}"
    headers = filter_headers(request.headers)
    resp = requests.post(
        url,
        json=request.get_json(silent=True),
        headers=headers
    )
    return jsonify(resp.json()), resp.status_code

# Proxy para usuarios (GET, POST, PUT, DELETE)
@app.route('/user/<path:path>', methods=['GET','POST','PUT','DELETE'])
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

# Proxy para tareas (GET, POST, PUT, DELETE) en /tasks y /tasks/<path>
@app.route('/tasks', methods=['GET', 'POST'])
@app.route('/tasks/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
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

if __name__ == '__main__':
    app.run(port=5000, debug=True)
