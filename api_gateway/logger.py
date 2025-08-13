import logging
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

os.makedirs('logs', exist_ok=True)

# Leer la URI desde variable de entorno
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("La variable de entorno MONGO_URI no está definida")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client["Logs"]       # base de datos
logs_collection = db["Logs"]    # colección

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


def log_to_mongo(log_data):
    try:
        logs_collection.insert_one(log_data)
    except Exception as e:
        logger.error(f"Error insertando log en MongoDB: {e}")
