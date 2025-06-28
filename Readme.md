# Proyecto Microservicios Flask con API Gateway

Este proyecto implementa varios microservicios en Flask para gestión de usuarios, autenticación y tareas a través de un API Gateway.


# Instalación y configuración del entorno

1. Clona el repositorio:

```bash
git clone <https://github.com/morgan24jm/Microservices>
cd <Directorio-del-proyecto>

#Crea tu entorno de desarrollo
python3 -m venv venv 
#activa el entorno para instalar las dependecias con
source venv/bin/activate 
# El entonro se activara automaticamente desde la ejecucion del archivo start_services.sh

#Instala las dependencias desde requirements.txt
pip install -r requirements.txt

#Para iniciar todos los servicios solo ejecuta el siguiente comando estando en la ruta raiz del proyecto
./start_services.sh

#para detener los servicios ejecuta el siguiente comando 
./stop_services.sh.
```

 ## Observaciones
- Asegúrate de tener permisos de ejecución en los scripts ```(chmod +x start_services.sh stop_services.sh)```.

- El API Gateway se conecta a los microservicios usando localhost con los puertos correspondientes ``` (5001, 5002, 5003)```.

- Cada microservicio corre de manera independiente, pero coordinados por el API Gateway.

- Las pruebas se pueden hacer vía Postman o cualquier cliente HTTP apuntando al API Gateway (por ejemplo, en http://localhost:5000/auth/register).
