#!/bin/sh
# Instala Docker y levanta el ecosistema en una instancia EC2 (Ubuntu 22.04/24.04)
# de AWS Academy. Ejecutar dentro de la instancia:
#
#   curl -fsSL https://raw.githubusercontent.com/Jerocz/MonolitoVentaAcero/main/deploy/aws/instalar_ec2.sh | sh
#
# o, si ya clonaste el repositorio:  sh deploy/aws/instalar_ec2.sh
set -e

REPO_URL="${REPO_URL:-https://github.com/Jerocz/MonolitoVentaAcero.git}"
DESTINO="${DESTINO:-$HOME/MonolitoVentaAcero}"

echo "==> 1/5 Instalando Docker Engine y el plugin compose"
if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl git
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo systemctl enable --now docker   # Docker arranca solo cuando la instancia se reinicia
sudo usermod -aG docker "$USER" || true

echo "==> 2/5 Swap de 2 GB (evita quedarse sin memoria en instancias pequenas)"
if [ ! -f /swapfile ]; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

echo "==> 3/5 Descargando el codigo (rama main)"
if [ -d "$DESTINO/.git" ]; then
  git -C "$DESTINO" pull --ff-only
else
  git clone --branch main "$REPO_URL" "$DESTINO"
fi
cd "$DESTINO"

echo "==> 4/5 Generando .env con claves aleatorias (solo la primera vez)"
if [ ! -f .env ]; then
  cp .env.example .env
  aleatorio() { tr -dc 'A-Za-z0-9' </dev/urandom | head -c "$1"; }
  sed -i "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$(aleatorio 50)|" .env
  for VAR in VENTAS CATALOGO PAGOS FABRICACION; do
    sed -i "s|^${VAR}_DB_PASSWORD=.*|${VAR}_DB_PASSWORD=$(aleatorio 24)|" .env
  done
fi

echo "==> 5/5 Construyendo y levantando los contenedores"
sudo docker compose up -d --build
sudo docker compose ps

IP=$(curl -fsS --max-time 3 http://checkip.amazonaws.com 2>/dev/null || echo "IP-ELASTICA")
echo ""
echo "Listo. Abre:  http://$IP/"
echo "Estado del ecosistema:  http://$IP/salud/"
