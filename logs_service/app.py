from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from pathlib import Path
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Cargar variables de entorno
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("No se encontró MONGO_URI en .env")

# Conexión a MongoDB
client = MongoClient(MONGO_URI)
db = client["Logs"]        
logs_collection = db["Logs"]  

app = Flask(__name__)
CORS(app)

# ==== Rate Limiting ====
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"]  # Límite global
)

# Endpoint: Conteo por status code
@app.route("/logs/status-count", methods=["GET"])
@limiter.limit("10 per minute")
def get_status_count():
    pipeline = [
        {"$group": {"_id": "$status", "total": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    result = list(logs_collection.aggregate(pipeline))
    return jsonify(result)

# Endpoint: Response time promedio
@app.route("/logs/average-response", methods=["GET"])
@limiter.limit("10 per minute")
def get_average_response():
    pipeline = [
        {"$group": {"_id": None, "promedio_ms": {"$avg": "$duration_ms"}}}
    ]
    result = list(logs_collection.aggregate(pipeline))
    return jsonify(result[0] if result else {})

# Endpoint: Response time más rápido y más lento
@app.route("/logs/minmax-response", methods=["GET"])
@limiter.limit("10 per minute")
def get_minmax_response():
    pipeline = [
        {"$group": {
            "_id": None,
            "mas_rapido": {"$min": "$duration_ms"},
            "mas_lento": {"$max": "$duration_ms"}
        }}
    ]
    result = list(logs_collection.aggregate(pipeline))
    return jsonify(result[0] if result else {})

# Endpoint: API más y menos consumida
@app.route("/logs/api-usage", methods=["GET"])
@limiter.limit("10 per minute")
def get_api_usage():
    pipeline = [
        {"$group": {"_id": "$path", "total": {"$sum": 1}}},
        {"$sort": {"total": -1}}
    ]
    result = list(logs_collection.aggregate(pipeline))
    return jsonify(result)

# Endpoint: Total de logs
@app.route("/logs/total", methods=["GET"])
@limiter.limit("10 per minute")
def get_total_logs():
    total = logs_collection.count_documents({})
    return jsonify({"total_logs": total})

if __name__ == "__main__":
    app.run(port=5004, debug=True)
