from flask import Flask, jsonify, request
import requests
from flask_cors import CORS

import time
import logging
from datetime import datetime, timezone
import os

app = Flask(__name__)
CORS(app)  


os.makedirs('logs', exist_ok=True)

logger = logging.getLogger('api_gateway_logger')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

file_handler = logging.FileHandler('logs/api_gateway.log')
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)


if logger.hasHandlers():
    logger.handlers.clear()

logger.addHandler(file_handler)
logger.addHandler(console_handler)


#Middleware de Logging
@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def log_request(response):
    duration = time.time() - request.start_time
    duration_ms = int(duration * 1000)

    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    method = request.method
    path = request.path
    status = response.status_code

 
    if path.startswith('/auth'):
        service = 'auth-service'
    elif path.startswith('/user'):
        service = 'user-service'
    elif path.startswith('/tasks'):
        service = 'task-service'
    else:
        service = 'unknown'

   
    user = request.headers.get('X-User')
    if not user:
        try:
            json_data = request.get_json(silent=True)
            if json_data:
                user = json_data.get('username', 'anonymous')
        except:
            user = 'anonymous'
    user = user or 'anonymous'

   
    log_msg = (
        f"{timestamp} | {method} {path} | "
        f"Service: {service} | User: {user} | "
        f"Status: {status} | Duration: {duration_ms}ms"
    )
    logger.info(log_msg)

    return response


AUTH_SERVICE_URL = 'http://localhost:5001'
USER_SERVICE_URL = 'http://localhost:5002'
TASK_SERVICE_URL = 'http://localhost:5003'

def filter_headers(headers):
   
    return {key: value for key, value in headers.items() if key.lower() != 'host'}




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


@app.route('/user/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
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
