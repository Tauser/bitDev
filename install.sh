#!/bin/bash

# Script de Instalação Automática - BitDev Monitor
# Execute com: bash install.sh

echo "--- INSTALADOR AUTOMÁTICO BITDEV MONITOR ---"

echo ">> [1/5] Atualizando sistema e instalando dependências..."
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip python3-pillow git python3-setuptools wireless-tools

echo ">> [2/5] Instalando bibliotecas Python..."
sudo pip3 install flask requests icalendar python-dateutil --break-system-packages

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
USER_NAME=${SUDO_USER:-$(whoami)}
PROJECT_DIR=$(pwd)
CHOWN_BIN=$(which chown)
SERVICE_FILE="/etc/systemd/system/crypto.service"

# Garante pasta de imagens
mkdir -p "$PROJECT_DIR/images"

# Cria arquivo de config se não existir (para novas instalações)
CONFIG_FILE="$PROJECT_DIR/user_config.json"
OLD_CONFIG_FILE="$PROJECT_DIR/moedas.json"

if [ ! -f "$CONFIG_FILE" ]; then
    if [ -f "$OLD_CONFIG_FILE" ]; then
        echo ">> Migrando configuração antiga..."
        mv "$OLD_CONFIG_FILE" "$CONFIG_FILE"
    else
        echo ">> Criando configuração padrão..."
        cat > "$CONFIG_FILE" <<EOF
{
  "secundarias": ["ETHUSDT", "BTCUSDT", "SOLUSDT"],
  "brilho": 50,
  "modo_noturno": false,
  "msg_custom": "",
  "cidade": "Sao_Paulo",
  "printer_ip": "",
  "printer_name": "VORON 2.4",
  "pages": [
    {"id": "DASHBOARD", "nome": "Dashboard Cripto", "enabled": true, "tempo": 30},
    {"id": "BOLSA",     "nome": "Bolsa & Mercado",  "enabled": true, "tempo": 15},
    {"id": "IMPRESSORA", "nome": "Impressora 3D",    "enabled": true, "tempo": 15},
    {"id": "GALERIA",   "nome": "Galeria PixelArt", "enabled": true, "tempo": 10}
  ]
EOF
    fi
    # Garante permissão correta para o usuário
    sudo $CHOWN_BIN $USER_NAME:$USER_NAME "$CONFIG_FILE"
fi

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
ExecStartPre=$CHOWN_BIN -R $USER_NAME:$USER_NAME $PROJECT_DIR
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