#!/bin/bash

# Script de Instalação Automática - BitDev Monitor
# Execute com: bash install.sh

echo "--- INSTALADOR AUTOMÁTICO BITDEV MONITOR ---"

# 1. Instalar Dependências do Sistema
echo ">> [1/5] Atualizando sistema e instalando dependências..."
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip python3-pillow git python3-setuptools

# 2. Instalar Bibliotecas Python (Flask, Requests)
echo ">> [2/5] Instalando bibliotecas Python..."
# Usa --break-system-packages para garantir instalação no Raspberry Pi OS Bookworm
sudo pip3 install flask requests --break-system-packages

# 3. Compilar Driver da Matriz (Método Manual Robusto)
echo ">> [3/5] Baixando e compilando driver da Matriz de LED..."
cd ~
# Remove versão anterior se existir para evitar conflitos
if [ -d "rpi-rgb-led-matrix" ]; then
    echo "Limpando instalação antiga..."
    rm -rf rpi-rgb-led-matrix
fi

git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix

# Compilação C++ (Core)
make

# Instalação Python Bindings
cd bindings/python
sudo make install-python PYTHON=$(which python3)

# Volta para a pasta onde o script foi executado (pasta do projeto)
cd - > /dev/null

# 4. Configurar Serviço de Boot
echo ">> [4/5] Configurando inicialização automática..."
USER_NAME=$(whoami)
PROJECT_DIR=$(pwd) # Pega a pasta atual automaticamente
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

# 5. Ativar Serviço
echo ">> [5/5] Ativando serviço..."
sudo systemctl daemon-reload
sudo systemctl enable crypto.service
sudo systemctl restart crypto.service

echo "---------------------------------------------------"
echo ">> SUCESSO! Instalação finalizada."
echo ">> O painel deve acender em alguns segundos."
echo ">> Acesse pelo navegador: http://$(hostname -I | awk '{print $1}'):5000"
echo "---------------------------------------------------"