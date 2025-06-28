#!/bin/bash
#! Script para iniciar todos los microservicios del proyecto
#! Activa el entorno virtual y ejecuta cada servicio en segundo plano 

#! Definimos el directorio base del proyecto
PROJECT_DIR="${PWD}"
VENV_DIR="${PROJECT_DIR}/venv"
LOG_DIR="${PROJECT_DIR}/logs"

#! Creamos un directorio para los logs si no existe
mkdir -p "${LOG_DIR}"

#!  verificamos si el entrono virtual existe
if [ ! -d "${VENV_DIR}" ]; then
echo"Error: No se encontró el entorno virtual en ${VENV_DIR}"
exit 1
fi

#! Activamos el entorno virtual
source "${VENV_DIR}/scripts/activate"

#! Verificamos si los puertos están disponibles
check_port() {
 local port=$1
 if lsof -i :$port > /dev/null; then
   echo "Error: El puerto $port ya está en uso."
   exit 1
 fi
}

check_port 5000
check_port 5001
check_port 5002 
check_port 5003

# Función para iniciar un servicio
start_service() {
  local service_dir=$1
  local service_name=$2
  local port=$3

  echo "Iniciando ${service_name} en el puerto ${port}..."

  cd "${PROJECT_DIR}/${service_dir}" || { echo "No se encontró ${service_dir}"; exit 1; }

  python3 app.py --port $port > "${LOG_DIR}/${service_name}.log" 2>&1 &

  echo $! > "${LOG_DIR}/${service_name}.pid"

  cd "${PROJECT_DIR}"
}


# iniciamos cada microservicio
start_service "api_gateway" "api_gateway" 5000
start_service "auth_service" "auth_service" 5001
start_service "user_service" "user_service" 5002
start_service "task_service" "task_service" 5003

echo "Todos los servicios han sido iniciados."
echo "logs disponibles en $LOG_DIR"
echo "Para detener los servicios, usa: ./stop_services.sh"
