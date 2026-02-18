#!/bin/bash

# Script de Instalação Automática - BitDev Monitor
# Execute com: bash install.sh

echo "--- INSTALADOR AUTOMÁTICO BITDEV MONITOR ---"

echo ">> [1/5] Atualizando sistema e instalando dependências..."
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip python3-pillow git python3-setuptools

echo ">> [2/5] Instalando bibliotecas Python..."
sudo pip3 install flask requests --break-system-packages

echo ">> [3/5] Baixando e compilando driver da Matriz de LED..."
cd ~

if [ -d "rpi-rgb-led-matrix" ]; then
    echo "Limpando instalação antiga..."
    rm -rf rpi-rgb-led-matrix
fi

git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix

make

cd bindings/python
sudo make install-python PYTHON=$(which python3)

cd - > /dev/null

echo ">> [4/5] Configurando inicialização automática..."
USER_NAME=$(whoami)
PROJECT_DIR=$(pwd)
SERVICE_FILE="/etc/systemd/system/crypto.service"

echo "Configurando para usuário: $USER_NAME na pasta: $PROJECT_DIR"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=BitDev Crypto Monitor
After=network-online.target
Wants=network-online.target

[Service]
User=root
Group=root
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/python3 $PROJECT_DIR/main.py
Restart=always
RestartSec=10
WatchdogSec=60
ExecStartPre=/bin/sleep 10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo ">> [5/5] Ativando serviço..."
sudo systemctl daemon-reload
sudo systemctl enable crypto.service
sudo systemctl restart crypto.service

echo "---------------------------------------------------"
echo ">> SUCESSO! Instalação finalizada."
echo ">> O painel deve acender em alguns segundos."
echo ">> Acesse pelo navegador: http://$(hostname -I | awk '{print $1}'):5000"
echo "---------------------------------------------------"