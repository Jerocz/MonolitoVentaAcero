# Despliegue en AWS Academy (EC2 + IP elástica)

Todo el ecosistema corre en **una sola instancia EC2** con Docker Compose.
Nginx (API Gateway) es el único contenedor que publica un puerto (80).

## 1. Crear la instancia (AWS Academy → Learner Lab → *Start Lab* → AWS)

| Parámetro | Valor recomendado |
|---|---|
| AMI | Ubuntu Server 24.04 LTS (x86_64) |
| Tipo | `t3.medium` (2 vCPU, 4 GB). `t3.small` funciona gracias al swap de 2 GB, pero es más lenta para compilar las imágenes |
| Par de claves | `vockey` (descargar `labsuser.pem` desde *AWS Details*) |
| Almacenamiento | 20 GB gp3 |
| Security Group | Entrada: **SSH 22** (Mi IP) y **HTTP 80** (0.0.0.0/0). Nada más: PostgreSQL, Redis y los microservicios **no** se exponen |

## 2. Asignar la IP elástica

EC2 → *Elastic IPs* → **Allocate Elastic IP address** → *Actions* →
**Associate** → elegir la instancia. Esa IP no cambia aunque el laboratorio
se apague y es la que se entrega en la plataforma institucional.

## 3. Instalar y levantar

```bash
ssh -i labsuser.pem ubuntu@<IP-ELASTICA>
curl -fsSL https://raw.githubusercontent.com/Jerocz/MonolitoVentaAcero/main/deploy/aws/instalar_ec2.sh | sh
```

El script ([`deploy/aws/instalar_ec2.sh`](../deploy/aws/instalar_ec2.sh)) instala Docker,
crea 2 GB de swap, clona la rama `main`, genera un `.env` con claves aleatorias
y ejecuta `docker compose up -d --build`.

Para configurar el servicio del equipo aliado:

```bash
cd ~/MonolitoVentaAcero
nano .env              # ALIADO_NOMBRE=...  ALIADO_API_URL=http://IP-ALIADO/api/...
sudo docker compose up -d web worker
```

## 4. Verificar

| URL | Qué muestra |
|---|---|
| `http://<IP>/` | Aplicación web (Django) |
| `http://<IP>/salud/` | Estado de BD, Redis, los 3 microservicios, worker de Celery y circuit breakers |
| `http://<IP>/gateway/salud` | Respuesta directa de Nginx |
| `http://<IP>/api/catalogo/publico/v1/productos` | **Servicio que proveemos** al equipo aliado |
| `http://<IP>/api/fabricacion/ordenes` | Microservicio de fabricación (solo lectura) |
| `http://<IP>/integraciones/` | Servicio aliado consumido + API de terceros (tasa de cambio) |
| `http://<IP>/procesos/` | Reportes y notificaciones generados por Celery |

```bash
sudo docker compose ps          # todos deben estar "healthy"
sudo docker compose logs -f worker
```

## 5. Día de la sustentación

AWS Academy apaga la instancia cuando termina la sesión del laboratorio.
Antes de la sustentación: **Start Lab** → EC2 → *Start instance*. Los
contenedores tienen `restart: unless-stopped` y Docker arranca con el sistema,
así que el ecosistema vuelve solo (esperar ~1 minuto a que estén *healthy*).

## Actualizar después de un nuevo commit

```bash
cd ~/MonolitoVentaAcero && git pull && sudo docker compose up -d --build
```
