#!/bin/bash
#! Script para detener todos los microservicios del proyecto

# Definimos el directorio base del proyecto
PROJECT_DIR="${PWD}"
LOG_DIR="${PROJECT_DIR}/logs"

# Lista de servicios
SERVICES=("api_gateway" "auth_service" "user_service" "task_service" "logs_service")

# Detenemos cada servicio
for SERVICE in "${SERVICES[@]}"; do
    PID_FILE="${LOG_DIR}/${SERVICE}.pid"

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill "$PID" > /dev/null 2>&1; then
            echo "Servicio $SERVICE detenido (PID: $PID)"
            rm "$PID_FILE"
        else
            echo "No se pudo detener $SERVICE o ya estaba detenido"
        fi
    else
        echo "No se encontró el archivo PID para $SERVICE"
    fi
done

echo "Todos los servicios han sido detenidos."
