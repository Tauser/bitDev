# Variáveis de Ambiente Sensíveis

## Obrigatória
- `BITDEV_FLASK_SECRET_KEY`

A aplicação Flask falha no startup com erro claro se essa variável não estiver definida.

## Recomendada
- `BITDEV_ADMIN_TOKEN`

Usada para autenticação das rotas administrativas (`/reiniciar`, `/desligar`, `/wifi_reset`, `/salvar_wifi`, `/logs`).
Sem ela, essas rotas retornam `403`.

## Onde configurar no Raspberry Pi
Arquivo de drop-in do systemd:
- `/etc/systemd/system/crypto.service.d/env.conf`

Exemplo:
```ini
[Service]
Environment=BITDEV_FLASK_SECRET_KEY=troque_por_chave_forte
Environment=BITDEV_ADMIN_TOKEN=troque_por_token_admin
```

Aplicar:
```bash
sudo systemctl daemon-reload
sudo systemctl restart crypto.service
```

## Permissões esperadas
- `user_config.json`: `640`
- `/etc/systemd/system/crypto.service.d/env.conf`: `640`
- `/etc/wpa_supplicant/wpa_supplicant.conf`: `640`
