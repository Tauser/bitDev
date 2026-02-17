# BitDev Crypto Monitor

Painel de monitoramento inteligente para Raspberry Pi com Matriz de LED 64x64.

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.9+-blue)

## 🚀 Funcionalidades

- **Criptomoedas:** Cotações em tempo real (Binance API) com conversão automática para BRL.
- **Mercado Financeiro:** Monitoramento de IBOVESPA, S&P 500 e NASDAQ.
- **Impressão 3D:** Integração com Klipper/Moonraker (Voron, Ender, etc) para status de impressão.
- **Pixel Art:** Galeria de imagens e GIFs animados.
- **Painel Web:** Controle total pelo celular (Wi-Fi, Brilho, Moedas, Playlist).
- **Watchdog:** Sistema de reinício automático em caso de travamento.

## 🛠️ Hardware Necessário

- Raspberry Pi (3, 4, Zero 2W)
- Adafruit RGB Matrix HAT + RTC
- Painel de LED P3 ou P4 (64x64)
- Fonte de Alimentação 5V (Mínimo 4A)

## 📦 Instalação

1. Clone o repositório no Raspberry Pi:

```bash
git clone https://github.com/Tauser/bitDev.git
cd bitDev
```

2. Execute o instalador automático:

```bash
bash install.sh
```

3. Acesse o painel web:
   - URL: `http://IP_DO_RASPBERRY:5000`

## 🔄 Como Atualizar

```bash
git pull
sudo systemctl restart crypto.service
```
