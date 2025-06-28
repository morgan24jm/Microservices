from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# URLs de los microservicios
AUTH_SERVICE_URL = 'http://localhost:5001'
USER_SERVICE_URL = 'http://localhost:5002'
TASK_SERVICE_URL = 'http://localhost:5003'
# Restringir a la ruta de autenticación auth service
@app.route('/auth/<path:path>', methods=['POST'])
def auth_proxy(path):
    url = f"{AUTH_SERVICE_URL}/{path}"
    
    headers = {}
    for key, value in request.headers:
        if key != 'Host':
            headers[key] = value
    
    resp = requests.request(
        method=request.method,
        url=url,
        json=request.get_json(),
        headers=headers
    )
    return jsonify(resp.json()), resp.status_code

@app.route('/user/<path:path>', methods=['GET','POST','PUT','DELETE'])
def user_proxy(path):
    url = f"{USER_SERVICE_URL}/{path}"
    
    headers = {}
    for key, value in request.headers:
        if key != 'Host':
            headers[key] = value
    
    resp = requests.request(
        method=request.method,
        url=url,
        json=request.get_json(),
        headers=headers
    )
    return jsonify(resp.json()), resp.status_code

@app.route('/task/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def task_proxy(path):
    url = f"{TASK_SERVICE_URL}/{path}"
    
    headers = {key: value for key, value in request.headers if key != 'Host'}
    
    resp = requests.request(
        method=request.method,
        url=url,
        json=request.get_json(),
        headers=headers
    )
    return jsonify(resp.json()), resp.status_code


if __name__ == '__main__':
    app.run(port=5000, debug=True)